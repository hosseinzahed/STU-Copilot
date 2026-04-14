import os
import chainlit as cl
import logging
from agent_framework import (
    Agent,
    MCPStreamableHTTPTool,
    agent_middleware,
    function_middleware)
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential
from agent_framework.openai import OpenAIChatClient
from .cache_service import cache_service
from .tool_factory import tools
from .compliance_workflow import get_compliance_workflow

# Configure logging
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating chat completion agents."""

    def __init__(self):
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.project_endpoint = os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
        self.credential = DefaultAzureCredential()
        self.foundry_client = FoundryChatClient(
            project_endpoint=self.project_endpoint,
            credential=self.credential,
            model="gpt-5.2-chat"
        )

        # Initialize agents
        self.agents: dict[str, Agent] = {
            "github_agent": self.get_github_agent(),
            "github_docs_search_agent": self.get_github_docs_search_agent(),
            "microsoft_docs_agent": self.get_microsoft_docs_agent(),
            "blog_posts_agent": self.get_blog_posts_agent(),
            "seismic_agent": self.get_seismic_agent(),
            # "architect_agent": self.get_architect_agent(),
            "aws_docs_agent": self.get_aws_docs_agent(),
            # "compliance_agent": self.get_compliance_agent()
            "compliance_agent": get_compliance_workflow().as_agent(name="compliance_agent")
        }
        self.agents["orchestrator_agent"] = self.get_orchestrator_agent()

    def get_agents(self) -> dict[str, Agent]:
        """Get all agents."""
        return self.agents

    def get_orchestrator_agent(self) -> Agent:
        """Create an orchestrator agent with the necessary plugins."""
        agent_name = "orchestrator_agent"
        model_name = "gpt-5.2-chat"
        
        web_search_tool = self.foundry_client.get_web_search_tool()

        # Create the agent
        orchestrator_agent = Agent(
            client=self.foundry_client,
            name=agent_name,
            description="Orchestrator agent that manages the workflow of other agents.",
            instructions="""
                You are a Microsoft technology assistant. 
                Route tasks to the appropriate specialized agent (Microsoft Docs, GitHub, blog posts, seismic presentations) as needed. 
                For web searches, use the provided web search tool and always cite sources with links. 
                Be clear and concise.
                """,
            tools=[
                self.agents.get("microsoft_docs_agent").as_tool(),                
                self.agents.get("blog_posts_agent").as_tool(),
                self.agents.get("github_docs_search_agent").as_tool(),
                #web_search_tool                
            ],
            default_options={
                "allow_multiple_tool_calls": True,
            },
            middleware=[
                self.simple_agent_middleware,
                self.simple_function_middleware
            ]
        )

        return orchestrator_agent

    def get_github_agent(self) -> Agent:
        """Create a GitHub agent with the necessary plugins."""
        agent_name = "github_agent"
        model_name = "gpt-4.1-mini"

        # Create the agent
        github_agent = Agent(
            client=self.foundry_client,
            name=agent_name,
            description="GitHub agent that fetches relevant information from GitHub repositories.",
            instructions=cache_service.load_prompt(agent_name),
            tools=[tools.search_github_repositories],
            middleware=[
                self.simple_agent_middleware,
                self.simple_function_middleware
            ]
        )

        return github_agent

    def get_microsoft_docs_agent(self) -> Agent:
        """Create a Microsoft Docs agent with the necessary plugins."""
        agent_name = "microsoft_docs_agent"
        model_name = "gpt-5.2-chat"

        # Create the MCP tool
        mcp_server = MCPStreamableHTTPTool(
            name="Microsoft Docs MCP Tool",
            url="https://learn.microsoft.com/api/mcp"
        )

        # Create the agent
        microsoft_docs_agent = Agent(
            client=FoundryChatClient(
                project_endpoint=self.project_endpoint,
                credential=self.credential,
                model=model_name
            ),
            name=agent_name,
            description="Microsoft Docs agent that searches for relevant Microsoft documentation.",
            instructions="""
                You provide information from Microsoft Docs using the search tool.
                - Rephrase queries max into up to 3 parallel searches for better results
                - Cite sources with links and include all images from search results
                - Format responses in markdown with related topic suggestions
            """,
            tools=[mcp_server],
            default_options={
                "allow_multiple_tool_calls": True,
            },
            middleware=[
                self.simple_agent_middleware,
                self.simple_function_middleware
            ]
        )

        return microsoft_docs_agent

    def get_blog_posts_agent(self) -> Agent:
        """Create a Blog Posts agent with the necessary plugins."""
        agent_name = "blog_posts_agent"
        model_name = "gpt-4.1-mini"

        # Create the agent
        blog_posts_agent = Agent(
            client=self.foundry_client,
            name=agent_name,
            description="Blog Posts agent that searches for relevant blog posts.",
            instructions=cache_service.load_prompt(agent_name),
            tools=[tools.search_blog_posts],
            middleware=[
                self.simple_agent_middleware,
                self.simple_function_middleware
            ]
        )

        return blog_posts_agent

    def get_seismic_agent(self) -> Agent:
        """Create a Seismic agent with the necessary plugins."""
        agent_name = "seismic_agent"
        model_name = "gpt-4.1-mini"

        # Create the agent
        seismic_agent = Agent(
            client=self.foundry_client,
            name=agent_name,
            description="Seismic agent that searches for relevant presentations and PowerPoints.",
            instructions=cache_service.load_prompt(agent_name),
            tools=[tools.search_seismic_presentations],
            middleware=[
                self.simple_agent_middleware,
                self.simple_function_middleware
            ]
        )

        return seismic_agent

    def get_github_docs_search_agent(self) -> Agent:
        """Create a GitHub Docs Search agent with the necessary plugins."""
        agent_name = "github_docs_search_agent"
        model_name = "gpt-5.2-chat"

        github_token = os.getenv("GITHUB_TOKEN")

        client = OpenAIChatClient(
            model=model_name,
            async_client=self.credential
        )
        github_mcp_tool = client.get_mcp_tool(
            name="GitHub",
            url="https://api.githubcopilot.com/mcp/",
            headers={
                "Authorization": f"Bearer {github_token}",
                "X-MCP-Tools": "github_support_docs_search"
            },
            approval_mode="never_require",
        )

        # Create the agent
        github_docs_search_agent = Agent(
            client=FoundryChatClient(
                project_endpoint=self.project_endpoint,
                credential=self.credential,
                model=model_name
            ),
            name=agent_name,
            description="GitHub Docs Search agent that searches for relevant GitHub support documentation.",
            instructions="""
                You help with GitHub support documentation questions.
                Never use prior knowledge.
                Phrase user queries like "query: <user question>" to use the tool.
                Always use the provided tool to search for relevant documentation based on user queries.
                Provide accurate and concise information and also cite your sources with appropriate links.
            """,
            tools=[github_mcp_tool],
            default_options={
                "allow_multiple_tool_calls": True,
            },
            middleware=[
                self.simple_agent_middleware,
                self.simple_function_middleware
            ]
        )

        return github_docs_search_agent

    def get_aws_docs_agent(self) -> Agent:
        """Create an AWS Docs agent with the necessary plugins."""
        agent_name = "aws_docs_agent"
        model_name = "gpt-5.2-chat"

        # Create the MCP tool
        mcp_server = MCPStreamableHTTPTool(
            name="AWS MCP Tool",
            url="https://knowledge-mcp.global.api.aws",
            load_prompts=False
        )

        # Create the agent
        aws_docs_agent = Agent(
            client=FoundryChatClient(
                project_endpoint=self.project_endpoint,
                credential=self.credential,
                model=model_name
            ),
            name=agent_name,
            description="AWS Docs agent that searches for relevant AWS documentation.",
            instructions="""
                You are a helpful assistant that provides information from AWS Docs.
                Use the provided tool to search for relevant documentation based on user queries.
                Always Provide accurate and concise information and also cite your sources with appropriate links.
                Provide suggestions for related topics the user might find useful.
            """,
            tools=[mcp_server],
            middleware=[
                self.simple_agent_middleware,
                self.simple_function_middleware
            ]
        )

        return aws_docs_agent

    def get_architect_agent(self) -> Agent:
        """Create an architect agent with the necessary plugins."""
        agent_name = "architect_agent"
        model_name = "o3-mini"

        # Create the agent
        architect_agent = Agent(
            client=self.foundry_client,
            name=agent_name,
            description="Architect agent that provides architectural guidance and best practices.",
            instructions=cache_service.load_prompt(agent_name),
            tools=[],
            middleware=[
                self.simple_agent_middleware,
                self.simple_function_middleware
            ]
        )

        return architect_agent

    @agent_middleware  # Explicitly marks as agent middleware
    async def simple_agent_middleware(self, context, next):
        """Agent middleware with decorator - types are inferred."""
        await cl.Message("Thinking...").send()
        await next()

    @function_middleware  # Explicitly marks as function middleware
    async def simple_function_middleware(self, context, next):
        """Function middleware with decorator - types are inferred."""
        async with cl.Step(type="tool", name=f"{context.function.name}") as step:
            step.input = context.arguments
            step.output = context.result
        # await cl.Message(f"Calling function: {context.function.name}").send()
        await next()


# Global instance
agent_factory = AgentFactory()
