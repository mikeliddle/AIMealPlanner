# Google OAuth Setup for Web App Flow

The application has been updated to use **Web Application OAuth flow** instead of Desktop app flow.

## What Changed

1. **OAuth Flow**: Now uses web-based OAuth with proper redirect URIs
2. **Authorization**: User clicks "Accept Meal Plan" → redirected to Google → authorized → redirected back
3. **No More Pop-ups**: Uses browser redirects instead of local server

## Required Configuration in Google Cloud Console

### 1. Update Your OAuth Client

Go to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials)

**Option A: Update Existing Credentials**

1. Click on your existing OAuth 2.0 Client ID
2. Change "Application type" to **Web application**
3. Under "Authorized redirect URIs", add:
   ```
   http://localhost:5001/oauth2callback
   ```
4. Click "Save"
5. Download the updated JSON file and replace `data/credentials.json`

**Option B: Create New Credentials**

1. Click "+ CREATE CREDENTIALS" → "OAuth client ID"
2. Application type: **Web application**
3. Name: "AI Meal Planner Web"
4. Under "Authorized redirect URIs", click "ADD URI" and add:
   ```
   http://localhost:5001/oauth2callback
   ```
5. Click "Create"
6. Download the JSON file and save as `data/credentials.json`

### 2. Verify credentials.json Format

Your `data/credentials.json` should look like this:

```json
{
  "web": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["http://localhost:5001/oauth2callback"]
  }
}
```

**Note**: Make sure it says `"web"` NOT `"installed"`.

## How Authorization Works Now

1. **First Time Authorization**:
   - User generates a meal plan and clicks "Accept Meal Plan" with calendar checked
   - If not authorized, user is redirected to Google's authorization page
   - User signs in and grants calendar permissions
   - Google redirects back to `http://localhost:5001/oauth2callback`
   - Token is saved in `data/token.json`
   - User is redirected back to the meal plan page

2. **Subsequent Uses**:
   - Token is reused automatically
   - No authorization needed unless token expires or is revoked

## New Routes Added

- `POST /authorize-calendar` - Initiates OAuth flow
- `/oauth2callback` - Handles Google's OAuth redirect
- `POST /revoke-calendar` - Revokes authorization (deletes token.json)

## Testing

1. Delete `data/token.json` if it exists (to test fresh authorization)
2. Start the app: `python app.py`
3. Generate a meal plan
4. Check "Add meals to Google Calendar"
5. Click "Accept Meal Plan"
6. You should be redirected to Google's authorization page
7. Authorize and you'll be redirected back

## Troubleshooting

**"redirect_uri_mismatch" error**:

- Make sure `http://localhost:5001/oauth2callback` is added to authorized redirect URIs in Google Cloud Console
- Check that you're running the app on port 5001
- Verify credentials.json has `"redirect_uris"` array with the correct URI

**"Invalid state parameter"**:

- Clear your browser cookies/session
- Restart the Flask app

**"Could not authenticate"**:

- Verify credentials.json exists and is properly formatted
- Check that it has `"web"` section, not `"installed"`
