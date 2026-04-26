import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
# This strictly limits the app to reading emails, not sending or deleting.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        print("✅ Successfully connected to Gmail API!\n")

        # Search for recent receipts or invoices (Max 10 for testing)
        print("🔍 Searching for recent receipts...")
        # Added explicit Amazon keywords and sender filters
        query = "receipt OR invoice OR 'order confirmation' OR 'amazon order' OR from:amazon"
        # Bumped up the max results to 20 to look a bit further back
        results = service.users().messages().list(userId='me', q=query, maxResults=20).execute()
        messages = results.get('messages', [])

        if not messages:
            print("No receipts found.")
            return

        print("-" * 60)
        for message in messages:
            # We removed format='metadata' to get the full payload
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload']['headers']
            
            # Extract Subject and Date
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            date = next((h['value'] for h in headers if h['name'] == 'Date'), "No Date")
            
            # Extract the plain-text snippet of the email body
            snippet = msg.get('snippet', 'No snippet available')
            
            print(f"[{date[:16]}] {subject[:40]}...")
            print(f"   ↳ {snippet[:100]}...\n") # Prints the first 100 characters of the body
        print("-" * 60)

    # THIS WAS THE MISSING PART!
    except Exception as error:
        print(f"❌ An error occurred: {error}")

if __name__ == '__main__':
    main()