import os
import logging
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient, AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential
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
                "AZURE_OPENAI_ENDPOINT or AI_FOUNDRY_KEY environment variable is not set.")

        self.project_endpoint = os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
        if not self.project_endpoint:
            raise EnvironmentError(
                "AI_FOUNDRY_PROJECT_ENDPOINT environment variable is not set.")

        self.bing_search_agent_id = os.getenv("BING_SEARCH_AGENT_ID")
        if not self.bing_search_agent_id:
            raise EnvironmentError(
                "BING_SEARCH_AGENT_ID environment variable is not set.")

        self.github_token = os.getenv("GITHUB_TOKEN")
        if not self.github_token:
            raise EnvironmentError(
                "GITHUB_TOKEN environment variable is not set.")

        self.chat_client = AzureOpenAIChatClient(
            endpoint=self.endpoint,
            api_key=self.api_key,
            deployment_name="gpt-4.1-mini"
        )

        self.agents = {
            "questioner_agent": self.get_questioner_agent(),
            "github_agent": self.get_github_agent(),
            "github_docs_search_agent": self.get_github_docs_search_agent(),
            "microsoft_docs_agent": self.get_microsoft_docs_agent(),
            "blog_posts_agent": self.get_blog_posts_agent(),
            "seismic_agent": self.get_seismic_agent(),
            "bing_search_agent": self.get_bing_search_agent(),
            "architect_agent": self.get_architect_agent(),
            "summarizer_agent": self.get_summarizer_agent(),
            "aws_docs_agent": self.get_aws_docs_agent(),
            "explainer_agent": self.get_explainer_agent(),
        }
        self.agents["orchestrator_agent"] = self.get_orchestrator_agent()

    def get_agents(self) -> dict[str, ChatAgent]:
        """Get all agents."""
        return self.agents

    def get_questioner_agent(self) -> ChatAgent:
        """Create a questioner agent with the necessary plugins."""
        agent_name = "questioner_agent"
        model_name = "gpt-4.1-nano"

        # Create the agent
        questioner_agent = ChatAgent(
            chat_client=self.chat_client,
            description="Questioner agent that asks clarifying questions to gather more information.",
            name=agent_name,
            model_id=model_name,
            instructions=cache_service.load_prompt(agent_name)
        )

        return questioner_agent

    def get_orchestrator_agent(self) -> ChatAgent:
        """Create an orchestrator agent with the necessary plugins."""
        agent_name = "orchestrator_agent"
        model_name = "gpt-5-mini"

        # Create the agent
        orchestrator_agent = ChatAgent(
            chat_client=self.chat_client,
            name=agent_name,
            description="Orchestrator agent that manages the workflow of other agents.",
            instructions=cache_service.load_prompt(agent_name),
            model_id=model_name,
            tools=[
                self.agents.get("questioner_agent").as_tool(),
                self.agents.get("microsoft_docs_agent").as_tool(),
                self.agents.get("github_agent").as_tool(),
                self.agents.get("github_docs_search_agent").as_tool(),
                self.agents.get("blog_posts_agent").as_tool(),
                self.agents.get("seismic_agent").as_tool(),
                self.agents.get("bing_search_agent").as_tool(),
                self.agents.get("aws_docs_agent").as_tool(),
                self.agents.get("explainer_agent").as_tool(),
            ]
        )

        return orchestrator_agent

    def get_github_agent(self) -> ChatAgent:
        """Create a GitHub agent with the necessary plugins."""
        agent_name = "github_agent"
        model_name = "gpt-4.1-mini"

        # Create the agent
        github_agent = ChatAgent(
            chat_client=self.chat_client,
            name=agent_name,
            description="GitHub agent that fetches relevant information from GitHub repositories.",
            instructions=cache_service.load_prompt(agent_name),
            model_id=model_name,
            tools=[tools.search_github_repositories]
        )

        return github_agent

    def get_microsoft_docs_agent(self) -> ChatAgent:
        """Create a Microsoft Docs agent with the necessary plugins."""
        agent_name = "microsoft_docs_agent"
        model_name = "gpt-5.2-chat"

        mcp_server = MCPStreamableHTTPTool(
            name="Microsoft Docs MCP Tool",
            url="https://learn.microsoft.com/api/mcp"
        )

        microsoft_docs_agent = ChatAgent(
            chat_client=AzureOpenAIChatClient(
                endpoint=self.endpoint,
                api_key=self.api_key,
                deployment_name=model_name
            ),
            name=agent_name,
            instructions="""
                You are a helpful assistant that provides information from Microsoft Docs.
                Always Use the provided tool to search for relevant documentation based on user queries.
                Provide accurate and concise information and also cite your sources with appropriate links.
                Provide suggestions for related topics the user might find useful.
            """,
            tools=[mcp_server]
        )

        return microsoft_docs_agent

    def get_blog_posts_agent(self) -> ChatAgent:
        """Create a Blog Posts agent with the necessary plugins."""
        agent_name = "blog_posts_agent"
        model_name = "gpt-4.1-mini"

        # Create the agent
        blog_posts_agent = ChatAgent(
            chat_client=self.chat_client,
            name=agent_name,
            description="Blog Posts agent that searches for relevant blog posts.",
            instructions=cache_service.load_prompt(agent_name),
            model_id=model_name,
            tools=[tools.search_blog_posts]
        )

        return blog_posts_agent

    def get_seismic_agent(self) -> ChatAgent:
        """Create a Seismic agent with the necessary plugins."""
        agent_name = "seismic_agent"
        model_name = "gpt-4.1-mini"

        # Create the agent
        seismic_agent = ChatAgent(
            chat_client=self.chat_client,
            name=agent_name,
            description="Seismic agent that searches for relevant presentations and PowerPoints.",
            instructions=cache_service.load_prompt(agent_name),
            model_id=model_name,
            tools=[tools.search_seismic_presentations]
        )

        return seismic_agent

    def get_bing_search_agent(self) -> ChatAgent:
        """Create a Bing Search agent with the necessary plugins."""
        agent_name = "bing_search_agent"

        bing_search_agent = ChatAgent(
            chat_client=AzureAIAgentClient(
                async_credential=DefaultAzureCredential(),
                project_endpoint=self.project_endpoint,
                agent_id=self.bing_search_agent_id
            ),
            name=agent_name,
            description="Bing Search agent that performs web searches to find relevant information.",
            instructions="You help with web search queries using Bing.",
        )

        return bing_search_agent

    def get_github_docs_search_agent(self) -> ChatAgent:
        """Create a GitHub Docs Search agent with the necessary plugins."""
        agent_name = "github_docs_search_agent"
        model_name = "gpt-5.2-chat"

        mcp_server = MCPStreamableHTTPTool(
            name="GitHub Docs MCP Tool",
            url="https://api.githubcopilot.com/mcp",
            headers={
                "Authorization": f"Bearer {self.github_token}",
                "Content-Type": "application/json",
                "X-MCP-Tools": "github_support_docs_search"
            },
            approval_mode="never_require",
        )

        github_docs_search_agent = ChatAgent(
            chat_client=AzureOpenAIChatClient(
                endpoint=self.endpoint,
                api_key=self.api_key,
                deployment_name=model_name
            ),
            name=agent_name,
            instructions="""
                You help with GitHub support documentation questions.
                Never use prior knowledge.
                Phrase user queries like "query: <user question>" to use the tool.
                Always use the provided tool to search for relevant documentation based on user queries.
                Provide accurate and concise information and also cite your sources with appropriate links.
            """,
            tools=[mcp_server]
        )

        return github_docs_search_agent

    def get_aws_docs_agent(self) -> ChatAgent:
        """Create an AWS Docs agent with the necessary plugins."""
        agent_name = "aws_docs_agent"
        model_name = "gpt-5.2-chat"

        mcp_server = MCPStreamableHTTPTool(
            name="AWS MCP Tool",
            url="https://knowledge-mcp.global.api.aws",
            load_prompts=False
        )

        aws_docs_agent = ChatAgent(
            chat_client=AzureOpenAIChatClient(
                endpoint=self.endpoint,
                api_key=self.api_key,
                deployment_name=model_name
            ),
            name=agent_name,
            instructions="""
                You are a helpful assistant that provides information from AWS Docs.
                Use the provided tool to search for relevant documentation based on user queries.
                Always Provide accurate and concise information and also cite your sources with appropriate links.
                Provide suggestions for related topics the user might find useful.
            """,
            tools=[mcp_server]
        )

        return aws_docs_agent

    def get_architect_agent(self) -> ChatAgent:
        """Create an architect agent with the necessary plugins."""
        agent_name = "architect_agent"
        model_name = "o3-mini"

        # Create the agent
        architect_agent = ChatAgent(
            chat_client=self.chat_client,
            name=agent_name,
            description="Architect agent that provides architectural guidance and best practices.",
            instructions=cache_service.load_prompt(agent_name),
            model_id=model_name,
            tools=[
                tools.search_by_bing
            ]
        )

        return architect_agent

    def get_summarizer_agent(self) -> ChatAgent:
        """Create a summarizer agent with the necessary plugins."""
        agent_name = "summarizer_agent"
        model_name = "gpt-5.2-chat"

        # Create the agent
        summarizer_agent = ChatAgent(
            chat_client=self.chat_client,
            name=agent_name,
            description="Summarizer agent that condenses information into concise summaries.",
            instructions=cache_service.load_prompt(agent_name),
            model_id=model_name
        )

        return summarizer_agent

    def get_explainer_agent(self) -> ChatAgent:
        """Create an explainer agent with the necessary plugins."""
        agent_name = "explainer_agent"
        model_name = "gpt-5.2-chat"

        # Create the agent
        explainer_agent = ChatAgent(
            chat_client=self.chat_client,
            name=agent_name,
            description="Explainer agent that provides detailed explanations of concepts.",
            instructions=cache_service.load_prompt(agent_name),
            model_id=model_name
        )

        return explainer_agent


# Global instance
agent_factory = AgentFactory()
