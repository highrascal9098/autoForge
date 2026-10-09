import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Load .env relative to project root (parent of scraper/)
project_root = Path(__file__).resolve().parent.parent
dotenv_path = project_root / ".env"
load_dotenv(dotenv_path=dotenv_path)

logger = logging.getLogger(__name__)

# Startup diagnostic
logger.info(f".env file found: {dotenv_path.exists()}")
keys = [k for k in ["GEMINI_API_KEY"] + [f"GEMINI_API_KEY_{i}" for i in range(2, 11)] if os.getenv(k)]
# Check for batch keys
if os.getenv("GEMINI_API_KEYS"):
    keys.append("GEMINI_API_KEYS")
logger.info(f"Number of Gemini API key configurations loaded: {len(keys)}")
logger.info(f"Selected model: {os.getenv('AI_MODEL', 'gemini-1.5-flash')}")

class GeminiKeyManager:
    def __init__(self):
        self.keys = []
        primary = os.getenv("GEMINI_API_KEY")
        if primary and primary != "your_gemini_api_key_here":
            self.keys.append(primary)

        for i in range(2, 11):
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if key and key != "your_gemini_api_key_here":
                self.keys.append(key)

        batch_keys = os.getenv("GEMINI_API_KEYS", "")
        if batch_keys:
            for k in batch_keys.split(","):
                k = k.strip()
                if k and k not in self.keys and k != "your_gemini_api_key_here":
                    self.keys.append(k)

        self.current_index = 0
        logger.info(f"Initialized GeminiKeyManager with {len(self.keys)} usable API key(s).")

    def get_client(self):
        if not self.keys:
            raise ValueError("No Gemini API keys configured.")
        key = self.keys[self.current_index]
        return genai.Client(api_key=key)

    def rotate_key(self):
        if len(self.keys) > 1:
            self.current_index = (self.current_index + 1) % len(self.keys)
            logger.warning(f"Rotating to Gemini API key index {self.current_index}.")

    def generate_content_with_retry(self, prompt: str, max_retries: int = 3):
        """
        Attempts content generation with key rotation on rate limits or errors using google.genai.
        """
        retries = 0
        model_name = os.getenv("AI_MODEL", "gemini-1.5-flash")
        while retries < max_retries * max(1, len(self.keys)):
            try:
                client = self.get_client()
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                return response
            except Exception as e:
                error_str = str(e).lower()
                logger.warning(f"Gemini generation error with key index {self.current_index}: {e}")
                if "429" in error_str or "quota" in error_str or "resourceexhausted" in error_str or "rate limit" in error_str:
                    self.rotate_key()
                else:
                    self.rotate_key()
                retries += 1

        raise RuntimeError("All Gemini API keys exhausted or failed during content generation.")

# Global instance
gemini_client = GeminiKeyManager()
