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

app = FastAPI(title="MasterMatch API", version="1.0.0")

# Global instances to avoid re-initializing on every request
auth_service = AuthService()

# This helper will look for the "Authorization: Bearer <token>" header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- Security Dependency ---
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Verifies the JWT token and returns the username. 
    Raises 401 if the token is invalid or expired.
    """
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
    current_user: str = Depends(get_current_user) # Protect the endpoint
):
    try:
        # Security Check: Ensure the token-user matches the requested username
        if current_user != request.username:
            raise HTTPException(status_code=403, detail="Forbidden: You cannot act as another user")

        # 1. Get User Profile Context
        user_profile = auth_service.get_profile(request.username)
        
        context_str = ""
        if user_profile:
            cv_text = user_profile.get("cv_text", "")
            background = user_profile.get("background", "N/A")
            gpa = user_profile.get("gpa", "N/A")
            budget = user_profile.get("budget", "N/A")
            interests = user_profile.get("interests", "N/A")

            context_str = "USER CONTEXT (Prioritize this info):"
            if cv_text:
                context_str += f"\n[RESUME/CV CONTENT]: {cv_text[:3000]}..." 
            
            if background != "N/A" or budget != "N/A":
                context_str += (
                    f"\n[MANUAL PROFILE]: "
                    f"Background: {background}, "
                    f"GPA: {gpa}, "
                    f"Budget: {budget}, "
                    f"Interests: {interests}."
                )

        # 2. Prepare History
        history_for_ai = request.history[-15:] if request.history else []
        if context_str:
            history_for_ai.insert(0, {"role": "system", "content": context_str})

        # 3. Run AI and Capture Tool Results
        client = AIClient(history_messages=history_for_ai)
        ai_response_text = client.send_message_to_agent(request.message)

        # 4. Extract Data from Tool Calls
        found_programs = []
        if hasattr(client, 'last_tool_results') and client.last_tool_results:
            found_programs = client.last_tool_results
            for doc in found_programs:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])

        # 5. Save to DB
        auth_service.save_message(request.thread_id, "user", request.message)
        auth_service.save_message(request.thread_id, "assistant", ai_response_text)

        return ChatResponse(response=ai_response_text, data=found_programs)

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))