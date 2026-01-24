import os
from dataclasses import dataclass

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


@dataclass
class DriveUploadResult:
    file_id: str
    size: int | None = None


class DriveClient:
    def __init__(self, service_account_file: str, folder_id: str | None = None):
        if not os.path.exists(service_account_file):
            raise FileNotFoundError(f"Drive service account file not found: {service_account_file}")

        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=["https://www.googleapis.com/auth/drive.file"],
        )
        self.service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        self.folder_id = folder_id

    def upload_file(self, local_path: str, filename: str | None = None) -> DriveUploadResult:
        file_name = filename or os.path.basename(local_path)
        metadata: dict[str, object] = {"name": file_name}
        if self.folder_id:
            metadata["parents"] = [self.folder_id]

        media = MediaFileUpload(local_path, mimetype="application/pdf", resumable=True)
        response = (
            self.service.files()
            .create(body=metadata, media_body=media, fields="id,size")
            .execute()
        )
        return DriveUploadResult(file_id=response["id"], size=int(response.get("size", 0)))
