'''class AIClient:
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
                max_output_tokens=10000,
            )
        )
        try:
            return (response.text or "").strip()
        except Exception:
            return ""'''

import google.generativeai as genai
from utils.config import Config
from tools.agent_tools import my_toolbox

class AIClient:
    def __init__(self):
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        
        self.model = genai.GenerativeModel(
            model_name=Config.LLM_MODEL,
            tools=my_toolbox 
        )
        
        self.chat_session = self.model.start_chat(enable_automatic_function_calling=True)

    def send_message_to_agent(self, user_text: str) -> str:
        """
        Envia a mensagem para o LLM. Ele decide sozinho se responde logo
        ou se usa uma ferramenta (search_masters, etc.) e depois responde.
        """
        response = self.chat_session.send_message(user_text)
        return response.text

