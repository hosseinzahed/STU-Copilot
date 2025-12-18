import os
import chainlit as cl
import logging
from agent_framework import (ChatAgent, MCPStreamableHTTPTool,
                             agent_middleware, function_middleware, chat_middleware)
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
        self.project_endpoint = os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
        self.chat_client = AzureOpenAIChatClient(
            endpoint=self.endpoint,
            api_key=self.api_key,
            deployment_name="gpt-5.2-chat"
        )

        self.agents = {
            "github_agent": self.get_github_agent(),
            "github_docs_search_agent": self.get_github_docs_search_agent(),
            "microsoft_docs_agent": self.get_microsoft_docs_agent(),
            "blog_posts_agent": self.get_blog_posts_agent(),
            "seismic_agent": self.get_seismic_agent(),
            "bing_search_agent": self.get_bing_search_agent(),
            # "architect_agent": self.get_architect_agent(),
            "aws_docs_agent": self.get_aws_docs_agent()
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
        model_name = "gpt-5.2-chat"

        # Create the agent
        orchestrator_agent = ChatAgent(
            chat_client=self.chat_client,
            name=agent_name,
            description="Orchestrator agent that manages the workflow of other agents.",
            instructions="""
                You're a helpful assistant assisting users with their requests in the context of Microsoft technologies.
                Based on the user's input, if necessary, decide which specialized agent to delegate the task to.
                You have access to the following agents:
                - Microsoft Docs Agent: For searching Microsoft documentation. You should use this agent to find official Microsoft documentation and provide accurate information.
                - Bing Search Agent: For performing web searches using Bing. Use this agent to gather up-to-date information from the web.                
                Provide clear and concise responses, ensuring that the user feels supported throughout their interaction.
                """,
            model_id=model_name,
            tools=[
                self.agents.get("microsoft_docs_agent").as_tool(
                    description="Search Microsoft documentation"
                ),
                self.agents.get("bing_search_agent").as_tool(
                    description="Perform web searches using Bing"
                )
            ],
            allow_multiple_tool_calls=True
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

        # Create the MCP tool
        mcp_server = MCPStreamableHTTPTool(
            name="Microsoft Docs MCP Tool",
            url="https://learn.microsoft.com/api/mcp"
        )

        # Create the agent
        microsoft_docs_agent = ChatAgent(
            chat_client=AzureOpenAIChatClient(
                endpoint=self.endpoint,
                api_key=self.api_key,
                deployment_name=model_name
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
            allow_multiple_tool_calls=True,
            middleware=[
                self.simple_agent_middleware,
                self.simple_function_middleware,
                self.simple_chat_middleware
            ]
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
        model_name = "gpt-4.1-mini"

        # Create the agent
        bing_search_agent = ChatAgent(
            name=agent_name,
            description="Bing Search agent that performs web searches using Bing.",
            model_name=model_name,
            chat_client=AzureAIAgentClient(
                credential=DefaultAzureCredential(),
                project_endpoint=self.project_endpoint,
                model_deployment_name=model_name,
                agent_id=os.getenv("BING_SEARCH_AGENT_ID")
            ),
            instructions="""
                You are a helpful assistant that provides information by searching the web.
                Use the provided tool to search for relevant information based on user queries.
                Always provide the answers in English. Provide the citations for your sources.
            """,
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
                "Authorization": f"Bearer {os.getenv("GITHUB_TOKEN")}",
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
            description="GitHub Docs Search agent that searches for relevant GitHub support documentation.",
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
            description="AWS Docs agent that searches for relevant AWS documentation.",
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

    @agent_middleware  # Explicitly marks as agent middleware
    async def simple_agent_middleware(self, context, next):
        """Agent middleware with decorator - types are inferred."""
        _global_task_list = cl.TaskList()
        _global_task_list.status = "Thinking..."
        await next(context)
        print("After agent execution")

    @function_middleware  # Explicitly marks as function middleware
    async def simple_function_middleware(self, context, next):
        """Function middleware with decorator - types are inferred."""
        print(f"Calling function: {context.function.name}")        
        async with cl.Step(type="tool", name=f"{context.function.name}") as step:
            step.input = context.arguments            
        await next(context)        
        print("Function call completed")

    @chat_middleware  # Explicitly marks as chat middleware
    async def simple_chat_middleware(self, context, next):
        """Chat middleware with decorator - types are inferred."""
        print(f"Processing {len(context.messages)} chat messages")
        await next(context)
        print("Chat processing completed")


# Global instance
agent_factory = AgentFactory()
