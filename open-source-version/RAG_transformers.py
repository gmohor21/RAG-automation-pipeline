import imapclient
import smtplib
import requests
import re
import email
import json
import ssl
import mysql.connector
import os
from flask import Flask, request
from googleapiclient.discovery import build
from google.oauth2 import service_account
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from transformers import pipeline

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
ZAPIER_WEBHOOK_URL = os.environ.get('ZAPIER_WEBHOOK_URL')
TRIGGER_API_KEY = os.environ.get('TRIGGER_API_KEY')

# Add Gmail API configuration
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gmail_service = build('gmail', 'v1', credentials=creds)

# Database connection
def get_db_connection():
    """
    Establishes a connection to a MySQL database.

    Returns:
        mysql.connector.connection.MySQLConnection: The connection object.

    Args:
        None

    Retrieves the database connection details from the environment variables
    and establishes a connection using them.
    """
    # Retrieve the database connection details from environment variables
    host = DB_HOST
    user = DB_USER
    password = DB_PASSWORD
    database = DB_NAME

    # Establish a connection to the MySQL database
    return mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
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

    Uses the following environment variables:
        - EMAIL_ADDRESS: The email address used to send the email.
        - EMAIL_PASSWORD: The password for the email address.

    Uses the following libraries:
        - smtplib
        - ssl
        - email

    This function sends an email using the Gmail SMTP server. It takes the subject, body, and recipient as arguments.
    The email is sent using the EMAIL_ADDRESS and EMAIL_PASSWORD environment variables as the sender's email address and password, respectively.
    The email is sent using the SSL context to establish a secure connection with the Gmail SMTP server.
    After sending the email, the function prints a message indicating that the email was sent successfully.

    If there is an error sending the email, the function catches the exception and prints an error message.

    Note:
        This function requires the EMAIL_ADDRESS and EMAIL_PASSWORD environment variables to be set.

    """

    # Define the Gmail SMTP server and port
    smtp_server = "smtp.gmail.com"
    port = 465

    # Define the sender's email address and password
    sender_email = EMAIL_ADDRESS
    password = EMAIL_PASSWORD

    # Create a new email message object
    message = MIMEMultipart()

    # Set the sender, recipient, and subject of the email
    message["From"] = sender_email
    message["To"] = recipient
    message["Subject"] = subject

    # Attach the email body to the message
    message.attach(MIMEText(body, "plain"))

    # Create an SSL context for secure connection
    context = ssl.create_default_context()

    try:
        # Connect to the SMTP server and log in
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)

            # Send the email
            server.sendmail(sender_email, recipient, message.as_string())

            # Log out and close the connection
            server.quit()

        # Print a message indicating that the email was sent successfully
        print(f"Email sent successfully to: {recipient}")

    except Exception as e:
        # If there is an error, print the error message
        print("Error: ", e)

# Function to trigger Zapier webhook
def trigger_zapier_webhook(payload):
    """
    Triggers a Zapier webhook with the provided payload.

    Args:
        payload (dict): The data payload to be sent to the Zapier webhook.

    Prints:
        - If successful: "Zapier webhook triggered successfully."
        - If failed: "Failed to trigger webhook. Status code: {response status code}"
        - If an error occurs during the process: "Error triggering Zapier webhook: {error message}"
    """
    # Construct the payload to be sent to the Zapier webhook
    zapier_payload = {
        'payload': payload
    }

    try:
        # Send a POST request to the Zapier webhook URL with the payload
        response = requests.post(ZAPIER_WEBHOOK_URL, json=zapier_payload)

        # Check if the request was successful
        if response.status_code != 200:
            print(f"Failed to trigger webhook. Status code: {response.status_code}")
        else:
            print("Zapier webhook triggered successfully.")
    except Exception as e:
        # If an error occurs during the process, print the error message
        print(f"Error triggering Zapier webhook: {e}")

# Function for retrieving the latest user response email
def get_latest_response_id():
    """
    Retrieves the latest response email ID from the IMAP server.

    Retrieves the latest email ID from the INBOX folder of the IMAP server
    that has the specified EMAIL_ADDRESS as the sender. The email content is
    decoded only if the email subject starts with 'SQL Query Result'.

    Returns:
        str: The decoded email content if the subject starts with 'SQL Query Result', otherwise None.
    """

    # Log in to the IMAP server using the provided credentials
    with imapclient.IMAPClient('imap.gmail.com') as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        # Select the INBOX folder
        server.select_folder('INBOX')

        # Search for emails from the specified EMAIL_ADDRESS
        messages = server.search(['FROM', EMAIL_ADDRESS])

        # Sort the messages in reverse order based on the message ID
        messages = sorted(messages, reverse=True)

        if messages:
            # Get the latest email ID
            latest_email_id = messages[0]

            # Fetch the latest email content
            latest_email = server.fetch([latest_email_id], ['BODY.PEEK[]'])

            # Create an email message object from the fetched content
            email_message = email.message_from_bytes(latest_email[latest_email_id][b'BODY[]'])

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
    is extracted from the payload and passed to the `parse_email` function for
    parsing.
    
    If the email data is found in the payload, the function returns a message
    indicating that the email data has been processed and an HTTP status code
    of 200.
    
    If the email data is not found in the payload, the function returns a message
    indicating that no email data was found and an HTTP status code of 400.
    
    Returns:
        str: A message indicating the status of email data processing.
        int: An HTTP status code indicating the processing status.
    """
    # Extract email data from the request payload
    email_data = request.json.get('email_data')
    
    if email_data:
        # Parse the email data
        parse_email(email_data)
        
        # Return a success message and HTTP status code
        return "Email data processed.", 200
    else:
        # Return an error message and HTTP status code
        return "No email data found.", 400

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
        query = f"INSERT INTO {TABLE_NAME} (column1, column2) VALUES (%s, %s)"

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

# Define function to generate code from description using Hugging Face Transformers
def generate_code_from_description(description):
    """
    Generates code from a given description using the Hugging Face Transformers pipeline.

    Args:
        description (str): The description from which the code is generated.

    Returns:
        str: The generated code.

    This function uses the Hugging Face Transformers pipeline to generate code from a given description. It takes in a description as input and uses the 'text-generation' pipeline with the 'gpt2' model to generate code. The generated code is then returned as a string.

    Example:
        >>> generate_code_from_description("Write a function to add two numbers")
        'def add_numbers(a, b):\n    return a + b'
    """
    # Initialize the Hugging Face Transformers pipeline for text generation
    generator = pipeline('text-generation', model='gpt2')

    # Generate code from the description using the pipeline
    result = generator(description, max_length=200, num_return_sequences=1)
    code = result[0]['generated_text']

    return code

# Function to handle triggers
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

        if not query_result:
            # If the query result is empty, send an email request
            to_email = "example@gmail.com"
            subject = "Data Request"
            body = "Please provide the relevant data for the SQL query."
            send_email(subject, body, to_email)

            # Trigger a webhook indicating that an email has been received
            data = {"trigger": "email_received"}
            trigger_zapier_webhook(data)

            # Generate code based on the description and print it
            description = "Whenever an SQL query returns a blank result, send an email via Gmail based on certain parameters. Whenever the user replies to the email, trigger a webhook to parse and insert Gmail response data into the SQL table again."
            automation_code = generate_code_from_description(description)
            print(automation_code)

        else:
            # If the query result is not empty, print a message
            print("SQL query returned results.")

        # Get the latest response email ID
        email_data = get_latest_response_id()
        if email_data:
            # Parse the email data
            parsed_data = parse_email(email_data)
            # Update the SQL table with the parsed email data
            update_sql_table(parsed_data)

            # Trigger a webhook indicating that the email has been parsed
            data = {"trigger": "email_parsed"}
            trigger_zapier_webhook(data)

            # Trigger a webhook indicating that the automation workflow has completed
            zapier_payload = {
                'message': 'Automation workflow completed.'
            }
            trigger_zapier_webhook(zapier_payload)

    except Exception as e:
        # Print the error if an exception occurs
        print(f"Error in main function: {e}")

# Define main function
def main():
    """
    The main function that calls the function to handle triggers.
    
    This function is the entry point of the program. It calls the `handle_trigger`
    function to execute the automation workflow.
    """
    # Call the function to handle triggers
    handle_trigger()

if __name__ == "__main__":
    main()

