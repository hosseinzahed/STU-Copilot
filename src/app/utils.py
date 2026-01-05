import asyncio
import os
import re
from agent_framework.azure import AzureAISearchContextProvider
from azure.identity.aio import DefaultAzureCredential
import chainlit as cl
from typing import List
from dotenv import load_dotenv, dotenv_values
from agent_framework import MCPStreamableHTTPTool, ChatMessage

load_dotenv(override=True)


def check_env_vars() -> None:
    """Check if the required environment variables are set.

    Args:
        required_vars (list[str]): List of required environment variable names. 
    Raises:
        EnvironmentError: If any required environment variable is not set.
    """

    # Get all variables defined in the .env file
    required_vars = list(dotenv_values('.env').keys())

    # Check for missing environment variables
    missing = [var for var in required_vars if not os.getenv(var)]

    # Raise an error
    if missing:
        raise ValueError(
            f"Missing environment variables: {', '.join(missing)}")


def extract_image_elements(content: str) -> List[cl.Image]:
    """Extract image URLs from content and return cl.Image elements.

    Supports:
    - Markdown images: ![alt](url)
    - HTML img tags: <img src="url">
    - Standalone image URLs with common extensions
    """
    image_elements = []
    found_urls = set()

    # Pattern to match markdown images: ![alt](url)
    markdown_images = re.findall(r'!\[([^\]]*)\]\(([^\)]+)\)', content)
    for alt_text, url in markdown_images:
        image_elements.append(
            cl.Image(url=url, name=alt_text or "Image", display="inline", size="medium"))
        found_urls.add(url)

    # Pattern to match HTML img tags: <img src="url" /> or <img src='url'>
    html_images = re.findall(
        r'<img[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
    for url in html_images:
        if url not in found_urls:
            image_elements.append(
                cl.Image(url=url, name="Image", display="inline", size="medium"))
            found_urls.add(url)

    # Pattern to match standalone image URLs (http/https URLs ending with image extensions)
    standalone_images = re.findall(
        r'https?://[^\s<>"]+\.(?:png|jpg|jpeg|gif|bmp|svg|webp)', content, re.IGNORECASE)
    for url in standalone_images:
        if url not in found_urls:
            image_elements.append(
                cl.Image(url=url, name="Image", display="inline", size="medium"))
            found_urls.add(url)

    return image_elements


async def get_results() -> None:
    ai_search_endpoint = os.getenv("AI_SEARCH_ENDPOINT")
    ai_search_key = os.getenv("AI_SEARCH_KEY")
    knowledge_base_name = "stu-copilot-kb"

    # AI Search Context Provider
    # Create the MCP tool
    mcp_server = MCPStreamableHTTPTool(
        name="AI Search MCP Tool",
        description="Tool to retrieve information from the compliance knowledge base using AI Search.",
        url=f"{ai_search_endpoint}/knowledgebases/{knowledge_base_name}/mcp?api-version=2025-11-01-preview",
        headers={
            "api-key": f"{ai_search_key}",
            "Content-Type": "application/json"
        },
        approval_mode="never_require",
        allowed_tools=["knowledge_base_retrieve"],
        load_prompts=False,
        load_tools=True,
        request_timeout=60,
        timeout=60
    )
    await mcp_server.connect()
    await mcp_server.load_tools()

    results = await mcp_server.call_tool(
        "knowledge_base_retrieve",
        request={
            "knowledgeAgentIntents": [
                "azure bing"
            ]
        }
    )
    await mcp_server.close()

    for item in results:
        print(str(item.text) + "\n------------------\n")


async def retrieve_content() -> str:

    search_provider = AzureAISearchContextProvider(
        endpoint=os.getenv("AI_SEARCH_ENDPOINT"),
        api_key=os.getenv("AI_SEARCH_KEY"),
        credential=DefaultAzureCredential() if not os.getenv("AI_SEARCH_KEY") else None,
        mode="agentic",
        knowledge_base_name="stu-copilot-kb",
        # Optional: Configure retrieval behavior
        knowledge_base_output_mode="extractive_data",  # or "answer_synthesis"
        retrieval_reasoning_effort="medium",  # or "medium", "low"
    )

    results = await search_provider.invoking(
        ChatMessage(role="user", content="azure bing"))

    print(results)


if __name__ == "__main__":
    asyncio.run(retrieve_content())
