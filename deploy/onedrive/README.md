# OneDrive Archiving (Personal Accounts)

This app can archive original PDF uploads to OneDrive after 5 days. The local cover thumbnail and extracted text remain on the VPS.

## App Registration (Personal Account)
1. Go to Azure Portal → App registrations → New registration.
2. Supported account type: **Personal Microsoft accounts only**.
3. Add a **Mobile and desktop** platform with redirect URI:
   `https://login.microsoftonline.com/common/oauth2/nativeclient`
4. Enable **Allow public client flows**.
5. Copy the **Application (client) ID**.

## Token Generation (Public Client)
1. Open this URL in a browser (replace CLIENT_ID):

```
https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_id=CLIENT_ID&response_type=code&redirect_uri=https%3A%2F%2Flogin.microsoftonline.com%2Fcommon%2Foauth2%2Fnativeclient&response_mode=query&scope=offline_access%20Files.ReadWrite&state=12345
```

2. After login, copy the `code` query parameter.
3. Exchange the code for a refresh token:

```
curl -X POST "https://login.microsoftonline.com/consumers/oauth2/v2.0/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=CLIENT_ID&grant_type=authorization_code&code=AUTH_CODE&redirect_uri=https%3A%2F%2Flogin.microsoftonline.com%2Fcommon%2Foauth2%2Fnativeclient&scope=offline_access%20Files.ReadWrite"
```

## Server Secrets
Store the refresh token in a file on the VPS (outside the repo):

```
/home/mag.mstatilitechnologies.com/.secrets/onedrive-token.json
```

Example contents:

```
{
  "client_id": "your-client-id",
  "refresh_token": "your-refresh-token"
}
```

## Environment Variables
Add these to `/home/mag.mstatilitechnologies.com/.env`:

```
ONEDRIVE_ENABLED=true
ONEDRIVE_TOKEN_FILE=/home/mag.mstatilitechnologies.com/.secrets/onedrive-token.json
ONEDRIVE_FOLDER_PATH=NewspaperArchives
ARCHIVE_AFTER_DAYS=5
```

## Manual Archive
Trigger a manual archive via API:

```
POST /api/editions/{id}/archive
```

## Scheduled Archive
A systemd timer is provided in `deploy/systemd/mag-newspaper-archive.timer`.
