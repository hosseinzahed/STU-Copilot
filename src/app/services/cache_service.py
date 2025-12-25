import os
from glob import glob
import logging
from datetime import datetime, timezone

class CacheService:
    def __init__(self):
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # In-memory cache for prompts
        self._PROMPT_CACHE = {}        
        self._PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts')

        # In-memory cache for sas tokens with timestamp
        # Structure: {container_name: {"token": str, "created_at": datetime}}
        self._STORAGE_SAS_TOKEN_CACHE = {}

        # Load all .prompty files at startup
        for prompt_path in glob(os.path.join(self._PROMPTS_DIR, "*.prompty")):
            prompt_name = os.path.splitext(os.path.basename(prompt_path))[0]
            with open(prompt_path, "r", encoding="utf-8") as f:
                self._PROMPT_CACHE[prompt_name] = f.read()
        self.logger.info("Loaded prompts into cache.")

    def load_prompt(self, prompt_name: str) -> str:
        """Fetch prompt from in-memory cache."""
        if prompt_name not in self._PROMPT_CACHE:
            raise KeyError(f"Prompt '{prompt_name}' not found in cache.")
        return self._PROMPT_CACHE[prompt_name]
    
    def set_sas_token_cache(self, container_name: str, sas_token: str):
        """Store SAS token with current timestamp."""
        self._STORAGE_SAS_TOKEN_CACHE[container_name] = {
            "token": sas_token,
            "created_at": datetime.now(timezone.utc)
        }
        
    def get_sas_token_cache(self, container_name: str) -> str:
        """Get SAS token only if it was created today (UTC), otherwise return None."""
        cache_entry = self._STORAGE_SAS_TOKEN_CACHE.get(container_name)
        if not cache_entry:
            return None
        
        # Check if token was created today
        created_date = cache_entry["created_at"].date()
        today = datetime.now(timezone.utc).date()
        
        if created_date == today:
            return cache_entry["token"]
        else:
            # Token is stale, remove it from cache
            self.logger.info(f"SAS token for '{container_name}' expired (created: {created_date})")
            del self._STORAGE_SAS_TOKEN_CACHE[container_name]
            return None

# Global instance
cache_service = CacheService()