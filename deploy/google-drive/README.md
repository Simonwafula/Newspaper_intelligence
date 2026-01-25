# Google Drive Archiving

This app archives original PDF uploads to Google Drive after 5 days. The local cover thumbnail and extracted text remain on the VPS.

## Service Account Setup
1. Create a Google Cloud project.
2. Enable the Google Drive API.
3. Create a service account and download the JSON key.
4. Create a Shared Drive or a folder inside a Shared Drive for archives, then share it with the service account email (Content manager).
   - Service accounts do not have My Drive storage quota, so Shared Drive storage is required.

## Server Secrets
Store the service account file on the VPS (outside the repo):

```
/home/mag.mstatilitechnologies.com/.secrets/drive-service-account.json
```

## Environment Variables
Add these to `/home/mag.mstatilitechnologies.com/.env`:

```
GDRIVE_ENABLED=true
GDRIVE_FOLDER_ID=your_drive_folder_id
GDRIVE_SERVICE_ACCOUNT_FILE=/home/mag.mstatilitechnologies.com/.secrets/drive-service-account.json
ARCHIVE_AFTER_DAYS=5
```

## Manual Archive
Trigger a manual archive via API:

```
POST /api/editions/{id}/archive
```

## Scheduled Archive
A systemd timer is provided in `deploy/systemd/mag-newspaper-archive.timer`.
