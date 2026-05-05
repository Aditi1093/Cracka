"""
utils/calendar_integration.py
Google Calendar integration.
Same credentials.json as Gmail (uses Google API).
"""

import os
from datetime import datetime, timedelta
from core.logger import log_info, log_error

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CREDS_FILE = "data/credentials.json"
TOKEN_FILE = "data/calendar_token.json"


def _get_service():
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
                raise FileNotFoundError("credentials.json not found. Set up Google Calendar API.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def get_todays_events() -> str:
    """Get today's calendar events."""
    try:
        service = _get_service()
        now = datetime.utcnow()
        start = now.replace(hour=0, minute=0, second=0).isoformat() + "Z"
        end = now.replace(hour=23, minute=59, second=59).isoformat() + "Z"

        events_result = service.events().list(
            calendarId="primary",
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        events = events_result.get("items", [])
        if not events:
            return "No events on your calendar today Boss. All clear!"

        lines = [f"You have {len(events)} event(s) today Boss:"]
        for e in events:
            start_time = e["start"].get("dateTime", e["start"].get("date", ""))
            if "T" in start_time:
                t = datetime.fromisoformat(start_time.replace("Z", ""))
                time_str = t.strftime("%I:%M %p")
            else:
                time_str = "All day"
            lines.append(f"  • {time_str}: {e.get('summary', 'No title')}")

        return "\n".join(lines)

    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        log_error(f"Calendar read error: {e}")
        return f"Could not read calendar Boss. Error: {e}"


def add_event(title: str, start_time: datetime, duration_mins: int = 60) -> str:
    """Add an event to Google Calendar."""
    try:
        service = _get_service()
        end_time = start_time + timedelta(minutes=duration_mins)

        event = {
            "summary": title,
            "start": {"dateTime": start_time.isoformat(), "timeZone": "Asia/Kolkata"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "Asia/Kolkata"},
        }

        service.events().insert(calendarId="primary", body=event).execute()
        log_info(f"Calendar event added: {title}")
        return f"Event '{title}' added to your calendar Boss."

    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        log_error(f"Calendar add error: {e}")
        return f"Could not add event Boss. Error: {e}"


def add_event_voice() -> str:
    """Voice-guided event creation."""
    import re
    from core.listener import listen_for_text
    from core.voice_engine import speak

    title = listen_for_text("What is the event title Boss?")
    time_str = listen_for_text("What time should I set it? Say like '3 PM' or '10 30 AM' Boss.")

    # Parse time
    try:
        now = datetime.now()
        match = re.search(r"(\d+)(?::(\d+))?\s*(am|pm)", time_str.lower())
        if match:
            hour = int(match.group(1))
            mins = int(match.group(2)) if match.group(2) else 0
            ampm = match.group(3)
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            event_time = now.replace(hour=hour, minute=mins, second=0, microsecond=0)
        else:
            return "Could not understand the time Boss. Please try again."

        return add_event(title, event_time)

    except Exception as e:
        return f"Could not create event Boss. Error: {e}"