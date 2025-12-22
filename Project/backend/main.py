# Project/backend/main.py
import sys
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.ai_client import AIClient
from services.auth_service import AuthService
from ai.prompts import get_system_instruction, generate_persona_summary

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

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    username: str
    message: str
    thread_id: str
    history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    response: str
    data: Optional[List[Dict[str, Any]]] = None 

# ✅ ADDED: Missing LoginRequest Model
class LoginRequest(BaseModel):
    username: str
    password: str

# --- Endpoints ---

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
        
        # 2. Check for cached summary
        user_persona = user_profile.get("summary") 
        
        # Lazy Loading Summary
        if not user_persona and user_profile:
             cv_text = user_profile.get("cv_text", "")
             if cv_text or user_profile.get("background"):
                 manual_data = {
                     "background": user_profile.get("background"),
                     "budget": user_profile.get("budget"),
                     "interests": user_profile.get("interests"),
                     "gpa": user_profile.get("gpa")
                 }
                 user_persona = generate_persona_summary(cv_text, manual_data)
                 if user_persona:
                     auth_service.save_profile_summary(request.username, user_persona)

        # 3. System Instruction
        system_instruction = get_system_instruction(
            user_context=user_persona, 
            intent="general"
        )
        
        # Explicitly append structured constraints to ensure the AI sees the numbers
        if user_profile:
             constraints = []
             if user_profile.get("budget"): constraints.append(f"Budget Limit: {user_profile.get('budget')} EUR")
             if user_profile.get("city"): constraints.append(f"Preferred City: {user_profile.get('city')}")
             
             if constraints:
                 system_instruction += "\n\nHARD CONSTRAINTS (Use these in tool arguments):\n" + "\n".join(constraints)
        # ----------------------

        # 4. History & AI Call
        history_for_ai = request.history[-15:] if request.history else []
        client = AIClient(
            history_messages=history_for_ai,
            system_instruction=system_instruction
        )
        ai_response_text = client.send_message_to_agent(request.message)

        # 5. Extract Tool Data
        found_programs = []
        if hasattr(client, 'last_tool_results') and client.last_tool_results:
            found_programs = client.last_tool_results
            for doc in found_programs:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])

        # 6. Save Logs
        auth_service.save_message(request.thread_id, "user", request.message)
        auth_service.save_message(request.thread_id, "assistant", ai_response_text)

        return ChatResponse(response=ai_response_text, data=found_programs)

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
def login(creds: LoginRequest):
    # This keeps the logic on the server side
    user = auth_service.login_user(creds.username, creds.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = auth_service.create_access_token({"sub": user["username"]})
    
    return {
        "token": token, 
        "name": user.get("name"), 
        "username": user.get("username")
    }

@app.get("/history/{thread_id}")
def get_history(thread_id: str, current_user: str = Depends(get_current_user)):
    return auth_service.load_thread_messages(thread_id)