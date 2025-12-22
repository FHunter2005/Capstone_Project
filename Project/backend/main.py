# backend/main.py
import sys
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.ai_client import AIClient
from services.auth_service import AuthService
from ai.prompts import get_system_instruction, PERSONA_SUMMARIZER_PROMPT # Import the new Prompt Layer

app = FastAPI(title="MasterMatch API", version="1.0.0")

# Global instances
auth_service = AuthService()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- Security Dependency ---
async def get_current_user(token: str = Depends(oauth2_scheme)):
    username = auth_service.verify_token(token)
    if not username:
        raise HTTPException(
            status_code=401, 
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username

class ChatRequest(BaseModel):
    username: str
    message: str
    thread_id: str
    history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    response: str
    data: Optional[List[Dict[str, Any]]] = None 

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest, 
    current_user: str = Depends(get_current_user)
):
    try:
        if current_user != request.username:
            raise HTTPException(status_code=403, detail="Forbidden: You cannot act as another user")

        # 1. Get User Profile Data
        user_profile = auth_service.get_profile(request.username)
        
        # 2. Formulate Context String (Raw or Summary)
        # Note: In a future step, we can use PERSONA_SUMMARIZER_PROMPT here to generate a cached summary
        context_str = ""
        if user_profile:
            cv_text = user_profile.get("cv_text", "")
            background = user_profile.get("background", "N/A")
            gpa = user_profile.get("gpa", "N/A")
            budget = user_profile.get("budget", "N/A")
            interests = user_profile.get("interests", "N/A")

            # Simple concatenation for now, passed to the Prompt Layer
            if cv_text:
                context_str += f"[RESUME/CV CONTENT]: {cv_text[:3000]}... "
            
            if background != "N/A" or budget != "N/A":
                context_str += (
                    f"\n[MANUAL PROFILE]: "
                    f"Background: {background}, "
                    f"GPA: {gpa}, "
                    f"Budget: {budget}, "
                    f"Interests: {interests}."
                )

        # 3. Call the Prompt Router
        # We can detect intent here (e.g. if 'search' in message), or default to "general"
        current_intent = "general" 
        system_instruction = get_system_instruction(
            user_context=context_str, 
            intent=current_intent
        )

        # 4. Prepare History (Clean, no system injection here)
        history_for_ai = request.history[-15:] if request.history else []

        # 5. Run AI with Dynamic System Instruction
        client = AIClient(
            history_messages=history_for_ai,
            system_instruction=system_instruction # Pass the router result
        )
        ai_response_text = client.send_message_to_agent(request.message)

        # 6. Extract Data from Tool Calls
        found_programs = []
        if hasattr(client, 'last_tool_results') and client.last_tool_results:
            found_programs = client.last_tool_results
            for doc in found_programs:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])

        # 7. Save to DB
        auth_service.save_message(request.thread_id, "user", request.message)
        auth_service.save_message(request.thread_id, "assistant", ai_response_text)

        return ChatResponse(response=ai_response_text, data=found_programs)

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))