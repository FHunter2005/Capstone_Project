# Project/ai/ai_client.py
from google import genai
from google.genai import types
from langfuse import observe, get_client
from utils.config import Config
from tools.agent_tools import my_toolbox

class AIClient:
    def __init__(self, use_tools: bool = True, history_messages: list = None):
        # 1. Initialize the new Client (replaces genai.configure)
        self.client = genai.Client(api_key=Config.GOOGLE_API_KEY)
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

        # 2. Format History for the new SDK
        formatted_history = []
        if history_messages:
            for msg in history_messages:
                role = "user" if msg["role"] == "user" else "model"
                # The new SDK requires valid content parts
                if msg.get("content"):
                    formatted_history.append(
                        types.Content(
                            role=role,
                            parts=[types.Part(text=msg["content"])]
                        )
                    )

        # 3. Configure the Chat
        config = types.GenerateContentConfig(
            system_instruction=sys_instruction,
            temperature=0.7 # Optional: standard setting
        )

        if use_tools:
            # Pass the list of functions directly
            config.tools = my_toolbox
            config.automatic_function_calling = types.AutomaticFunctionCallingConfig(disable=False)

        # 4. Create Chat Session
        self.chat = self.client.chats.create(
            model=Config.LLM_MODEL,
            config=config,
            history=formatted_history
        )

    @observe(name="MasterMatch_Agent_Message")
    def send_message_to_agent(self, user_text: str) -> str:
        if not self.chat:
            return "Error: Client initialized without chat session."
        
        # Send message
        response = self.chat.send_message(user_text)

        # 5. Extract Tool Results (Updated for new SDK structure)
        # We assume the tool returns a dict with a "results" key as per agent_tools.py
        try:
            # We iterate backwards to find the most recent function response
            for message in reversed(self.chat.history):
                for part in message.parts:
                    if part.function_response:
                        # The response content is now a standard dictionary
                        response_content = part.function_response.response
                        if response_content and "results" in response_content:
                            self.last_tool_results = response_content["results"]
                            break # Found the results
                if self.last_tool_results:
                    break
        except Exception as e:
            print(f"⚠️ Warning: Could not extract tool results: {e}")

        get_client().flush()
        return response.text

    def embed(self, text: str):
        # Updated Embedding Call
        result = self.client.models.embed_content(
            model=self.embed_model,
            contents=text
        )
        if result.embeddings:
            return result.embeddings[0].values
        return []