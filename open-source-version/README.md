# Open-Source Version of the Script

## Overview

This version of the RAG automation script uses a pre-trained model from the Hugging Face Transformers library to generate code snippets based on incoming webhook data. The script handles email parsing, SQL database updates, and triggering webhooks using Zapier and Trigger.dev.

## Prerequisites

1. **Google Service Account JSON File:**
    - Go to the Google Cloud Console.
    - Create a new project or use an existing one.
    - Enable the Gmail API for the project.
    - Create a service account and download the JSON key file.
    - Store the file path, e.g., `/path/to/service_account.json`.

2. **Database Credentials:**
    - Set up a MySQL database server if not already done.
    - Create a user and a database for the script to use.
    - Store the credentials.

3. **Email Credentials:**
    - Use your Gmail account credentials. Ensure that "Less secure app access" is enabled for the Gmail account.

4. **Hugging Face Transformers Model:**
    - No additional setup needed; the script will download the model automatically.

5. **Zapier Webhook URL:**
    - Create a Zap on Zapier and set up a Webhook trigger.
    - Copy the Webhook URL.

6. **Trigger.dev API Key:**
    - Sign up on Trigger.dev and get your API key.

## Setup

1. Clone the repository and navigate to the `open-source-version` directory:
    ```sh
    git clone https://github.com/your-username/automation-script.git
    cd automation-script/open-source-version
    ```

2. Create a `.env` file with the following content:
    ```plaintext
    SERVICE_ACCOUNT_JSON_FILE=/path/to/service_account.json
    DB_HOST=localhost
    DB_USER=username
    DB_PASSWORD=password
    DB_NAME=database_name
    TABLE_NAME=table_name
    EMAIL_ADDRESS=your_email@gmail.com
    EMAIL_PASSWORD=your_password
    ZAPIER_WEBHOOK_URL=your_zapier_webhook_url
    TRIGGER_API_KEY=your_trigger_dev_api_key
    ```

3. Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```

## Running the Script

1. Start the Flask app:
    ```sh
    python automation_script.py
    ```

2. The Flask app will listen for incoming webhooks and process them accordingly.

## License

This project is licensed under the MIT License.

