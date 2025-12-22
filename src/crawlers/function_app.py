import azure.functions as func
import logging
from dotenv import load_dotenv
from cosmos_db_service import CosmosDBService
from foundry_service import FoundryService
from storage_account_service import StorageAccountService

# Load environment variables from .env file
load_dotenv(override=True)

# Configure logging
# logging.basicConfig(level=logging.INFO)
# logging.getLogger("azure.functions")
logging.getLogger("azure.cosmos").setLevel(logging.CRITICAL)

# Initialize the Function App
app = func.FunctionApp()

# Initialize services
cosmos_db_service = CosmosDBService()
foundry_service = FoundryService()
storage_account_service = StorageAccountService()


@app.timer_trigger(schedule="0 0 0 * * *",  # Run every day at midnight
                   arg_name="timer_request",
                   run_on_startup=False,
                   use_monitor=False)
def github_crawler_func(timer_request: func.TimerRequest) -> None:
    logging.info('GitHub crawler function started.')
    from github_crawler import GitHubCrawler
    github_crawler = GitHubCrawler(cosmos_db_service=cosmos_db_service,
                                   foundry_service=foundry_service)
    github_crawler.run()
    logging.info('GitHub crawler function finished.')


@app.timer_trigger(schedule="0 0 0 * * *",  # Run every day at midnight
                   arg_name="timer_request",
                   run_on_startup=False,
                   use_monitor=False)
def blogs_crawler_func(timer_request: func.TimerRequest) -> None:
    logging.info('Blogs crawler function started.')
    from blogs_crawler import BlogsCrawler
    blogs_crawler = BlogsCrawler(cosmos_db_service=cosmos_db_service,
                                 foundry_service=foundry_service)
    blogs_crawler.run()
    logging.info('Blogs crawler function finished.')


@app.timer_trigger(schedule="0 0 0 * * *",  # Run every day at midnight
                   arg_name="timer_request",
                   run_on_startup=False,
                   use_monitor=False)
def compliance_crawler_func(timer_request: func.TimerRequest) -> None:
    logging.info('Compliance crawler function started.')
    from compliance_crawler import ComplianceCrawler
    compliance_crawler = ComplianceCrawler(
        storage_account_service=storage_account_service
    )
    compliance_crawler.run()
    logging.info('Compliance crawler function finished.')
