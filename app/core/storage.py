from datetime import datetime, timedelta, timezone
from typing import NamedTuple, Protocol

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from azure.storage.blob.aio import BlobServiceClient




class BlobProperties(NamedTuple):
    size: int
    content_type: str


class Storage(Protocol):
    def upload_url(self, path: str, content_type: str, expires_in: int) -> str:
        """Signed URL the client PUTs to directly."""

    def read_url(self, path: str, expires_in: int) -> str:
        """Signed URL for reading a blob back."""

    async def get_properties(self, path: str) -> BlobProperties | None:
        """None if the blob does not exist. Used to confirm an upload."""

    async def delete(self, path: str) -> None:
        """Clean up abandoned or deleted attachments."""


class AzureBlobStorage:
    def __init__(self, connection_string: str, container: str) -> None:
        self._client = BlobServiceClient.from_connection_string(connection_string)
        self._container = container

    def _sign(self, path: str, permission: BlobSasPermissions, expires_in: int) -> str:
        token = generate_blob_sas(
            account_name=self._client.account_name,
            container_name=self._container,
            blob_name=path,
            account_key=self._client.credential.account_key,
            permission=permission,
            expiry=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        )
        return f"{self._client.get_blob_client(self._container, path).url}?{token}"

    def upload_url(self, path: str, content_type: str, expires_in: int) -> str:
        return self._sign(path, BlobSasPermissions(create=True, write=True), expires_in)

    def read_url(self, path: str, expires_in: int) -> str:
        return self._sign(path, BlobSasPermissions(read=True), expires_in)

    async def get_properties(self, path: str) -> BlobProperties | None:
        blob = self._client.get_blob_client(self._container, path)
        try:
            props = await blob.get_blob_properties()
        except ResourceNotFoundError:
            return None
        return BlobProperties(
            size=props.size,
            content_type=props.content_settings.content_type,
        )

    async def delete(self, path: str) -> None:
        blob = self._client.get_blob_client(self._container, path)
        try:
            await blob.delete_blob()
        except ResourceNotFoundError:
            pass

