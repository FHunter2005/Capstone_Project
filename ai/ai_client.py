import google.generativeai as genai
from utils.config import Config

class AIClient:
    def __init__(self):
        # Configure Gemini API with your key
        genai.configure(api_key=Config.GOOGLE_API_KEY)

        # Set your models
        self.embed_model = Config.EMBED_MODEL
        self.llm_model = Config.LLM_MODEL

        # For generate() we create a model object
        self.model = genai.GenerativeModel(self.llm_model)

    def embed(self, text: str):
        """Generate embedding vector for input text."""
        response = genai.embed_content(
            model=self.embed_model,
            content=text
        )
        return response["embedding"]

    def generate(self, prompt: str) -> str:
        """Generate LLM response text."""
        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=400,
            )
        )
        try:
            return response.text.strip()
        except Exception:
            return ""

