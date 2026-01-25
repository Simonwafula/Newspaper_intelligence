import json
import os
from dataclasses import dataclass

import httpx

TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
DEFAULT_SCOPE = "offline_access Files.ReadWrite"


@dataclass
class OneDriveUploadResult:
    item_id: str
    size: int | None = None


class OneDriveClient:
    def __init__(
        self,
        client_id: str | None,
        refresh_token: str | None,
        folder_path: str | None = None,
        token_file: str | None = None,
    ) -> None:
        self.client_id = client_id
        self.refresh_token = refresh_token
        self.folder_path = (folder_path or "").strip().strip("/")
        self.token_file = token_file
        self._load_token_file()

        if not self.client_id:
            raise RuntimeError("ONEDRIVE_CLIENT_ID not set")
        if not self.refresh_token:
            raise RuntimeError("ONEDRIVE_REFRESH_TOKEN not set")

    def _load_token_file(self) -> None:
        if not self.token_file or not os.path.exists(self.token_file):
            return

        try:
            with open(self.token_file, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:
            raise RuntimeError("Invalid OneDrive token file") from exc

        if not self.client_id:
            self.client_id = data.get("client_id")
        if not self.refresh_token:
            self.refresh_token = data.get("refresh_token")

    def _save_token_file(self, refresh_token: str) -> None:
        if not self.token_file:
            return

        os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
        payload = {
            "client_id": self.client_id,
            "refresh_token": refresh_token,
        }
        with open(self.token_file, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        try:
            os.chmod(self.token_file, 0o600)
        except OSError:
            pass

    def _get_access_token(self) -> str:
        data = {
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": DEFAULT_SCOPE,
        }
        with httpx.Client(timeout=30) as client:
            response = client.post(TOKEN_URL, data=data)

        if response.status_code >= 400:
            raise RuntimeError(f"OneDrive token refresh failed: {response.text}")

        payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise RuntimeError("OneDrive token refresh missing access_token")

        new_refresh = payload.get("refresh_token")
        if new_refresh and new_refresh != self.refresh_token:
            self.refresh_token = new_refresh
            self._save_token_file(new_refresh)

        return access_token

    def _get_headers(self) -> dict[str, str]:
        token = self._get_access_token()
        return {"Authorization": f"Bearer {token}"}

    def _children_url(self, parent_id: str) -> str:
        if parent_id == "root":
            return f"{GRAPH_BASE_URL}/me/drive/root/children"
        return f"{GRAPH_BASE_URL}/me/drive/items/{parent_id}/children"

    def _find_child_folder(self, parent_id: str, name: str, headers: dict[str, str]) -> str | None:
        params = {
            "$select": "id,name,folder",
            "$top": "200",
        }
        url = self._children_url(parent_id)
        with httpx.Client(timeout=30) as client:
            while url:
                response = client.get(url, headers=headers, params=params)
                if response.status_code >= 400:
                    raise RuntimeError(f"OneDrive folder lookup failed: {response.text}")

                payload = response.json()
                for item in payload.get("value", []):
                    if item.get("name") == name and item.get("folder") is not None:
                        return item.get("id")

                url = payload.get("@odata.nextLink")
                params = None

        return None

    def _create_child_folder(self, parent_id: str, name: str, headers: dict[str, str]) -> str:
        payload = {
            "name": name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail",
        }
        with httpx.Client(timeout=30) as client:
            response = client.post(self._children_url(parent_id), headers=headers, json=payload)

        if response.status_code >= 400:
            raise RuntimeError(f"OneDrive folder create failed: {response.text}")

        return response.json()["id"]

    def _ensure_folder(self, headers: dict[str, str]) -> str | None:
        if not self.folder_path:
            return None

        parent_id = "root"
        for segment in self.folder_path.split("/"):
            if not segment:
                continue
            existing = self._find_child_folder(parent_id, segment, headers)
            parent_id = existing or self._create_child_folder(parent_id, segment, headers)
        return parent_id

    def upload_file(self, local_path: str, filename: str | None = None) -> OneDriveUploadResult:
        file_name = filename or os.path.basename(local_path)
        headers = self._get_headers()
        self._ensure_folder(headers)

        if self.folder_path:
            remote_path = f"/{self.folder_path}/{file_name}"
        else:
            remote_path = f"/{file_name}"

        url = f"{GRAPH_BASE_URL}/me/drive/root:{remote_path}:/content"
        with httpx.Client(timeout=120) as client:
            with open(local_path, "rb") as handle:
                response = client.put(url, headers=headers, content=handle)

        if response.status_code >= 400:
            raise RuntimeError(f"OneDrive upload failed: {response.text}")

        payload = response.json()
        return OneDriveUploadResult(
            item_id=payload["id"],
            size=int(payload.get("size", 0)) if payload.get("size") is not None else None,
        )
