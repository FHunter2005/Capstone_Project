# ai/ai_client.py
import google.generativeai as genai
from utils.config import Config
from tools.agent_tools import my_toolbox

class AIClient:
    # 1. Add 'history_messages' argument (default is None)
    def __init__(self, use_tools: bool = True, history_messages: list = None):
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        
        self.embed_model = Config.EMBED_MODEL 
        
        sys_instruction = """
        You are MasterMatch, an expert academic advisor for Master's degrees in Portugal.
        
        YOUR BEHAVIOR:
        1. GREETINGS: If the user says "Hello" or asks who you are, reply naturally. DO NOT use search tools.
        2. SEARCHING: Only use the 'search_masters_tool' if the user explicitly asks for courses, programs, or topics (e.g., 'marketing', 'biology').
        3. PERSONALITY: Be professional, encouraging, and concise. 
        4. CONTEXT: You only know about programs in the database. If you don't find results, suggest broader search terms.
        """

        # 2. Convert Streamlit/Mongo history to Gemini history
        gemini_history = []
        if history_messages:
            for msg in history_messages:
                role = "user" if msg["role"] == "user" else "model"
                content = msg["content"]
                
                # Gemini format:
                gemini_history.append({
                    "role": role,
                    "parts": [content]
                })

        if use_tools:
            self.model = genai.GenerativeModel(
                model_name=Config.LLM_MODEL,
                tools=my_toolbox,
                system_instruction=sys_instruction
            )
            # 3. Pass the converted history here
            self.chat_session = self.model.start_chat(
                enable_automatic_function_calling=True,
                history=gemini_history
            )
        else:
            self.model = genai.GenerativeModel(model_name=Config.LLM_MODEL)
            self.chat_session = None

    def send_message_to_agent(self, user_text: str) -> str:
        if not self.chat_session:
            return "Error: Client initialized without tools/chat session."
        response = self.chat_session.send_message(user_text)
        return response.text

    def embed(self, text: str):
        response = genai.embed_content(
            model=self.embed_model,
            content=text
        )
        return response["embedding"]
