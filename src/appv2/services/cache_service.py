import os
from glob import glob
import logging

class CacheService:
    def __init__(self):
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.PROMPT_CACHE = {}
        self.PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts')

        # Load all .prompty files at startup
        for prompt_path in glob(os.path.join(self.PROMPTS_DIR, "*.prompty")):
            prompt_name = os.path.splitext(os.path.basename(prompt_path))[0]
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.PROMPT_CACHE[prompt_name] = f.read()
        self.logger.info("Loaded prompts into cache.")

    def load_prompt(self, prompt_name: str) -> str:
        """Fetch prompt from in-memory cache."""
        if prompt_name not in self.PROMPT_CACHE:
            raise KeyError(f"Prompt '{prompt_name}' not found in cache.")
        return self.PROMPT_CACHE[prompt_name]

# Global instance
cache_service = CacheService()