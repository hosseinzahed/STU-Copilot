import os
import chainlit as cl
from typing import Annotated
from pydantic import Field
from .cosmos_db_service import cosmos_db_service
from agent_framework import tool, Agent
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential


class Tools:
    """Collection of AI functions as tools."""    

    @tool(name="search_github_repositories",
          description="Search for relevant GitHub repositories for a given topic.",
          approval_mode="never_require")
    #@cl.step(type="tool", name="Search GitHub Repositories")
    async def search_github_repositories(prompt: Annotated[str, Field(description="The topic to search for")]) -> list:
        """Search for relevant GitHub repositories."""
        results = await cosmos_db_service.hybrid_search(
            search_terms=prompt,
            container_name="github-repos",
            fields=["name", "url", "description",
                    "stars_count", "archived", "updated_at"],
            top_count=5)
        return results

    @tool(name="search_blog_posts",
          description="Search for relevant blog posts for a given topic.",
          approval_mode="never_require")
    #@cl.step(type="tool", name="Search Blog Posts")
    async def search_blog_posts(prompt: Annotated[str, Field(description="The topic to search for")]) -> list:
        """Search for relevant blog posts."""
        results = await cosmos_db_service.hybrid_search(
            search_terms=prompt,
            container_name="blog-posts",
            fields=["title", "description", "published_date", "url"],
            top_count=5)
        return results

    @tool(name="search_seismic_presentations",
          description="Search for relevant Seismic presentations for a given topic.",
          approval_mode="never_require")
    #@cl.step(type="tool", name="Search Seismic Presentations")
    async def search_seismic_presentations(prompt: Annotated[str, Field(description="The topic to search for")]) -> list:
        """Search for relevant Seismic presentations."""
        results = await cosmos_db_service.hybrid_search(
            search_terms=prompt,
            container_name="seismic-contents",
            fields=["name", "url", "description", "last_update", "expiration_date",
                    "level", "solution_area", "format", "size", "confidentiality"],
            top_count=5)
        return results

    @tool(name="search_by_bing", 
          description="Search by Bing for a given query.", 
          approval_mode="never_require")
    #@cl.step(type="tool", name="Search by Bing")
    async def search_by_bing(prompt: Annotated[str, Field(description="The query to search for")]) -> str:
        """Perform a Bing search."""

        async with (
            DefaultAzureCredential() as credential,
            Agent(
                chat_client=AzureAIAgentClient(
                    async_credential=credential,
                    project_endpoint=os.getenv("AI_FOUNDRY_PROJECT_ENDPOINT"),
                    agent_id=os.getenv("BING_SEARCH_AGENT_ID")
                ),
                instructions="You help with web search queries using Bing.",
            ) as agent,
        ):
            result = await agent.run(messages=prompt)
            return result.text


# Global instances
tools = Tools()
