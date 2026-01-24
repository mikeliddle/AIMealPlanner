# Google Calendar Integration Guide

This guide explains how to set up Google Calendar integration for AI Meal Planner.

## Overview

The Google Calendar integration allows you to automatically add your accepted meal plans to your Google Calendar. Each meal is added as a calendar event with:

- Event time: 6:00 PM on the scheduled date
- Duration: 1 hour
- Reminder: 1 hour before the meal
- Description: Recipe details and link back to the app

## Setup Steps

### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" at the top, then "New Project"
3. Enter a project name (e.g., "AI Meal Planner")
4. Click "Create"

### 2. Enable Google Calendar API

1. In your project, navigate to "APIs & Services" > "Library"
2. Search for "Google Calendar API"
3. Click on it and press "Enable"

### 3. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "+ CREATE CREDENTIALS" at the top
3. Select "OAuth client ID"
4. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in the required fields (app name, user support email, developer contact)
   - Add your email as a test user
   - Save and continue
5. Back in the credentials creation:
   - Application type: **Web application**
   - Name: "AI Meal Planner Web"
   - Under "Authorized redirect URIs", click "ADD URI" and add:
     - `http://localhost:5001/oauth2callback`
   - Click "Create"
6. Download the credentials JSON file

### 4. Install Credentials in the App

#### For Local Development:

```bash
# Create the data directory if it doesn't exist
mkdir -p data

# Copy the downloaded credentials file
cp ~/Downloads/client_secret_*.json data/credentials.json
```

#### For Docker:

```bash
# Place credentials in the data directory
cp ~/Downloads/client_secret_*.json data/credentials.json

# The docker-compose.yml already mounts the data directory
docker-compose up -d
```

### 5. First-Time Authorization

1. Start the application
2. Generate and accept a meal plan
3. Check the "Add meals to Google Calendar" option
4. Click "Accept Meal Plan"
5. You'll be redirected to Google's authorization page in your browser
6. Sign in with your Google account
7. Grant the requested permissions (Calendar access)
8. You'll be redirected back to the app
9. The authorization token will be saved in `data/token.json`

**Note**: You only need to do this once. The token will be used for all future calendar operations.

## Usage

### Adding Meal Plans to Calendar

1. Generate a meal plan
2. Review and customize it in the staging area
3. When ready to accept:
   - Check ☑️ "Add meals to Google Calendar"
   - Click "Accept Meal Plan"
4. Your meals will be added as calendar events

### Calendar Event Details

Each meal event includes:

- **Title**: 🍽️ Dinner: [Recipe Name]
- **Time**: 6:00 PM - 7:00 PM (on the scheduled date)
- **Description**: Recipe description + "From AI Meal Planner"
- **Reminder**: Pop-up notification 1 hour before

### Customizing Event Time

To change the default meal time (6:00 PM), edit `utils/calendar_utils.py`:

```python
# Line 85-86
event_start = meal_date.replace(hour=18, minute=0, second=0)  # 18 = 6 PM
```

Change `hour=18` to your preferred time (24-hour format).

### Customizing Time Zone

By default, events use `America/New_York` timezone. To change this, edit `utils/calendar_utils.py`:

```python
# Lines 88-89 and 92-93
'timeZone': 'America/New_York',  # Change to your timezone
```

Valid timezone strings: `America/Los_Angeles`, `Europe/London`, `Asia/Tokyo`, etc.

## Troubleshooting

### "Could not authenticate with Google Calendar"

**Cause**: No credentials file found

**Solution**:

1. Verify `data/credentials.json` exists
2. Check the file has valid JSON format
3. Ensure it's the OAuth client credentials (not API key or service account)

### "Error during OAuth flow"

**Cause**: Authorization failed or was cancelled

**Solution**:

1. Try the authorization process again
2. Make sure you're using the correct Google account
3. Grant all requested permissions
4. Check that your email is added as a test user in Google Cloud Console

### "Token expired" or "Invalid token"

**Cause**: The saved token is no longer valid

**Solution**:

```bash
# Delete the token file to force re-authorization
rm data/token.json

# Next time you add to calendar, you'll be prompted to authorize again
```

### Events not appearing in calendar

**Possible causes**:

1. Wrong calendar selected (if you have multiple calendars)
2. Calendar sync issues
3. Event was created but in wrong timezone

**Solutions**:

- Refresh your Google Calendar view
- Check "All Calendars" in calendar settings
- Verify the timezone in `calendar_utils.py`

### OAuth consent screen not configured

**Cause**: You skipped the consent screen configuration

**Solution**:

1. Go to Google Cloud Console
2. Navigate to "APIs & Services" > "OAuth consent screen"
3. Fill out the required information
4. Add your email as a test user
5. Save changes

## Security Notes

- **credentials.json**: Contains your OAuth client ID and secret. Don't commit to git!
- **token.json**: Contains your personal access token. Keep this private!
- Add both files to `.gitignore`

### Recommended .gitignore entries:

```
data/credentials.json
data/token.json
```

## Advanced Configuration

### Using a Specific Calendar

By default, events are added to your primary calendar. To use a different calendar:

1. Get the calendar ID:
   - Go to Google Calendar settings
   - Find your calendar in the list
   - Copy the "Calendar ID" (looks like an email address)

2. Modify the app.py accept route:
   ```python
   calendar_result = add_meal_plan_to_calendar(plan, calendar_id='your-calendar-id@group.calendar.google.com')
   ```

### Customizing Event Reminders

Edit `utils/calendar_utils.py` to change reminder settings:

```python
'reminders': {
    'useDefault': False,
    'overrides': [
        {'method': 'popup', 'minutes': 60},  # Change minutes
        {'method': 'email', 'minutes': 1440},  # Add email reminder (24 hours)
    ],
},
```

## Disabling Calendar Integration

If you don't want to use Google Calendar:

1. Simply don't create `data/credentials.json`
2. The app will detect this and disable the calendar feature
3. The "Add to Calendar" checkbox won't appear in the staging view

The app works fully without calendar integration!

## Getting Help

If you encounter issues:

1. Check the application logs for error messages
2. Verify your Google Cloud Console settings
3. Ensure you're using a Desktop app OAuth client (not Web or Mobile)
4. Try deleting `token.json` and re-authorizing

For more help, see the main [README.md](../README.md) or create an issue in the repository.
