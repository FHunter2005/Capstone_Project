# Project/ai/prompts.py
import google.generativeai as genai
from utils.config import Config

"""
AI Prompts & Router Logic.

This module centralizes all system prompts, persona definitions, and 'router' logic 
for the MasterMatch AI. It separates prompt management from application logic, 
making it easier to iterate on agent behavior without touching core code.

It also contains the logic to compress large, unstructured CVs into a concise 
'User Persona' that fits efficiently into the LLM's context window.
"""

# --- PROMPTS ---

# The core persona definition for the AI Agent.
# It defines the agent's identity, operational constraints, and fallback behaviors.
BASE_SYSTEM_INSTRUCTION = """
You are MasterMatch, an expert academic advisor for Master's degrees in Portugal.

YOUR BEHAVIOR:
1. GREETINGS: If the user says "Hello" or asks who you are, reply naturally.
2. USE THE TOOL CORRECTLY: When searching, you MUST check the "User Persona" or "User Context" for constraints.
   - If the user has a **Budget** (e.g., 1500), pass `max_budget=1500` to the tool.
   - If the user has a **City** (e.g., Lisbon), pass `preferred_location="Lisbon"` to the tool.
   - If the user has a **Duration** preference, pass `preferred_duration` to the tool.
   
3. SAFETY NET: The tool will tell you if no exact matches exist.
   - If the tool says "NO EXACT MATCHES", explicitly tell the user: "I couldn't find any programs that strictly match your budget/location preferences, but here are the closest options:"
   - Do NOT invent programs.

4. PERSONALITY: Be professional, encouraging, and concise.
"""

# Prompt used to distill raw user data (CV + Q&A) into a token-efficient summary.
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
    Calls the LLM to summarize a potentially long CV and manual form data into a 
    concise 'User Persona' string.

    This optimization reduces the number of tokens passed to the agent in subsequent 
    chat turns, saving cost and latency while preserving key context.

    Args:
        cv_text (str): The raw text extracted from the user's PDF CV.
        manual_data (dict): Dictionary containing answers from the onboarding questionnaire (e.g., GPA, Budget).

    Returns:
        str: A concise summary paragraph (e.g., "User Persona: A Data Science student with a 2000 EUR budget...").
             Returns an empty string on failure to prevent blocking the flow.
    """
    try:
        genai.configure(api_key=Config.GOOGLE_API_KEY)
        # Using the standard model for summarization tasks
        model = genai.GenerativeModel(Config.LLM_MODEL)
        
        # Safely truncate extremely long text to avoid hitting context window limits
        # (20k chars is well within Gemini 1.5's limit, but good for safety).
        safe_cv = cv_text[:20000] if cv_text else "No CV provided."
        
        prompt = PERSONA_SUMMARIZER_PROMPT.format(
            cv_text=safe_cv,
            manual_data=str(manual_data)
        )
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Log error but don't crash; the app can function without a persona summary if needed
        print(f"⚠️ Error generating persona summary: {e}")
        return ""

def get_system_instruction(user_context: str = "", intent: str = "general") -> str:
    """
    Constructs the final system instruction dynamically based on the user's context and intent.

    This implements a basic 'Router' pattern: modifying the agent's instructions 
    at runtime to better suit the current task (e.g., stricter fact-checking vs. empathetic support).

    Args:
        user_context (str): The generated persona summary (from generate_persona_summary).
        intent (str): The detected intent of the conversation (default: "general"). 
                      Can be 'research', 'support', etc.

    Returns:
        str: The complete, concatenated system prompt to be sent to the LLM.
    """
    
    # 1. Start with the Base Instruction (Identity & Constraints)
    instruction = BASE_SYSTEM_INSTRUCTION

    # 2. Apply Mode/Router Logic (Extensible)
    # Appends specific behavioral instructions based on the requested 'intent'
    if intent == "research":
        instruction += "\n\nCURRENT MODE: Deep Researcher. Focus strictly on facts, tuition fees, and admission requirements."
    elif intent == "support":
        instruction += "\n\nCURRENT MODE: Empathetic Mentor. Be reassuring and focus on the student's potential."
    
    # 3. Inject User Context (The Persona)
    # This places the user's specific data at the end of the prompt to ensure high attention
    if user_context:
        instruction += f"\n\nUSER CONTEXT (Prioritize this info):\n{user_context}"

    return instruction