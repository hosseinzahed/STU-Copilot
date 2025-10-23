import os
from openai import AzureOpenAI 
from openai.types import CreateEmbeddingResponse
import json
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


class FoundryService:
    """Service to interact with Azure OpenAI Foundry for embeddings and chat completions."""

    def __init__(self):
        self.endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
        self.api_key = os.environ.get('AI_FOUNDRY_KEY')
        self.embedding_model = "text-embedding-3-small"
        self.chat_model = "gpt-4.1-nano"
        self.api_version = "2024-12-01-preview"

        if not self.endpoint or not self.api_key:
            raise EnvironmentError(
                "Azure OpenAI credentials are not set in environment variables.")

        self.embedding_client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            azure_deployment=self.embedding_model,
            api_version=self.api_version,
            api_key=self.api_key
        )

        self.chat_client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            azure_deployment=self.chat_model,
            api_version=self.api_version,
            api_key=self.api_key
        )

    def generate_embedding(self, text: str) -> list:
        """Get the embedding for a given text."""
        if not text:
            return []

        response: CreateEmbeddingResponse = self.embedding_client.embeddings.create(
            input=text,
            model=self.embedding_model,
            encoding_format="float",
            dimensions=1536,
        )
        return response.data[0].embedding if response.data else []

    def summarize_and_generate_keywords(self, text: str) -> tuple:
        """Summarize the given text using a GPT model and extract keywords.

        Args:
            text (str): The text to summarize and extract keywords from

        Returns:
            tuple: (summary, keywords) where summary is the summarized text and 
                  keywords is a comma-separated string of keywords
        """
        if not text:
            return ("", "")

        try:
            response = self.chat_client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": """
                            Your task is to process the following text in two steps:
                            
                            1. Summarize the text into less than 2000 characters, keeping words as similar as possible to the original text.
                               - Remove code blocks, markdown formatting, and unnecessary whitespace
                               - Do not include explanations or comments
                            
                            2. Extract exactly 5 keywords that best represent the main topics from the content.
                            
                            IMPORTANT: You must respond ONLY with a valid JSON object using this exact format:
                            {
                                "summary": "<your summarized text>",
                                "keywords": "<five keywords separated by commas>"
                            }
                            
                            Do not include any text before or after the JSON object. No markdown formatting, no code blocks, no explanations.
                        """
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                max_tokens=4096,
                timeout=30  # Add timeout for better reliability
            )

            # Extract content from response
            content = response.choices[0].message.content if response.choices else ''

            # Default values in case parsing fails
            summary = content
            keywords = ""

            # Try to parse as JSON if content looks like JSON
            if content and content.strip():
                # Strip any potential non-JSON leading/trailing characters
                content_stripped = content.strip()
                json_start = content_stripped.find('{')
                json_end = content_stripped.rfind('}')

                if json_start >= 0 and json_end > json_start:
                    try:
                        json_content = content_stripped[json_start:json_end+1]
                        data = json.loads(json_content)
                        summary = data.get("summary", "")
                        keywords = data.get("keywords", "")
                        if not summary and not keywords:
                            logger.warning(
                                "JSON parsed but missing expected fields")
                    except json.JSONDecodeError as e:
                        logger.warning(
                            f"Failed to parse model response as JSON: {e}")
                else:
                    logger.warning(
                        "Model response does not contain valid JSON structure")
            elif not content:
                logger.warning("Model response is empty.")
            else:
                logger.warning("Model response is not in expected JSON format")

            return summary, keywords

        except Exception as e:
            logger.error(f"Error during text summarization: {e}")
            return ("", "")

# Global instance
foundry_service = FoundryService()