# Project/ai/ai_client.py
import google.generativeai as genai
from langfuse import observe, get_client
from utils.config import Config
from tools.agent_tools import my_toolbox

class AIClient:
    """
    A wrapper class for the Google Gemini API, managing chat sessions, 
    context injection, tool execution, and observability via Langfuse.
    """

    def __init__(self, use_tools: bool = True, history_messages: list = None, system_instruction: str = None):
        """
        Initializes the AI Client with configuration, history, and optional tool capabilities.

        Args:
            use_tools (bool): If True, initializes the model with function calling capabilities.
            history_messages (list): A list of previous chat dictionaries (e.g., {"role": "user", "content": "..."}).
            system_instruction (str): The system prompt/persona (e.g., "You are an academic advisor...").
        """
        # Configure the Google AI SDK with the API key from environment variables
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        self.embed_model = Config.EMBED_MODEL 
        
        # Stores structured data returned by tools (e.g., lists of programs) for frontend access
        self.last_tool_results = []
        
        # --- History Parsing ---
        # Convert standard chat history into Gemini's specific 'user'/'model' content format
        gemini_history = []
        if history_messages:
            for msg in history_messages:
                # Map 'assistant' role to Gemini's 'model'
                role = "user" if msg["role"] == "user" else "model"
                content = msg["content"]
                
                # Ensure content is valid non-empty text before appending
                if content and isinstance(content, str) and content.strip():
                    gemini_history.append({"role": role, "parts": [content]})

        # --- Model Initialization ---
        if use_tools:
            # Initialize model with the defined toolbox and system-level context
            self.model = genai.GenerativeModel(
                model_name=Config.LLM_MODEL,
                tools=my_toolbox,
                system_instruction=system_instruction 
            )
            # Start a chat session with automatic function calling enabled
            self.chat_session = self.model.start_chat(
                enable_automatic_function_calling=True,
                history=gemini_history
            )
        else:
            # Fallback initialization for simple embedding or text generation tasks without tools
            self.model = genai.GenerativeModel(model_name=Config.LLM_MODEL)
            self.chat_session = None

    @observe(name="MasterMatch_Agent_Message")
    def send_message_to_agent(self, user_text: str) -> str:
        """
        Sends a user message to the agent, handles tool execution, and retrieves the text response.
        
        This method also inspects the chat history to extract 'raw_data' from tool outputs
        (e.g., JSON objects) so they can be rendered by the UI separately from the text.

        Args:
            user_text (str): The user's input prompt.

        Returns:
            str: The text response from the AI agent.
        """
        if not self.chat_session:
            return "Error: Client initialized without tools/chat session."
        
        # Send message to Gemini; function calling happens automatically here if triggered
        response = self.chat_session.send_message(user_text)

        # Reset tool results container for this turn
        self.last_tool_results = []
        
        # --- Tool Data Extraction ---
        # Iterate backwards through history to find the most recent function execution result.
        # This is necessary because Gemini handles the tool execution internally, so we
        # inspect the history to retrieve structured data (raw_data) for the UI.
        if self.chat_session.history:
            for msg in reversed(self.chat_session.history):
                for part in msg.parts:
                    # Check if this part of the message is a function response
                    if fn := part.function_response:
                        # Extract 'raw_data' if the tool returned it (custom convention)
                        if "raw_data" in fn.response:
                            self.last_tool_results = fn.response["raw_data"]
                            break
                # Stop looking once we find the most recent tool result
                if self.last_tool_results:
                    break
        
        # Ensure traces are sent to Langfuse before returning
        get_client().flush()
        
        return response.text

    def embed(self, text: str):
        """
        Generates a vector embedding for the provided text using the configured embedding model.

        Args:
            text (str): The input text to embed.

        Returns:
            list: A list of floats representing the vector embedding.
        """
        response = genai.embed_content(model=self.embed_model, content=text)
        return response["embedding"]