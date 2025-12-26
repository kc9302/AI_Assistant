import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Ensure we can find the project root regardless of where this script is called from
# This assumes the script is in backend/scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(SCRIPT_DIR)

TOKEN_FILE = os.path.join(BACKEND_ROOT, "token.json")
CREDENTIALS_FILE = os.path.join(BACKEND_ROOT, "credentials.json")
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def main():
    """Manually refresh or create Google OAuth credentials."""
    creds = None
    
    # Remove old token if it exists to force fresh login
    if os.path.exists(TOKEN_FILE):
        print(f"Removing old {TOKEN_FILE}...")
        os.remove(TOKEN_FILE)

    print("Starting authentication flow...")
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"ERROR: {CREDENTIALS_FILE} not found.")
        print(f"Please ensure your OAuth client secret file is named 'credentials.json' and placed at {BACKEND_ROOT}.")
        return

    try:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        # Use run_local_server which will open a browser
        creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
        
        print(f"\nSUCCESS: {TOKEN_FILE} has been created successfully!")
        print("You can now restart your backend server.")
    except Exception as e:
        print(f"FAILED: Authentication error: {e}")

if __name__ == "__main__":
    main()
