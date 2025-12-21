# backend/main.py
import sys
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.ai_client import AIClient
from services.auth_service import AuthService
# IMPORT THE BUFFER
from tools.agent_tools import RESULTS_BUFFER 

app = FastAPI(title="MasterMatch API", version="1.0.0")

class ChatRequest(BaseModel):
    username: str
    message: str
    thread_id: str
    history: Optional[List[Dict[str, str]]] = None

# --- UPDATE THE RESPONSE MODEL ---
class ChatResponse(BaseModel):
    response: str
    data: Optional[List[Dict[str, Any]]] = None  # New field for the cards!

# In backend/main.py

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # 1. Clear buffer
        RESULTS_BUFFER.clear()

        # 2. Get User Profile Context (The New Logic)
        auth = AuthService()
        user_profile = auth.get_profile(request.username)
        
        # Create a "System Context" string
        context_str = ""
        if user_profile:
            # Check if they have CV text
            cv_text = user_profile.get("cv_text", "")
            
            # Check if they have Q&A answers
            background = user_profile.get("background", "N/A")
            gpa = user_profile.get("gpa", "N/A")
            budget = user_profile.get("budget", "N/A")
            interests = user_profile.get("interests", "N/A")

            context_str = f"USER CONTEXT (Prioritize this info):"
            
            if cv_text:
                context_str += f"\n[RESUME/CV CONTENT]: {cv_text[:3000]}..." # Limit text length
            
            if background != "N/A" or budget != "N/A":
                context_str += (
                    f"\n[MANUAL PROFILE]: "
                    f"Background: {background}, "
                    f"GPA: {gpa}, "
                    f"Budget: {budget}, "
                    f"Interests: {interests}."
                )

        # 3. Prepare History
        # We inject the profile context as a "system" message at the VERY START
        history_for_ai = request.history[-15:] if request.history else []
        
        if context_str:
            # Insert context at index 0 so AI sees it first
            history_for_ai.insert(0, {"role": "system", "content": context_str})

        # 4. Run AI
        client = AIClient(history_messages=history_for_ai)
        ai_response = client.send_message_to_agent(request.message)

        # 5. Save to DB (Save original message to keep chat clean)
        auth.save_message(request.thread_id, "user", request.message)
        auth.save_message(request.thread_id, "assistant", ai_response)

        # 6. Grab data & Fix IDs
        found_programs = list(RESULTS_BUFFER)
        for doc in found_programs:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        return ChatResponse(response=ai_response, data=found_programs)

    except Exception as e:
        print(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))