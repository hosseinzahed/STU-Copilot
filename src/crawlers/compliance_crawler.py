import logging
import hashlib
from typing import List
from storage_account_service import StorageAccountService
import json
from data_models import ComplianceItem
from markitdown import MarkItDown

# Configure logging
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger("azure.functions")

categories = [
    # "terms"
    "privacy",
    # "dpa",
    # "sla",
    # "service_assurance_trust",
    
    
    # "supplier_vendor_management",
    # "risk_management_governance",
    # "data_residency_global_infrastructure",
    # "github_platform_compliance",
    # "ai_responsible_use",
    # "linkedin_legal_privacy"
]


class ComplianceCrawler:
    """Compliance Crawler to process compliance documents and store in Storage Account."""

    def __init__(self,
                 storage_account_service: StorageAccountService):
        """Initialize the Compliance Crawler."""
        self.storage_account_service = storage_account_service

    def load_references(self) -> List[ComplianceItem]:
        """Load compliance references from a JSON file.
        Returns:
            List[ComplianceItem]: A list of compliance items.
        """
        # Load compliance references from a JSON file
        with open('compliance_references.json', 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Convert to ComplianceItem instances
        compliance_items = [
            ComplianceItem(**{k: v for k, v in item.items()
                           if k in ['category', 'title', 'url']})
            for item in data
        ]
        return compliance_items

    def store_compliance_document(self, item: ComplianceItem, content: str) -> None:
        """Store the compliance document in CosmosDB.
        Args:
            item (ComplianceItem): The compliance item metadata.
            content (str): The Markdown content of the compliance document.
        """
        # Create a unique ID for the document
        doc_id = hashlib.md5(item.url.encode('utf-8')).hexdigest()

        # Append metadata to the markdown content
        content = f"---\ncategory: {item.category}\ntitle: {item.title}\nurl: {item.url}\n---\n\n" + content

        # Store the document in compliance folder locally
        with open(f'compliance_docs/{item.category}/{doc_id}.md', 'w', encoding='utf-8') as file:
            file.write(content)

        # # Store the document in Azure Blob Storage
        # self.storage_account_service.upload_blob(
        #     container_name=item.category,
        #     blob_name=f"{doc_id}.md",
        #     data=content.encode('utf-8'),
        #     overwrite=True
        # )

        logger.info(f"Stored document with id: {doc_id}")

    def run(self):
        """Main function to run the Compliance crawler."""
        logger.info("Compliance crawler started.")

        # Ensure compliance_docs directory exists for each category
        import os
        for category in categories:
            os.makedirs(f'compliance_docs/{category}', exist_ok=True)

        # Load compliance references
        compliance_items = self.load_references()
        
        # Initialize MarkItDown
        md = MarkItDown()

        for item in compliance_items:
            try:
                logger.info(f"Processing item: {item.title} - {item.url}")

                # Convert URL content to Markdown
                md_result = md.convert_url(url=item.url)

                # Store the compliance document
                self.store_compliance_document(item, md_result.markdown)
            except Exception as e:
                logger.error(
                    f"Error processing item: '{item.title}' - '{item.url}': {e}")

        logger.info("Compliance crawler finished.")
