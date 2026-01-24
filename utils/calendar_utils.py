"""Google Calendar integration utilities."""

import json
import os
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Calendar credentials file path
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'token.json')

# OAuth redirect URI - must match what's configured in Google Cloud Console
REDIRECT_URI = 'http://localhost:5001/oauth2callback'


def get_calendar_service():
    """
    Get a Google Calendar service instance using saved credentials.

    Returns:
        Google Calendar service object or None if authentication fails
    """
    creds = None

    # Check if we have a valid token
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Error loading token: {e}")

    # If no valid credentials, return None (user needs to authorize)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save refreshed credentials
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                return None
        else:
            # No valid credentials available
            return None

    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building calendar service: {e}")
        return None


def get_authorization_url(state):
    """
    Generate the OAuth authorization URL for web flow.

    Args:
        state: A random state string for CSRF protection

    Returns:
        Authorization URL string or None if credentials file is missing
    """
    if not os.path.exists(CREDENTIALS_FILE):
        return None

    try:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )
        return authorization_url
    except Exception as e:
        print(f"Error generating authorization URL: {e}")
        return None


def exchange_code_for_token(code, state):
    """
    Exchange the authorization code for access tokens.

    Args:
        code: Authorization code from OAuth callback
        state: State string for verification

    Returns:
        Dictionary with success status
    """
    if not os.path.exists(CREDENTIALS_FILE):
        return {
            'success': False,
            'error': 'Credentials file not found'
        }

    try:
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
            state=state
        )
        flow.fetch_token(code=code)
        creds = flow.credentials

        # Save the credentials
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

        return {
            'success': True,
            'message': 'Successfully authorized Google Calendar access'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error exchanging code for token: {str(e)}'
        }


def add_meal_plan_to_calendar(meal_plan, calendar_id='primary'):
    """
    Add a meal plan to Google Calendar.

    Args:
        meal_plan: Dictionary containing meal plan data with recipes and dates
        calendar_id: Google Calendar ID (default: 'primary' for main calendar)

    Returns:
        Dictionary with success status and event IDs if successful
    """
    service = get_calendar_service()
    if not service:
        return {
            'success': False,
            'error': 'Could not authenticate with Google Calendar. Please set up credentials.json in data/ directory.'
        }

    try:
        start_date = datetime.strptime(meal_plan.get('start_date'), '%Y-%m-%d')
        recipes = meal_plan.get('recipes', [])
        event_ids = []

        for i, recipe in enumerate(recipes):
            meal_date = start_date + timedelta(days=i)

            # Create event for dinner time (5 PM)
            event_start = meal_date.replace(hour=17, minute=0, second=0)
            event_end = event_start + timedelta(hours=1)

            event = {
                'summary': f'🍽️ Dinner: {recipe.get("name")}',
                'description': recipe.get('description', '') + '\n\nFrom AI Meal Planner',
                'start': {
                    'dateTime': event_start.isoformat(),
                    'timeZone': 'America/Denver',
                },
                'end': {
                    'dateTime': event_end.isoformat(),
                    'timeZone': 'America/Denver',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 60},  # Reminder 1 hour before
                    ],
                },
            }

            created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
            event_ids.append(created_event.get('id'))

        return {
            'success': True,
            'event_ids': event_ids,
            'message': f'Successfully added {len(event_ids)} meals to your calendar!'
        }

    except HttpError as error:
        return {
            'success': False,
            'error': f'Google Calendar API error: {error}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error adding to calendar: {str(e)}'
        }


def remove_meal_plan_from_calendar(event_ids, calendar_id='primary'):
    """
    Remove meal plan events from Google Calendar.

    Args:
        event_ids: List of Google Calendar event IDs to remove
        calendar_id: Google Calendar ID (default: 'primary')

    Returns:
        Dictionary with success status
    """
    service = get_calendar_service()
    if not service:
        return {
            'success': False,
            'error': 'Could not authenticate with Google Calendar'
        }

    try:
        for event_id in event_ids:
            try:
                service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            except HttpError as e:
                print(f"Error deleting event {event_id}: {e}")

        return {
            'success': True,
            'message': f'Removed {len(event_ids)} events from calendar'
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Error removing from calendar: {str(e)}'
        }


def is_calendar_configured():
    """
    Check if Google Calendar is properly configured.

    Returns:
        Boolean indicating if credentials are set up
    """
    return os.path.exists(CREDENTIALS_FILE)


def is_calendar_authorized():
    """
    Check if user has authorized Google Calendar access.

    Returns:
        Boolean indicating if valid token exists
    """
    if not os.path.exists(TOKEN_FILE):
        return False

    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        return creds and creds.valid
    except Exception:
        return False
