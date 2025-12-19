import os
import re
import chainlit as cl
from typing import List
from dotenv import load_dotenv, dotenv_values

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


if __name__ == "__main__":
    check_env_vars()
