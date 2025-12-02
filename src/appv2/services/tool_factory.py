import os
from contextlib import asynccontextmanager
import chainlit as cl
from typing import Annotated
from pydantic import Field
from .cosmos_db_service import cosmos_db_service
from agent_framework import ai_function, ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient, AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient

# Environment variables for AI Foundry project endpoint and agent IDs
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
if not azure_openai_endpoint:
    raise EnvironmentError(
        "AZURE_OPENAI_ENDPOINT environment variable is not set.")

ai_foundry_key = os.getenv("AI_FOUNDRY_KEY")
if not ai_foundry_key:
    raise EnvironmentError(
        "AI_FOUNDRY_KEY environment variable is not set.")

ai_foundry_project_endpoint = os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT")
if not ai_foundry_project_endpoint:
    raise EnvironmentError(
        "AI_FOUNDRY_PROJECT_ENDPOINT environment variable is not set.")

bing_search_agent_id = os.getenv("BING_SEARCH_AGENT_ID")
if not bing_search_agent_id:
    raise EnvironmentError(
        "BING_SEARCH_AGENT_ID environment variable is not set.")

github_docs_search_agent_id = os.getenv("GITHUB_DOCS_SEARCH_AGENT_ID")
if not github_docs_search_agent_id:
    raise EnvironmentError(
        "GITHUB_DOCS_SEARCH_AGENT_ID environment variable is not set.")

github_token = os.getenv("GITHUB_TOKEN")
if not github_token:
    raise EnvironmentError(
        "GITHUB_TOKEN environment variable is not set.")


class Tools:
    """Collection of AI functions as tools."""

    @ai_function(name="search_github_repositories",
                 description="Search for relevant GitHub repositories for a given topic.")
    @cl.step(type="tool", name="Search GitHub Repositories")
    async def search_github_repositories(prompt: Annotated[str, Field(description="The topic to search for")]) -> list:
        """Search for relevant GitHub repositories."""
        results = cosmos_db_service.hybrid_search(
            search_terms=prompt,
            container_name="github-repos",
            fields=["name", "url", "description",
                    "stars_count", "archived", "updated_at"],
            top_count=10)
        return results

    @ai_function(name="search_microsoft_docs",
                 description="Search for relevant Microsoft documentation for a given topic.")
    @cl.step(type="tool", name="Search Microsoft Documentation")
    async def search_microsoft_docs(prompt: Annotated[str, Field(description="The topic to search for")]) -> str:
        """Search for relevant Microsoft documentation."""

        async with (
            MCPStreamableHTTPTool(
                name="Microsoft Docs MCP Tool",
                url="https://learn.microsoft.com/api/mcp"
            ) as mcp_server,
            ChatAgent(
                chat_client=AzureOpenAIChatClient(
                    endpoint=azure_openai_endpoint,
                    api_key=ai_foundry_key,
                    deployment_name="gpt-5-mini"
                ),
                name="Microsoft Docs Agent",
                instructions="You help with Microsoft documentation questions.",
                tools=[mcp_server]
            ) as agent,
        ):
            result = await agent.run(messages=prompt)
            return result.text

    @ai_function(name="search_blog_posts",
                 description="Search for relevant blog posts for a given topic.")
    @cl.step(type="tool", name="Search Blog Posts")
    async def search_blog_posts(prompt: Annotated[str, Field(description="The topic to search for")]) -> list:
        """Search for relevant blog posts."""
        results = cosmos_db_service.hybrid_search(
            search_terms=prompt,
            container_name="blog-posts",
            fields=["title", "description", "published_date", "url"],
            top_count=5)
        return results

    @ai_function(name="search_seismic_presentations",
                 description="Search for relevant Seismic presentations for a given topic.")
    @cl.step(type="tool", name="Search Seismic Presentations")
    async def search_seismic_presentations(prompt: Annotated[str, Field(description="The topic to search for")]) -> list:
        """Search for relevant Seismic presentations."""
        results = cosmos_db_service.hybrid_search(
            search_terms=prompt,
            container_name="seismic-contents",
            fields=["name", "url", "description", "last_update", "expiration_date",
                    "level", "solution_area", "format", "size", "confidentiality"],
            top_count=10)
        return results

    @ai_function(name="search_by_bing", description="Search by Bing for a given query.")
    @cl.step(type="tool", name="Search by Bing")
    async def search_by_bing(prompt: Annotated[str, Field(description="The query to search for")]) -> str:
        """Perform a Bing search."""

        async with (
            DefaultAzureCredential() as credential,
            ChatAgent(
                chat_client=AzureAIAgentClient(
                    async_credential=credential,
                    project_endpoint=ai_foundry_project_endpoint,
                    agent_id=bing_search_agent_id                                        
                ),
                instructions="You help with web search queries using Bing.",
            ) as agent,
        ):
            result = await agent.run(messages=prompt)
            return result.text

    @ai_function(name="search_github_docs",
                 description="Search for relevant GitHub documentation for a given topic.")
    @cl.step(type="tool", name="Search GitHub Documentation")
    async def search_github_docs(prompt: Annotated[str, Field(description="The topic to search for")]) -> str:
        """Search for relevant GitHub documentation."""
        async with (
            MCPStreamableHTTPTool(
                name="GitHub MCP Tool",
                url="https://api.githubcopilot.com/mcp",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Content-Type": "application/json"
                },
                allowed_tools=["github_support_docs_search"]
            ) as mcp_server,
            ChatAgent(
                chat_client=AzureOpenAIChatClient(
                    endpoint=azure_openai_endpoint,
                    api_key=ai_foundry_key,
                    deployment_name="gpt-5-mini"
                ),
                name="GitHub Docs Agent",
                instructions="You help with GitHub support documentation questions.",
                tools=[mcp_server]
            ) as agent,
        ):
            result = await agent.run(messages=prompt)
            return result.text

    @ai_function(name="search_aws_docs",
                 description="Search for relevant AWS documentation for a given topic.")
    @cl.step(type="tool", name="Search AWS Documentation")
    async def search_aws_docs(prompt: Annotated[str, Field(description="The topic to search for")]) -> str:
        """Search for relevant AWS documentation."""

        async with (
            MCPStreamableHTTPTool(
                name="AWS MCP Tool",
                url="https://knowledge-mcp.global.api.aws"
            ) as mcp_server,
            ChatAgent(
                chat_client=AzureOpenAIChatClient(
                    endpoint=azure_openai_endpoint,
                    api_key=ai_foundry_key,
                    deployment_name="gpt-5-mini"
                ),
                name="AWS Docs Agent",
                instructions="You help with AWS documentation questions.",
                tools=[mcp_server]
            ) as agent,
        ):
            result = await agent.run(messages=prompt)
            return result.text


@asynccontextmanager
async def get_ai_foundry_client():
    async with (
        AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint=ai_foundry_project_endpoint,
        ) as client
    ):
        yield client

# Global instances
tools = Tools()
