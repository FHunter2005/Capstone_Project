# ai/ai_client.py
import google.generativeai as genai
from utils.config import Config


class AIClient:
    def __init__(self):
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        self.embed_model = Config.EMBED_MODEL
        self.llm_model = Config.LLM_MODEL
        self.model = genai.GenerativeModel(self.llm_model)

    def embed(self, text: str):
        """Return embedding vector (list of floats) for input text."""
        response = genai.embed_content(
            model=self.embed_model,
            content=text
        )
        return response["embedding"]

    def generate(self, prompt: str) -> str:
        """Return generated text from LLM."""
        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=1500,
            )
        )
        try:
            return (response.text or "").strip()
        except Exception:
            return ""

