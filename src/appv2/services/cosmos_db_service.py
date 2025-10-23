import os
from azure.cosmos import CosmosClient, PartitionKey, exceptions, ContainerProxy, CosmosDict
from .foundry_service import FoundryService
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)


class CosmosDBService:
    def __init__(self):
        endpoint = os.environ.get('COSMOSDB_ENDPOINT')
        key = os.environ.get('COSMOSDB_KEY')
        database_name = os.environ.get('COSMOSDB_DATABASE')
        if not endpoint or not key or not database_name:
            raise EnvironmentError(
                "CosmosDB credentials are not set in environment variables.")
        self.client = CosmosClient(endpoint, key)
        self.database = self.client.get_database_client(database_name)
        self.foundry_service = FoundryService()

    def get_container(self, container_name: str) -> ContainerProxy:
        return self.database.get_container_client(container_name)

    def create_item(self, item: dict, container_name: str) -> CosmosDict:
        container = self.get_container(container_name)
        return container.create_item(body=item)

    def upsert_item(self, item: dict, container_name: str) -> CosmosDict:
        container = self.get_container(container_name)
        return container.upsert_item(body=item)

    def read_item(self, item_id: str, partition_key: PartitionKey, container_name: str) -> CosmosDict:
        container = self.get_container(container_name)
        try:
            return container.read_item(item=item_id, partition_key=partition_key)
        except exceptions.CosmosResourceNotFoundError:
            return None

    def update_item(self, item_id: str, partition_key: PartitionKey, updated_fields: dict, container_name: str) -> CosmosDict:
        container = self.get_container(container_name)
        item = self.read_item(item_id, partition_key, container_name)
        if not item:
            return None
        item.update(updated_fields)
        return container.replace_item(item=item_id, body=item)

    def delete_item(self, item_id: str, partition_key: PartitionKey, container_name: str) -> bool:
        container = self.get_container(container_name)
        try:
            container.delete_item(item=item_id, partition_key=partition_key)
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False

    def check_item_exists(self, item_id: str, container_name: str) -> bool:
        container = self.get_container(container_name=container_name)
        try:
            container.read_item(item=item_id, partition_key=item_id)
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False

    def query_items(self, query: str, container_name: str, parameters: list = None) -> list:
        container = self.get_container(container_name)
        return list(container.query_items(
            query=query,
            parameters=parameters or [],
            enable_cross_partition_query=True
        ))

    def hybrid_search(self, search_terms: str,
                      container_name: str,
                      fields: list[str],
                      full_text_search_field: str = 'name',
                      top_count: int = 5) -> list:
        """
        Perform a hybrid search using full-text search and vector search.
        This is a placeholder for the actual implementation.
        """

        # Generate the embedding for the search terms
        search_embedding = self.foundry_service.generate_embedding(
            search_terms)
        # Split search terms to a quoted, comma-separated string for full-text search
        full_text = ', '.join(f'"{word}"' for word in search_terms.split())
        query_fields = f"c.{', c.'.join(fields)}"
        hybrid_query = f"""
            SELECT TOP {top_count} {query_fields}, 
            VectorDistance(c.embedding, {search_embedding}) AS similarity_score
            FROM c
            ORDER BY RANK RRF(VectorDistance(c.embedding, {search_embedding}), FullTextScore(c.{full_text_search_field}, '@full_text'))
        """

        container = self.get_container(container_name)

        response = container.query_items(
            query=hybrid_query,
            parameters=[
                {
                    "name": "@full_text",
                    "value": full_text
                }
            ],
            enable_cross_partition_query=True,
            populate_query_metrics=True)

        return list(response)

# Global instance
cosmos_db_service = CosmosDBService()