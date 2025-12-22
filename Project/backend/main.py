# Project/backend/main.py
import sys
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Ensure the project root is in the python path for module resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.ai_client import AIClient
from services.auth_service import AuthService
from ai.prompts import get_system_instruction, generate_persona_summary

# Initialize the FastAPI application with metadata
app = FastAPI(title="MasterMatch API", version="1.0.0")

# Global service instances (Singleton pattern usage for database connections)
auth_service = AuthService()


# --- Pydantic Models ---

class ChatRequest(BaseModel):
    """
    Schema for incoming chat messages.
    """
    username: str             # Unique identifier for the user context
    message: str              # The current query from the user
    thread_id: str            # Session ID to maintain conversation continuity
    history: Optional[List[Dict[str, str]]] = None  # Previous context (optional)

class ChatResponse(BaseModel):
    """
    Schema for the API response.
    Returns both the natural language text and any structured data found.
    """
    response: str
    data: Optional[List[Dict[str, Any]]] = None 


# --- Endpoints ---

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Core RAG Orchestrator Endpoint.

    This function handles the full lifecycle of a chat turn:
    1. Fetches User Profile (CV, Preferences) from DB.
    2. Lazy-loads or generates a 'Persona Summary' if one doesn't exist.
    3. Constructs a Dynamic System Prompt with strict constraints (Budget/City).
    4. Initializes the AI Client with this specific context.
    5. Executes the agent loop (Thought -> Tool -> Response).
    6. Logs the interaction and returns the result.
    """
    try:
        # 1. Get User Profile Data
        # Retrieve raw profile data (budget, GPA, CV text) to personalize the answer
        user_profile = auth_service.get_profile(request.username)
        
        # 2. Check for cached summary (The "User Persona")
        user_persona = user_profile.get("summary") 
        
        # Lazy Loading Strategy:
        # If the summary doesn't exist yet (first run or profile update), generate it now using the LLM.
        # This saves tokens on subsequent calls by caching the result.
        if not user_persona and user_profile:
             cv_text = user_profile.get("cv_text", "")
             # Only generate if we actually have data to summarize
             if cv_text or user_profile.get("background"):
                 manual_data = {
                     "background": user_profile.get("background"),
                     "budget": user_profile.get("budget"),
                     "interests": user_profile.get("interests"),
                     "gpa": user_profile.get("gpa")
                 }
                 # Call the helper from prompts.py
                 user_persona = generate_persona_summary(cv_text, manual_data)
                 
                 # Cache the result to the DB so we don't re-compute it next time
                 if user_persona:
                     auth_service.save_profile_summary(request.username, user_persona)

        # 3. System Instruction Construction
        # Build the initial system prompt using the Persona and intended behavior
        system_instruction = get_system_instruction(
            user_context=user_persona, 
            intent="general"
        )
        
        # Constraint Injection:
        # Explicitly append "Hard Constraints" (Budget, City) to the prompt.
        # This ensures the LLM sees these numbers clearly when calling tools, reducing hallucinations.
        if user_profile:
             constraints = []
             if user_profile.get("budget"): constraints.append(f"Budget Limit: {user_profile.get('budget')} EUR")
             if user_profile.get("city"): constraints.append(f"Preferred City: {user_profile.get('city')}")
             
             if constraints:
                 system_instruction += "\n\nHARD CONSTRAINTS (Use these in tool arguments):\n" + "\n".join(constraints)
        # ----------------------

        # 4. History & AI Execution
        # Limit history to last 15 turns to manage context window efficiency
        history_for_ai = request.history[-15:] if request.history else []
        
        # Initialize the Agent with the fully constructed context
        client = AIClient(
            history_messages=history_for_ai,
            system_instruction=system_instruction
        )
        
        # Run the agent (this triggers the Tool Calling loop if necessary)
        ai_response_text = client.send_message_to_agent(request.message)

        # 5. Extract Structured Data
        # If the agent called a tool (e.g., search_masters), retrieve the raw JSON data
        # so the Frontend can render it as interactive cards.
        found_programs = []
        if hasattr(client, 'last_tool_results') and client.last_tool_results:
            found_programs = client.last_tool_results
            # Convert ObjectIds to strings for JSON serialization
            for doc in found_programs:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])

        # 6. Persistence / Logging
        auth_service.save_message(request.thread_id, "user", request.message)
        auth_service.save_message(request.thread_id, "assistant", ai_response_text)

        return ChatResponse(response=ai_response_text, data=found_programs)

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{thread_id}")
def get_history(thread_id: str):
    """
    Retrieves the chat history for a specific conversation thread.
    Used by the frontend to populate the chat interface on load.
    """
    return auth_service.load_thread_messages(thread_id)