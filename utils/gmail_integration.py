"""
utils/gmail_integration.py
Gmail integration using Gmail API.
Setup: https://developers.google.com/gmail/api/quickstart/python
Place credentials.json in data/ folder.
"""

import os
import base64
import json
from email.mime.text import MIMEText
from core.logger import log_info, log_error

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]
CREDS_FILE = "data/credentials.json"
TOKEN_FILE = "data/gmail_token.json"


def _get_service():
    """Authenticate and return Gmail API service."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_FILE):
                raise FileNotFoundError(
                    "credentials.json not found in data/ folder. "
                    "Please set up Gmail API at https://developers.google.com/gmail/api"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def read_emails(max_results: int = 5) -> str:
    """Read latest unread emails from Gmail."""
    try:
        service = _get_service()
        results = service.users().messages().list(
            userId="me",
            labelIds=["INBOX", "UNREAD"],
            maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return "No unread emails Boss. Your inbox is clean."

        email_list = []
        for msg in messages:
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()

            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            sender = headers.get("From", "Unknown")
            subject = headers.get("Subject", "No subject")
            email_list.append(f"From: {sender[:40]} | {subject[:50]}")

        log_info(f"Read {len(email_list)} emails")
        return f"You have {len(messages)} unread emails Boss:\n" + "\n".join(email_list)

    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        log_error(f"Gmail read error: {e}")
        return f"Could not read Gmail Boss. Error: {e}"


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Gmail."""
    try:
        service = _get_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        log_info(f"Email sent to {to}")
        return f"Email sent to {to} Boss."
    except Exception as e:
        log_error(f"Gmail send error: {e}")
        return f"Could not send email Boss. Error: {e}"


def send_email_voice() -> str:
    """Interactive voice-guided email sending."""
    from core.listener import listen_for_text
    to = listen_for_text("Who should I send the email to Boss? Say the email address.")
    subject = listen_for_text("What is the subject Boss?")
    body = listen_for_text("What should the email say Boss?")
    if not all([to, subject, body]):
        return "Could not get all email details Boss. Please try again."
    return send_email(to, subject, body)