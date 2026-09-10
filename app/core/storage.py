import contextlib
from datetime import UTC, datetime, timedelta
from typing import NamedTuple, Protocol

from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob import BlobSasPermissions, ContentSettings, generate_blob_sas
from azure.storage.blob.aio import BlobServiceClient


class BlobProperties(NamedTuple):
    size: int
    content_type: str


class Storage(Protocol):
    async def upload_url(self, path: str, content_type: str, expires_in: int) -> str:
        """Signed URL the client PUTs to directly."""

    async def read_url(self, path: str, expires_in: int) -> str:
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
    """Blob storage with two ways of proving who we are.

    Locally, an account key from a connection string — Azurite understands
    nothing else. In Azure, a managed identity, so no key exists at all.
    """

    def __init__(
        self,
        container: str,
        connection_string: str | None = None,
        account_name: str | None = None,
    ) -> None:
        self._container = container
        self._credential: DefaultAzureCredential | None = None

        if connection_string:
            self._client = BlobServiceClient.from_connection_string(connection_string)
            self._account_key: str | None = self._client.credential.account_key
        else:
            if not account_name:
                raise ValueError("account_name is required when no connection string is set")
            self._credential = DefaultAzureCredential()
            self._client = BlobServiceClient(
                f"https://{account_name}.blob.core.windows.net",
                credential=self._credential,
            )
            self._account_key = None

        resolved = self._client.account_name or account_name
        if not resolved:
            raise ValueError("Could not determine the storage account name")
        self._account_name: str = resolved

    async def _sign(self, path: str, permission: BlobSasPermissions, expires_in: int) -> str:
        expiry = datetime.now(UTC) + timedelta(seconds=expires_in)

        if self._account_key:
            token = generate_blob_sas(
                account_name=self._account_name,
                container_name=self._container,
                blob_name=path,
                account_key=self._account_key,
                permission=permission,
                expiry=expiry,
            )
        else:
            # No key to sign with, so ask Azure for a short-lived delegation key.
            # Backdated slightly to tolerate clock skew between Azure and us.
            start = datetime.now(UTC) - timedelta(minutes=5)
            delegation_key = await self._client.get_user_delegation_key(start, expiry)
            token = generate_blob_sas(
                account_name=self._account_name,
                container_name=self._container,
                blob_name=path,
                user_delegation_key=delegation_key,
                permission=permission,
                expiry=expiry,
                start=start,
            )

        return f"{self._client.get_blob_client(self._container, path).url}?{token}"

    async def upload_url(self, path: str, content_type: str, expires_in: int) -> str:
        return await self._sign(path, BlobSasPermissions(create=True, write=True), expires_in)

    async def read_url(self, path: str, expires_in: int) -> str:
        return await self._sign(path, BlobSasPermissions(read=True), expires_in)

    async def upload(self, path: str, data: bytes, content_type: str) -> None:
        blob = self._client.get_blob_client(self._container, path)
        await blob.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )

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
        if self._credential is not None:
            await self._credential.close()
