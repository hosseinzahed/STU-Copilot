from azure.storage.blob import BlobServiceClient, generate_container_sas, ContainerSasPermissions
from typing import Any
import os
import logging
from datetime import datetime, timedelta, timezone
from .cache_service import cache_service

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class StorageAccountService:
    def __init__(self):
        self._account_name = os.getenv("APP_AZURE_STORAGE_ACCOUNT")
        self._account_key = os.getenv("APP_AZURE_STORAGE_ACCESS_KEY")
        
        _connection_string = (
            f"DefaultEndpointsProtocol=https;"
            f"AccountName={self._account_name};"
            f"AccountKey={self._account_key};"
            f"EndpointSuffix=core.windows.net"
        )
        self._blob_service_client = BlobServiceClient.from_connection_string(
            _connection_string)

    def upload_blob(self, container_name: str, blob_name: str, data: Any, overwrite: bool = True):
        container_client = self._blob_service_client.get_container_client(
            container_name)
        container_client.upload_blob(
            name=blob_name, data=data, overwrite=overwrite)

    def download_blob(self, container_name: str, blob_name: str) -> bytes:
        container_client = self._blob_service_client.get_container_client(
            container_name)
        blob_client = container_client.get_blob_client(blob_name)
        return blob_client.download_blob().readall()

    def list_blobs(self, container_name: str):
        container_client = self._blob_service_client.get_container_client(
            container_name)
        return [blob.name for blob in container_client.list_blobs()]

    def delete_blob(self, container_name: str, blob_name: str):
        container_client = self._blob_service_client.get_container_client(
            container_name)
        container_client.delete_blob(blob_name)

    def generate_sas_token(self, container_name: str, expiry_weeks: int = 1) -> str:
        # Check cache first
        cached_token = cache_service.get_sas_token_cache(container_name)
        if cached_token:
            return cached_token

        # Generate new SAS token
        sas_token = generate_container_sas(
            account_name=self._account_name,
            container_name=container_name,
            account_key=self._account_key,
            permission=ContainerSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(weeks=expiry_weeks)
        )
        # Cache the new token
        cache_service.set_sas_token_cache(container_name, sas_token)
        return sas_token


# Global instance
storage_account_service = StorageAccountService()
