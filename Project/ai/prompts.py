# Project/ai/prompts.py
import google.generativeai as genai
from utils.config import Config

"""
This module centralizes all system prompts and 'router' logic for the AI.
It also contains the utility to compress large CVs into a 'User Persona'.
"""

# --- PROMPTS ---

BASE_SYSTEM_INSTRUCTION = """
You are MasterMatch, an expert academic advisor for Master's degrees in Portugal.

YOUR BEHAVIOR:
1. GREETINGS: If the user says "Hello" or asks who you are, reply naturally. DO NOT use search tools.
2. SEARCHING: Only use the 'search_masters_tool' if the user explicitly asks for courses, programs, or topics.
3. PERSONALITY: Be professional, encouraging, and concise. 
4. CONTEXT: You only know about programs in the database. If you don't find results, suggest broader search terms.
"""

PERSONA_SUMMARIZER_PROMPT = """
You are an expert profile analyzer. Summarize this student's data into a specific 'User Persona' 
for an academic advisor AI. 

INSTRUCTIONS:
- Condense the provided CV and manual data into a short semantic summary (max 200 words).
- Focus ONLY on: Academic background (Major, GPA), Financial Budget, Specific Interests, and Career Goals.
- Ignore irrelevant personal details (address, phone, primary school).

Raw CV: {cv_text}
Manual Data: {manual_data}

Output a single paragraph starting with "User Persona:".
"""

# --- FUNCTIONS ---

def generate_persona_summary(cv_text: str, manual_data: dict) -> str:
    """
    Calls the LLM to summarize a long CV into a concise User Persona.
    Uses the configured model (or a faster/cheaper one if specified).
    """
    try:
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        model = genai.GenerativeModel(Config.LLM_MODEL)
        
        # safely truncate extremely long text just to fit context window if needed, 
        # but 10k chars is usually fine for Gemini 1.5
        safe_cv = cv_text[:20000] if cv_text else "No CV provided."
        
        prompt = PERSONA_SUMMARIZER_PROMPT.format(
            cv_text=safe_cv,
            manual_data=str(manual_data)
        )
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ Error generating persona summary: {e}")
        return ""

def get_system_instruction(user_context: str = "", intent: str = "general") -> str:
    """
    ROUTER LOGIC:
    Constructs the final system instruction dynamically based on the situation.
    """
    
    # 1. Start with the Base Instruction
    instruction = BASE_SYSTEM_INSTRUCTION

    # 2. Apply Mode/Router Logic (Extensible)
    if intent == "research":
        instruction += "\n\nCURRENT MODE: Deep Researcher. Focus strictly on facts, tuition fees, and admission requirements."
    elif intent == "support":
        instruction += "\n\nCURRENT MODE: Empathetic Mentor. Be reassuring and focus on the student's potential."
    
    # 3. Inject User Context (The Persona)
    if user_context:
        instruction += f"\n\nUSER CONTEXT (Prioritize this info):\n{user_context}"

    return instruction