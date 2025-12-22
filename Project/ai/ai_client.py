# Project/ai/ai_client.py
import google.generativeai as genai
from langfuse import observe, get_client
from utils.config import Config
from tools.agent_tools import my_toolbox

class AIClient:
    def __init__(self, use_tools: bool = True, history_messages: list = None):
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        self.embed_model = Config.EMBED_MODEL 
        
        # This will store the raw data for the Backend/UI
        self.last_tool_results = []
        
        sys_instruction = """
        You are MasterMatch, an expert academic advisor for Master's degrees in Portugal.
        
        YOUR BEHAVIOR:
        1. GREETINGS: If the user says "Hello" or asks who you are, reply naturally. DO NOT use search tools.
        2. SEARCHING: Only use the 'search_masters_tool' if the user explicitly asks for courses, programs, or topics.
        3. PERSONALITY: Be professional, encouraging, and concise. 
        4. CONTEXT: You only know about programs in the database. If you don't find results, suggest broader search terms.
        """

        gemini_history = []
        if history_messages:
            for msg in history_messages:
                role = "user" if msg["role"] == "user" else "model"
                content = msg["content"]
                if content and isinstance(content, str) and content.strip():
                    gemini_history.append({"role": role, "parts": [content]})

        if use_tools:
            self.model = genai.GenerativeModel(
                model_name=Config.LLM_MODEL,
                tools=my_toolbox,
                system_instruction=sys_instruction
            )
            self.chat_session = self.model.start_chat(
                enable_automatic_function_calling=True,
                history=gemini_history
            )
        else:
            self.model = genai.GenerativeModel(model_name=Config.LLM_MODEL)
            self.chat_session = None

    @observe(name="MasterMatch_Agent_Message")
    def send_message_to_agent(self, user_text: str) -> str:
        if not self.chat_session:
            return "Error: Client initialized without tools/chat session."
        
        response = self.chat_session.send_message(user_text)

        # --- NEW LOGIC: Extract Tool Results for the Backend ---
        # We look through the response parts to find function call results
        if response.candidates:
            for part in response.candidates[0].content.parts:
                # If using automatic function calling, the result is often 
                # available in the chat history immediately after the call
                pass
        
        # Better approach: Check the chat history for the most recent function response
        if self.chat_session.history:
            last_msg = self.chat_session.history[-1]
            for part in last_msg.parts:
                if fn := part.function_response:
                    # 'results' matches the key we returned in agent_tools.py
                    if "results" in fn.response:
                        self.last_tool_results = fn.response["results"]

        get_client().flush()
        return response.text

    def embed(self, text: str):
        response = genai.embed_content(model=self.embed_model, content=text)
        return response["embedding"]