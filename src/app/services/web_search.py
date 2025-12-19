"""
Web Search functionality for AI agents.

This module provides a high-performance web search class that reuses connections
and agent instances for faster query execution.
"""

import os
from types import SimpleNamespace
from typing import Optional
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, WebSearchPreviewTool, ApproximateLocation


class WebSearchService:
    """
    High-performance web search service that reuses connections and agents.

    This class maintains persistent connections and agent instances to avoid
    the overhead of creating/deleting resources on every query.
    """

    def __init__(
        self,
        model: str = "gpt-4.1-nano",
        name: str = "bing_search_agent",
        instructions: str = "You are a helpful assistant that can search the web",
        credential: Optional[DefaultAzureCredential] = None,
    ):
        """
        Initialize the WebSearchService.

        Args:
            model: The AI model deployment name (default: "gpt-4.1-nano")
            agent_instructions: Instructions for the agent behavior
            credential: Azure credential (defaults to DefaultAzureCredential)
        """
        self.name = name
        self.model = model
        self.agent_instructions = instructions
        self.endpoint = os.environ["AI_FOUNDRY_PROJECT_ENDPOINT"]
        self.credential = credential if credential is not None else DefaultAzureCredential()

        # Initialize clients (reused across requests)
        self.project_client = AIProjectClient(
            endpoint=self.endpoint, credential=self.credential)
        self.openai_client = self.project_client.get_openai_client()

        # Create agent once (reused across requests)
        self.agent = None
        self._initialize_agent()

    def _initialize_agent(self):
        """Initialize the web search agent."""
        tool = WebSearchPreviewTool(
            user_location=ApproximateLocation(
                country="DK",                
                city="Copenhagen"
            ),
            search_context_size="medium")

        self.agent = self.project_client.agents.create_version(
            agent_name="WebSearchAgent",
            definition=PromptAgentDefinition(
                model=self.model,
                instructions=self.agent_instructions,
                tools=[tool],
            ),
            description="Agent for web search operations.",
        )

    async def run_stream(self, messages: list[str]):
        """
        Perform a web search query as an async generator.

        Args:
            messages: The list of messages in the conversation

        Yields:
            str: Chunks of the agent's response text

        Raises:
            Exception: Any Azure AI Projects or OpenAI client exceptions
        """
        try:
            # Create a new conversation for this query
            conversation = self.openai_client.conversations.create()
            
            # Send the query and get response
            response = self.openai_client.responses.create(
                conversation=conversation.id,
                input=messages,
                extra_body={
                    "agent": {
                        "name": self.agent.name,
                        "type": "agent_reference"
                    }
                },
            )

            yield SimpleNamespace(text=response.output_text)

        except Exception as e:
            raise Exception(f"Web search failed: {str(e)}") from e

    def close(self):
        """Clean up resources."""
        try:
            if self.agent:
                self.project_client.agents.delete_version(
                    agent_name=self.agent.name,
                    agent_version=self.agent.version
                )
        except Exception:
            pass  # Ignore cleanup errors

        try:
            if hasattr(self.openai_client, 'close'):
                self.openai_client.close()
        except Exception:
            pass

        try:
            if hasattr(self.project_client, 'close'):
                self.project_client.close()
        except Exception:
            pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


# Global singleton instance
_global_service: Optional[WebSearchService] = None


def get_web_search_agent(
    model: str,
    name: str,
    instructions: str
) -> WebSearchService:
    """
    Create and return a web search agent.

    Args:
        model: The AI model deployment name
        name: The name of the agent
        instructions: Instructions for the agent behavior
    Returns:
        WebSearchService: An instance of the web search service
    """
    global _global_service

    if _global_service is None:
        _global_service = WebSearchService(
            name=name,
            model=model,
            instructions=instructions)
    return _global_service


def perform_web_search(query: str) -> str:
    """
    Perform a web search query.

    This function uses a singleton service that reuses connections and agents
    for optimal performance.

    Args:
        query: The search query to execute

    Returns:
        str: The agent's response text

    Example:
        >>> result = perform_web_search("What is the weather today?")
        >>> print(result)
    """
    global _global_service

    if _global_service is None:
        _global_service = WebSearchService(
            model="gpt-4.1-nano",
            agent_instructions="You are a helpful assistant that can search the web"
        )

    return _global_service.run_stream(query)


# For backwards compatibility and testing
if __name__ == "__main__":
    from dotenv import load_dotenv
    import time

    load_dotenv()

    queries = [
        "Which search engine are you using?",
        "What is the weather today in Copenhagen?",
        "What are the top trending topics on social media today?",
        "What is the current stock price of Microsoft?",
        "What are the latest AI breakthroughs in 2025?"
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n=== Query {i} ===")
        start_time = time.time()
        result = perform_web_search(query)
        elapsed = time.time() - start_time
        print(f"Response time: {elapsed:.2f} seconds")
        print(f"Query: {query}")
        print(f"Response: {result[:150]}...")

        if i < len(queries):
            time.sleep(1)
