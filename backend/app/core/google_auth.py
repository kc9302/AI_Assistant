from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os
import json

# Robust path resolution
CORE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(CORE_DIR)
BACKEND_ROOT = os.path.dirname(APP_DIR)

TOKEN_FILE = os.path.join(BACKEND_ROOT, "token.json")
CREDENTIALS_FILE = os.path.join(BACKEND_ROOT, "credentials.json")
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_credentials():
    """
    Retrieves the Google OAuth credentials.
    Refresh if expired.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Error loading token.json: {e}")
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save the refreshed creds
                with open(TOKEN_FILE, "w") as token:
                    token.write(creds.to_json())
            except Exception as e:
                if "invalid_grant" in str(e):
                    print("CRITICAL: Google Token is invalid (invalid_grant).")
                    print("ACTION REQUIRED: Run 'python scripts/reauth.py' to refresh your authentication.")
                else:
                    print(f"Error refreshing token: {e}")
                return None
        else:
            # We assume token.json is provided for now as per instructions.
            print("No valid token.json found and cannot refresh.")
            print("ACTION REQUIRED: Run 'python scripts/reauth.py' to generate a new token.")
            return None
            
    return creds

def get_calendar_service():
    """
    Returns an authenticated Google Calendar Service resource.
    """
    creds = get_credentials()
    if not creds:
        return None
    
    try:
        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception as e:
        print(f"Error building service: {e}")
        return None
