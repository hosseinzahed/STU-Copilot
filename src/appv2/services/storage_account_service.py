# from azure.storage.blob import BlobServiceClient
# from typing import Any
# import os
# import logging

# # Configure logging
# logging.basicConfig(level=logging.WARNING)
# logger = logging.getLogger(__name__)


# class StorageAccountService:
#     def __init__(self):
#         account_name = os.getenv("APP_AZURE_STORAGE_ACCOUNT")
#         account_key = os.getenv("APP_AZURE_STORAGE_ACCESS_KEY")

#         if not account_name or not account_key:
#             raise EnvironmentError(
#                 "Storage account name or key is not set in environment variables.")

#         connection_string = (
#             f"DefaultEndpointsProtocol=https;"
#             f"AccountName={account_name};"
#             f"AccountKey={account_key};"
#             f"EndpointSuffix=core.windows.net"
#         )
#         self.blob_service_client = BlobServiceClient.from_connection_string(
#             connection_string)

#     def upload_blob(self, container_name: str, blob_name: str, data: Any, overwrite: bool = True):
#         container_client = self.blob_service_client.get_container_client(
#             container_name)
#         container_client.upload_blob(
#             name=blob_name, data=data, overwrite=overwrite)

#     def download_blob(self, container_name: str, blob_name: str) -> bytes:
#         container_client = self.blob_service_client.get_container_client(
#             container_name)
#         blob_client = container_client.get_blob_client(blob_name)
#         return blob_client.download_blob().readall()

#     def list_blobs(self, container_name: str):
#         container_client = self.blob_service_client.get_container_client(
#             container_name)
#         return [blob.name for blob in container_client.list_blobs()]

#     def delete_blob(self, container_name: str, blob_name: str):
#         container_client = self.blob_service_client.get_container_client(
#             container_name)
#         container_client.delete_blob(blob_name)

# # Global instance
# storage_account_service = StorageAccountService()
