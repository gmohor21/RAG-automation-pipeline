import openai
import imapclient
import smtplib
import requests
import re
import email
import json
import ssl
import mysql.connector
import os

from trigger import Trigger
from flask import Flask, request
from googleapiclient.discovery import build
from google.oauth2 import service_account
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Zapier integration to trigger the automation workflow
import zapier

app = Flask(__name__)

# Load configuration variables from environment variables
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCOUNT_JSON_FILE')
DB_HOST = os.environ.get('DB_HOST')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME')
TABLE_NAME = os.environ.get('TABLE_NAME')
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
ZAPIER_WEBHOOK_URL = os.environ.get('ZAPIER_WEBHOOK_URL')
TRIGGER_API_KEY = os.environ.get('TRIGGER_API_KEY')

# Add Gmail API configuration
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Connect to Gmail
gmail_service = build('gmail', 'v1', credentials=creds)

# Set up OpenAI API key
openai.api_key = OPENAI_API_KEY

# Set up Zapier webhook URL
zapier_webhook_url = ZAPIER_WEBHOOK_URL

# Set up trigger.dev API key
trigger_api_key = TRIGGER_API_KEY

# Set up trigger.dev client
trigger_client = Trigger(api_key=trigger_api_key)

# Database connection
def get_db_connection():
    """
    Establishes a connection to a MySQL database.

    Returns:
        mysql.connector.connection.MySQLConnection: The connection object.

    This function uses the database connection details from the environment variables
    to establish a connection to the MySQL database.
    """
    # Connect to the MySQL database
    return mysql.connector.connect(
        host=DB_HOST,  # Database host
        user=DB_USER,  # Database username
        password=DB_PASSWORD,  # Database password
        database=DB_NAME  # Database name
    )

# Function to execute SQL query
def execute_sql_query(query):
    """
    Executes an SQL query and returns the result.

    Args:
        query (str): The SQL query to be executed.

    Returns:
        list: The result of the executed query, fetched using cursor.fetchall().
            If there is an error executing the query, it returns an empty list.

    This function establishes a connection to the SQL database using the `get_db_connection` function.
    It then executes the provided SQL query using the cursor object.
    The result of the query is fetched using cursor.fetchall() and returned.
    If there is an error executing the query, the function prints an error message and returns an empty list.
    Finally, the cursor and the connection to the database are closed.
    """
    # Establish a connection to the SQL database
    connection = get_db_connection()

    # Create a cursor object to execute SQL queries
    cursor = connection.cursor()

    try:
        # Execute the SQL query
        cursor.execute(query)

        # Fetch all the rows returned by the query
        result = cursor.fetchall()

        # Return the result of the query
        return result

    except Exception as e:
        # If there is an error, print the error message and return an empty list
        print(f"Error executing SQL query: {e}")
        return []

    finally:
        # Close the cursor and the database connection
        cursor.close()
        connection.close()

# Function to send email via Gmail
def send_email(subject, body, recipient):
    """
    Sends an email using the provided subject, body, and recipient.

    Args:
        subject (str): The subject of the email.
        body (str): The body of the email.
        recipient (str): The email address of the recipient.

    Raises:
        Exception: If there is an error sending the email.

    Returns:
        None

    Prints:
        str: A message indicating that the email was sent successfully.

    This function sends an email using the Gmail SMTP server. It takes the subject, body, and recipient as arguments.
    The email is sent using the EMAIL_ADDRESS and EMAIL_PASSWORD environment variables as the sender's email address and password, respectively.
    The email is sent using the SSL context to establish a secure connection with the Gmail SMTP server.
    After sending the email, the function prints a message indicating that the email was sent successfully.

    If there is an error sending the email, the function catches the exception and prints an error message.
    """
    try:
        # Define the Gmail SMTP server and port
        smtp_server = "smtp.gmail.com"
        port = 465

        # Define the sender's email address and password
        sender_email = EMAIL_ADDRESS
        password = EMAIL_PASSWORD

        # Create a new email message object
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        # Establish a secure connection with the Gmail SMTP server
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient, message.as_string())

        # Print a success message
        print(f"Email sent successfully to: {recipient}")

    except Exception as e:
        # Print an error message if there was an issue sending the email
        print("Error: ", e)

# Define Zapier webhook function
def trigger_zapier_webhook(payload):
    """
    Triggers a Zapier webhook with the provided payload.

    Args:
        payload (dict): The data payload to be sent to the Zapier webhook.

    Prints:
        str: A message indicating that the webhook was triggered successfully.
            If there is an error triggering the webhook, prints an error message instead.

    This function takes a payload dictionary as an argument and sends it to the Zapier webhook URL defined in the environment variable ZAPIER_WEBHOOK_URL.
    The payload is wrapped in another dictionary with the key 'payload' to conform to the Zapier webhook API.
    """
    zapier_payload = {'payload': payload}
    try:
        # Send a POST request to the Zapier webhook URL with the payload
        zapier.webhooks.post(zapier_webhook_url, json=zapier_payload)

        # Print a success message
        print("Zapier webhook triggered successfully.")
    except Exception as e:
        # Print an error message if there was an issue triggering the webhook
        print(f"Error triggering Zapier webhook: {e}")

# Define trigger.dev webhook function
def trigger_triggerdev_webhook(data):
    """
    Triggers a trigger.dev webhook with the provided data payload.

    Args:
        data (dict): The data payload to be sent to the trigger.dev webhook.

    Prints:
        str: A message indicating that the webhook was triggered successfully.
            If there is an error triggering the webhook, prints an error message instead.

    This function creates an event using the trigger_client and retrieves the webhook URL from the event data.
    It then sends a POST request to the webhook URL with the provided data payload.
    If the request is successful (status code 200), it prints a success message.
    Otherwise, it prints an error message with the status code.
    """
    # Create an event using the trigger_client and retrieve the webhook URL
    event = trigger_client.events.create(data=data)
    webhook_url = event.data.get("webhook_url")

    try:
        # Send a POST request to the webhook URL with the data payload
        response = requests.post(webhook_url, json=data)

        # Check if the request was successful
        if response.status_code != 200:
            print(f"Failed to trigger webhook. Status code: {response.status_code}")
        else:
            print("trigger.dev webhook triggered successfully.")
    except Exception as e:
        # Print an error message if there was an issue triggering the webhook
        print(f"Error triggering trigger.dev webhook: {e}")

# Function for retrieving the latest user response email
def get_latest_response_id():
    """
    Retrieves the latest user response email ID from the IMAP server.

    Retrieves the latest email ID from the INBOX folder of the IMAP server
    that has the specified EMAIL_ADDRESS as the sender. The email content is
    decoded only if the email subject starts with 'SQL Query Result'.

    Returns:
        str: The decoded email content if the subject starts with 'SQL Query Result', otherwise None.
    """
    with imapclient.IMAPClient('imap.gmail.com') as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.select_folder('INBOX')
        messages = server.search(['FROM', EMAIL_ADDRESS])
        messages = sorted(messages, reverse=True)

        if messages:
            # Get the latest email content
            latest_email = server.fetch(messages[0], ['BODY.PEEK[]'])
            email_message = email.message_from_bytes(latest_email[messages[0]][b'BODY[]'])

            # Check if the email subject starts with 'SQL Query Result'
            if str(email_message['Subject']).startswith('SQL Query Result'):
                # Decode and return the email content
                return email_message.get_payload(decode=True).decode('utf-8')

        # Return None if no matching email is found
        return None

# Webhook endpoint to handle email response data
@app.route('/webhook', methods=['POST'])
def webhook():
    """
    A webhook endpoint that processes email data received via POST request.
    
    This endpoint expects a JSON payload containing the email data. The email data
    is extracted from the payload and passed to the `parse_email_response` function for
    parsing.
    
    If the email data is found in the payload, the function returns a message
    indicating that the email data has been processed and an HTTP status code
    of 200.
    
    Returns:
        str: A message indicating the status of email data processing.
        int: An HTTP status code indicating the processing status.
    """
    # Extract email data from the request payload
    email_data = request.data.decode('utf-8')
    
    # Parse the email data
    parse_email_response(email_data)
    
    # Return a success message and HTTP status code
    return 'OK', 200

# Define Python script function to parse email response
def parse_email_response(email_data):
    """
    Parses email response data and updates the SQL table with the parsed data.

    Args:
        email_data (str): The response data from the email.

    Returns:
        None
    """
    # Parse the email data
    parsed_data = parse_email(email_data)

    # Update the SQL table with the parsed data
    update_sql_table(parsed_data)

# Function for parsing the email response
def parse_email(response_text):
    """
    Parses a response text from an email and extracts key-value pairs.

    Args:
        response_text (str): The response text from the email.

    Returns:
        dict: A dictionary containing the extracted key-value pairs.
    """
    # Initialize an empty dictionary to store the extracted key-value pairs
    data = {}

    # Split the response text into lines
    lines = response_text.split("\n")

    # Iterate over each line in the response text
    for line in lines:
        # Use regular expression to match key-value pairs in the line
        match = re.match(r"(\w+):\s*(.*)", line)

        # If a key-value pair is found
        if match:
            # Extract the key and value from the match
            key, value = match.groups()

            # Add the key-value pair to the dictionary
            data[key] = value

    # Return the dictionary containing the extracted key-value pairs
    return data

# Function for updating the SQL table
def update_sql_table(data):
    """
    Updates an SQL table with the given data.

    Args:
        data (dict): A dictionary containing the data to be inserted into the table.
            It should have the keys 'column1' and 'column2', representing the values to be inserted.

    Returns:
        None

    Raises:
        Exception: If there is an error updating the SQL table. The specific error message will be printed.

    This function establishes a connection to the SQL database using the `get_db_connection` function.
    It then executes an INSERT query to insert the data into the specified table.
    If the query is successful, it prints a success message.
    If there is an error, it rolls back the transaction and prints an error message.
    Finally, it closes the cursor and the connection to the database.
    """
    # Establish a connection to the SQL database
    conn = get_db_connection()

    # Create a cursor object to execute SQL queries
    cursor = conn.cursor()

    try:
        # Construct the SQL INSERT query
        query = "INSERT INTO {table_name} (column1, column2) VALUES (%s, %s)".format(
            table_name=TABLE_NAME)

        # Execute the INSERT query with the provided data
        cursor.execute(query, (data['column1'], data['column2']))

        # Commit the transaction to save the changes
        conn.commit()

        # Print a success message
        print("SQL table updated successfully.")

    except Exception as e:
        # If there is an error, roll back the transaction and print the error message
        conn.rollback()
        print(f"Error updating SQL table: {e}")

    finally:
        # Close the cursor and the database connection
        cursor.close()
        conn.close()

# Define GPT-4 function
def generate_code_from_description(description):
    """
    Generates code from a given description using GPT-4 model from OpenAI.

    Args:
        description (str): The description from which the code is generated.

    Returns:
        str: The generated code.

    This function uses the OpenAI GPT-4 model to generate code from a given description.
    It takes in a description as input and uses the 'text-generation' prompt to generate code.
    The generated code is then returned as a string.

    """
    # Prompt the GPT-4 model to generate code from the given description
    response = openai.Completion.create(
        engine="gpt-4",
        prompt=f"Generate Python code for the following automation task: {description}",
        max_tokens=1000,  # Maximum number of tokens in the generated code
        n=1,  # Number of completions to generate
        stop=None,  # Optional string to stop the generation
        temperature=0.7,  # Controls the randomness of the generated code
    )

    # Extract the generated code from the response
    code = response.choices[0].text.strip()

    return code

# A separate function to be triggered by an event or a scheduled task
@Trigger.action
@Trigger.event('cron')
def handle_trigger():
    """
    Handles triggers based on SQL query results.

    Sends an email request when the query result is empty, triggers webhooks
    based on email responses, and updates the SQL table with parsed email data.
    Handles exceptions by printing errors.

    Raises:
        Exception: If an error occurs in the main function.
    """
    try:
        # Execute the SQL query
        query = "SELECT * FROM example_table WHERE condition = 'example'"
        query_result = execute_sql_query(query)

        # Check if the query result is empty
        if not query_result:
            # Send an email request
            to_email = "example@gmail.com"
            subject = "Data Request"
            body = "Please provide the relevant data for the SQL query."
            send_email(to_email, subject, body)

            # Trigger a webhook indicating that an email has been received
            data = {"trigger": "email_received"}
            trigger_zapier_webhook(data)

            # Generate code based on the description and print it
            description = "Whenever an SQL query returns a blank result, send an email via Gmail based on certain parameters. Whenever the user replies to the email, trigger a webhook to parse and insert Gmail response data into the SQL table again."
            automation_code = generate_code_from_description(description)
            print(automation_code)
        else:
            print("SQL query returned results.")

        # Get the latest response email ID
        email_data = get_latest_response_id()
        if email_data:
            # Parse the email data
            parse_email_response(email_data)

            # Trigger a webhook indicating that the email has been parsed
            data = {"trigger": "email_parsed"}
            trigger_triggerdev_webhook(data)

            # Trigger a webhook indicating that the automation workflow has completed
            zapier_payload = {
                'message': 'Automation workflow completed.'
            }
            trigger_zapier_webhook(zapier_payload)

    except Exception as e:
        # If an error occurs during the process, print the error message
        print(f"Error in main function: {e}")

def main():
    """
    The main function that runs the Flask app on port 5000.
    This function does not take any parameters and does not return anything.
    """
    # Run the Flask app on port 5000
    app.run(port=5000)

if __name__ == "__main__":
    main()

