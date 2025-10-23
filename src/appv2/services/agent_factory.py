import os
import logging
from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from .cache_service import cache_service
from .tool_factory import tools

# Configure logging
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating chat completion agents."""

    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AI_FOUNDRY_KEY")
        if not self.endpoint or not self.api_key:
            raise EnvironmentError(
                "Missing Azure Open AI endpoint or API key.")

        self.agents = {}

    def create_client(self, model_name: str) -> AzureOpenAIChatClient:
        """Create an Azure OpenAI chat client."""
        return AzureOpenAIChatClient(
            endpoint=self.endpoint,
            api_key=self.api_key,
            deployment_name=model_name
        )

    def get_questioner_agent(self) -> ChatAgent:
        """Create a questioner agent with the necessary plugins."""
        agent_name = "questioner_agent"
        model_name = "gpt-4.1-nano"

        # Create a chat client instance
        client = self.create_client(model_name)

        # Create the agent
        questioner_agent = ChatAgent(
            chat_client=client,
            description="Questioner agent that asks clarifying questions to gather more information.",
            name=agent_name,
            instructions=cache_service.load_prompt(agent_name)
        )

        return questioner_agent

    def get_github_agent(self) -> ChatAgent:
        """Create a GitHub agent with the necessary plugins."""
        agent_name = "github_agent"
        model_name = "gpt-4.1-mini"

        # Create a chat client instance
        client = self.create_client(model_name)

        # Create the agent
        github_agent = ChatAgent(
            chat_client=client,
            name=agent_name,
            description="GitHub agent that fetches relevant information from GitHub repositories.",
            instructions=cache_service.load_prompt(agent_name),
            tools=[tools.search_github_repositories]
        )

        return github_agent

    def get_microsoft_docs_agent(self) -> ChatAgent:
        """Create a Microsoft Docs agent with the necessary plugins."""
        agent_name = "microsoft_docs_agent"
        model_name = "gpt-4.1"

        # Create a chat client instance
        client = self.create_client(model_name)

        # Create the agent
        microsoft_docs_agent = ChatAgent(
            chat_client=client,
            name=agent_name,
            description="Microsoft Docs agent that fetches relevant documentation from Microsoft Docs.",
            instructions=cache_service.load_prompt(agent_name),
            tools=[tools.search_microsoft_docs]
        )

        return microsoft_docs_agent

    def get_blog_posts_agent(self) -> ChatAgent:
        """Create a Blog Posts agent with the necessary plugins."""
        agent_name = "blog_posts_agent"
        model_name = "gpt-4.1-mini"

        # Create a chat client instance
        client = self.create_client(model_name)

        # Create the agent
        blog_posts_agent = ChatAgent(
            chat_client=client,
            name=agent_name,
            description="Blog Posts agent that searches for relevant blog posts.",
            instructions=cache_service.load_prompt(agent_name),
            tools=[tools.search_blog_posts]
        )

        return blog_posts_agent

    def get_seismic_agent(self) -> ChatAgent:
        """Create a Seismic agent with the necessary plugins."""
        agent_name = "seismic_agent"
        model_name = "gpt-4.1-mini"

        # Create a chat client instance
        client = self.create_client(model_name)

        # Create the agent
        seismic_agent = ChatAgent(
            chat_client=client,
            name=agent_name,
            description="Seismic agent that searches for relevant presentations and PowerPoints.",
            instructions=cache_service.load_prompt(agent_name),
            tools=[tools.search_seismic_presentations]
        )

        return seismic_agent

    def get_bing_search_agent(self) -> ChatAgent:
        """Create a Bing Search agent with the necessary plugins."""
        agent_name = "bing_search_agent"
        model_name = "gpt-4.1-mini"

        # Create a chat client instance
        client = self.create_client(model_name)

        # Create the agent
        bing_search_agent = ChatAgent(
            chat_client=client,
            name=agent_name,
            description="Bing Search agent that performs web searches to find relevant information.",
            instructions=cache_service.load_prompt(agent_name),
            tools=[tools.search_by_bing]
        )

        return bing_search_agent

    def get_github_docs_search_agent(self) -> ChatAgent:
        """Create a GitHub Docs Search agent with the necessary plugins."""
        agent_name = "github_docs_search_agent"
        model_name = "gpt-4.1-mini"

        # Create a chat client instance
        client = self.create_client(model_name)

        # Create the agent
        github_docs_search_agent = ChatAgent(
            chat_client=client,
            name=agent_name,
            description="GitHub Docs Search agent that performs searches to find relevant documentation.",
            instructions=cache_service.load_prompt(agent_name),
            tools=[tools.search_github_docs]
        )

        return github_docs_search_agent

    def get_aws_docs_agent(self) -> ChatAgent:
        """Create an AWS Docs agent with the necessary plugins."""
        agent_name = "aws_docs_agent"
        model_name = "gpt-4.1-mini"

        # Create a chat client instance
        client = self.create_client(model_name)

        # Create the agent
        aws_docs_agent = ChatAgent(
            chat_client=client,
            name=agent_name,
            description="AWS Docs agent that fetches relevant documentation from AWS Docs.",
            instructions=cache_service.load_prompt(agent_name),
            tools=[tools.search_aws_docs]
        )

        return aws_docs_agent

    def get_architect_agent(self) -> ChatAgent:
        """Create an architect agent with the necessary plugins."""
        agent_name = "architect_agent"
        model_name = "o3-mini"

        # Create a chat client instance
        client = self.create_client(model_name)

        # Create the agent
        architect_agent = ChatAgent(
            chat_client=client,
            name=agent_name,
            instructions=cache_service.load_prompt(agent_name),
            tools=[
                tools.search_microsoft_docs,
                tools.search_by_bing
            ]
        )

        return architect_agent

    def get_summarizer_agent(self) -> ChatAgent:
        """Create a summarizer agent with the necessary plugins."""
        agent_name = "summarizer_agent"
        model_name = "gpt-4.1-mini"

        # Create a chat client instance
        client = self.create_client(model_name)

        # Create the agent
        summarizer_agent = ChatAgent(
            chat_client=client,
            name=agent_name,
            description="Summarizer agent that condenses information into concise summaries.",
            instructions=cache_service.load_prompt(agent_name)
        )

        return summarizer_agent

    def get_explainer_agent(self) -> ChatAgent:
        """Create an explainer agent with the necessary plugins."""
        agent_name = "explainer_agent"
        model_name = "gpt-4.1"

        # Create a chat client instance
        client = self.create_client(model_name)

        # Create the agent
        explainer_agent = ChatAgent(
            chat_client=client,
            name=agent_name,
            description="Explainer agent that provides detailed explanations of concepts.",
            instructions=cache_service.load_prompt(agent_name)
        )

        return explainer_agent


# Global instance
agent_factory = AgentFactory()
