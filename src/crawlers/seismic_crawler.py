import hashlib
import os
import json
from typing import List
from data_models import SeismicContent
from foundry_service import FoundryService
from cosmos_db_service import CosmosDBService
import logging
from pathlib import Path

# Configure logging
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logger = logging.getLogger("azure.functions")

# Define the path to the seismic data source
# This should point to the processed seismic data file
data_source = str(Path(__file__).resolve()
                  .parents[2] / '.temp' / 'xxx-processed.json')


class SeismicCrawler:
    def __init__(self, cosmos_db_service: CosmosDBService,
                 foundry_service: FoundryService):
        """Initialize the Seismic Crawler with a data source."""

        # Ensure the data source exists
        if not os.path.exists(data_source):
            raise FileNotFoundError(
                f"Data source file not found: {data_source}")

        self.data_source = data_source
        self.foundry_service = foundry_service
        self.cosmos_db_service = cosmos_db_service

    def generate_item_id(self, url: str) -> str:
        """Generate a unique ID for a blog post based on URL."""
        content = f"{url}"
        return hashlib.md5(content.encode()).hexdigest()

    def fetch_data(self) -> List[SeismicContent]:
        """Fetch seismic data from the data source."""

        # Load seismic json data and parse it into SeismicContent objects
        with open(self.data_source, 'r', encoding='utf-8') as file:
            seismic_data = json.load(file)

        # Parse the loaded data into SeismicContent objects
        return [SeismicContent.from_dict(item) for item in seismic_data]

    def process_data(self, seismic_data: List[SeismicContent]):
        """Process the fetched seismic data."""

        for item in seismic_data:
            try:                

                # Check if the item already exists in CosmosDB
                if self.cosmos_db_service.check_item_exists(item.id, "seismic-contents"):
                    logger.info(
                        f"Seismic content '{item.name}' already exists in CosmosDB.")
                    continue

                logger.info(f"Processing Seismic content: {item.name}")
                
                # Generate embedding for the seismic content
                embedding_content = item.name
                item.embedding = self.foundry_service.generate_embedding(
                    embedding_content)

                # Add tags to the seismic content
                if item.products and item.products != "--":
                    item.tags = item.products
                
                # Save the processed seismic content to CosmosDB
                self.cosmos_db_service.upsert_item(
                    item=item.to_dict(),
                    container_name="seismic-contents"
                )

            except Exception as e:
                logger.error(
                    f"Error processing seismic content '{item.name}': {e}")

    

    def run(self):
        """Run the Seismic Crawler."""
        try:
            logger.info("Seismic Crawler started.")

            # Fetch and process seismic data
            seismic_data = self.fetch_data()

            if not seismic_data:
                logger.warning("No seismic data found to process.")
                return

            # Process the fetched seismic data
            self.process_data(seismic_data)

            logger.info(
                f"Seismic Crawler finished processing {len(seismic_data)} items.")

        except Exception as e:
            logger.error(f"An error occurred processing seismic data: {e}")
