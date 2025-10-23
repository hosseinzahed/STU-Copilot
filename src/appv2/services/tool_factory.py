import os
from contextlib import asynccontextmanager
import json
import chainlit as cl
from typing import Annotated
from pydantic import Field
from .cosmos_db_service import cosmos_db_service
from agent_framework import ai_function, ChatAgent, ChatMessage
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient


# Environment variables for AI Foundry project endpoint and agent IDs
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


class Tools:
    """A plugin to search GitHub repositories."""

    @ai_function(name="search_github_repositories",
                 description="Search for relevant GitHub repositories for a given topic.")
    @cl.step(type="tool", name="Search GitHub Repositories")
    async def search_github_repositories(self,
                                         input: Annotated[str, Field(description="The topic to search for")]) -> list:
        """Search for relevant GitHub repositories."""
        results = cosmos_db_service.hybrid_search(
            search_terms=input,
            container_name="github-repos",
            fields=["name", "url", "description",
                    "stars_count", "archived", "updated_at"],
            top_count=10)
        return results

    @ai_function(name="search_microsoft_docs",
                 description="Search for relevant Microsoft documentation for a given topic.")
    @cl.step(type="tool", name="Search Microsoft Documentation")
    async def search_microsoft_docs(self,
                                    input: Annotated[str, Field(description="The topic to search for")]) -> str:
        """Search for relevant Microsoft documentation."""

        async with streamablehttp_client("https://learn.microsoft.com/api/mcp") as (
            read_stream,
            write_stream,
            _,
        ):
            # Create a session using the client streams
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the connection
                await session.initialize()

                # Call the Microsoft Docs MCP tool
                response = await session.call_tool(
                    "microsoft_docs_search",
                    arguments={
                        "query": input
                    }
                )
                if response.isError or not response.content or not response.content[0] or not response.content[0].text:
                    return "Could not retrieve results from Microsoft Docs Portal."

                data = json.loads(response.content[0].text)

                aggregated = {}

                for item in data:
                    title = item["title"]
                    content = item["content"]
                    heading = f"# {title}\n"
                    # Remove the heading from the content if it exists
                    if content.startswith(heading):
                        content = content[len(heading):]
                    if title in aggregated:
                        aggregated[title].append(content)
                    else:
                        aggregated[title] = [content]

                aggregated_results = [
                    {"title": title, "content": "\n\n".join(contents)}
                    for title, contents in aggregated.items()
                ]

                return json.dumps(aggregated_results, indent=2, ensure_ascii=False)

    @ai_function(name="search_blog_posts",
                 description="Search for relevant blog posts for a given topic.")
    @cl.step(type="tool", name="Search Blog Posts")
    async def search_blog_posts(self,
                                input: Annotated[str, Field(description="The topic to search for")]) -> list:
        """Search for relevant blog posts."""
        results = cosmos_db_service.hybrid_search(
            search_terms=input,
            container_name="blog-posts",
            fields=["title", "description", "published_date", "url"],
            top_count=5)
        return results

    @ai_function(name="search_seismic_presentations",
                 description="Search for relevant Seismic presentations for a given topic.")
    @cl.step(type="tool", name="Search Seismic Presentations")
    async def search_seismic_presentations(self,
                                           input: Annotated[str, Field(description="The topic to search for")]) -> list:
        """Search for relevant Seismic presentations."""
        results = cosmos_db_service.hybrid_search(
            search_terms=input,
            container_name="seismic-contents",
            fields=["name", "url", "description", "last_update", "expiration_date",
                    "level", "solution_area", "format", "size", "confidentiality"],
            top_count=10)
        return results

    @ai_function(name="search_by_bing", description="Search by Bing for a given query.")
    @cl.step(type="tool", name="Search by Bing")
    async def search_by_bing(self,
                             input: Annotated[str, Field(description="The query to search for")]) -> str:
        """Perform a Bing search."""
        async with get_ai_foundry_client() as client:
            agent: ChatAgent = await client.agents.get_agent(agent_id=bing_search_agent_id)
            message = ChatMessage(
                role="user",
                text=input
            )
            response = await agent.run(messages=[message])
            if not response:
                return "Could not retrieve results from Bing Search."
            return response.text

    @ai_function(name="search_github_docs",
                 description="Search for relevant GitHub documentation for a given topic.")
    @cl.step(type="tool", name="Search GitHub Documentation")
    async def search_github_docs(self,
                                 input: Annotated[str, Field(description="The topic to search for")]) -> str:
        """Search for relevant GitHub documentation."""
        async with get_ai_foundry_client() as client:

            agent: ChatAgent = await client.agents.get_agent(agent_id=github_docs_search_agent_id)
            message = ChatMessage(
                role="user",
                text=input
            )
            response = await agent.run(messages=[message])
            if not response:
                return "Could not retrieve results from GitHub Docs Portal."
            return response.text

    @ai_function(name="search_aws_docs",
                 description="Search for relevant AWS documentation for a given topic.")
    @cl.step(type="tool", name="Search AWS Documentation")
    async def search_aws_docs(self,
                              input: Annotated[str, Field(description="The topic to search for")]) -> str:
        """Search for relevant AWS documentation."""

        async with streamablehttp_client("https://knowledge-mcp.global.api.aws") as (
            read_stream,
            write_stream,
            _,
        ):
            # Create a session using the client streams
            async with ClientSession(read_stream, write_stream) as session:

                # Initialize the connection
                await session.initialize()

                # Call the tool
                response = await session.call_tool(
                    "aws___search_documentation",
                    arguments={
                        "search_phrase": input,
                        "limit": 10
                    }
                )

                # Check for errors
                if response.isError or not response.content or len(response.content) == 0:
                    return "Could not retrieve results from AWS Docs Portal."

                results = []
                for content in response.content:
                    if isinstance(content, types.TextContent):
                        data = json.loads(content.text)
                        results = data["response"]["payload"]["content"]["result"]

                return json.dumps(results, indent=2, ensure_ascii=False)


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
