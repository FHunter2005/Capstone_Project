# Project/ai/prompts.py

"""
This module centralizes all system prompts and 'router' logic for the AI.
It constructs the final system instruction based on the user's context and intent.
"""

# The core personality of the agent
BASE_SYSTEM_INSTRUCTION = """
You are MasterMatch, an expert academic advisor for Master's degrees in Portugal.

YOUR BEHAVIOR:
1. GREETINGS: If the user says "Hello" or asks who you are, reply naturally. DO NOT use search tools.
2. SEARCHING: Only use the 'search_masters_tool' if the user explicitly asks for courses, programs, or topics.
3. PERSONALITY: Be professional, encouraging, and concise. 
4. CONTEXT: You only know about programs in the database. If you don't find results, suggest broader search terms.
"""

# Prompt used to summarize a long CV into a concise Persona
PERSONA_SUMMARIZER_PROMPT = """
You are an expert profile analyzer. Summarize this student's data into a specific 'User Persona' 
for an academic advisor AI. Focus ONLY on: 
- Academic background (GPA, Major)
- Financial Budget
- Specific Interests (AI, Data Science, etc.)
- Career Goals

Raw CV: {cv_text}
Manual Data: {manual_data}

Output a single paragraph starting with "User Persona:".
"""

def get_system_instruction(user_context: str = "", intent: str = "general") -> str:
    """
    ROUTER LOGIC:
    Constructs the final system instruction dynamically based on the situation.
    
    Args:
        user_context (str): The summarized user persona or raw context string.
        intent (str): The detected intent (e.g., 'general', 'research', 'support').
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