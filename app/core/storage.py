import contextlib
from datetime import UTC, datetime, timedelta
from typing import NamedTuple, Protocol

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobSasPermissions, ContentSettings, generate_blob_sas
from azure.storage.blob.aio import BlobServiceClient


class BlobProperties(NamedTuple):
    size: int
    content_type: str


class Storage(Protocol):
    def upload_url(self, path: str, content_type: str, expires_in: int) -> str:
        """Signed URL the client PUTs to directly."""

    def read_url(self, path: str, expires_in: int) -> str:
        """Signed URL for reading a blob back."""

    async def upload(self, path: str, data: bytes, content_type: str) -> None:
        """Upload bytes directly. Used by the worker for exports."""

    async def get_properties(self, path: str) -> BlobProperties | None:
        """None if the blob does not exist. Used to confirm an upload."""

    async def delete(self, path: str) -> None:
        """Clean up abandoned or deleted attachments."""

    async def aclose(self) -> None:
        """Release the underlying HTTP connections."""



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
            expiry=datetime.now(UTC) + timedelta(seconds=expires_in),
        )
        return f"{self._client.get_blob_client(self._container, path).url}?{token}"

    def upload_url(self, path: str, content_type: str, expires_in: int) -> str:
        return self._sign(path, BlobSasPermissions(create=True, write=True), expires_in)
    
    async def upload(self, path: str, data: bytes, content_type: str) -> None:
        """Upload bytes directly. Used by the worker for exports."""
        blob = self._client.get_blob_client(self._container, path)
        await blob.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
    
    
   
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
        with contextlib.suppress(ResourceNotFoundError):
            await blob.delete_blob()
            
    async def aclose(self) -> None:
        await self._client.close()
