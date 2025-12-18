# services/query_engine.py

import re
from typing import List, Dict

from services.db_service import DatabaseService
from services.embedding_service import EmbeddingService
from services.location_service import LocationService
from ai.ai_client import AIClient
from ai.prompts import multi_program_prompt

SYSTEM_PERSONA = (
    "You are an expert Academic Advisor AI. "
    "Your goal is to help users find their ideal Master's degree. "
    "You are friendly, proactive, optimistic and professional. "
    "NEVER say you are a 'large language model' or 'trained by Google'. "
    "If asked who you are, say you are a specialized Study Advisor helper."
)
class QueryEngine:
    """
    Full search + explanation pipeline.
    Now includes an Intent Router to handle chitchat vs. search queries.
    """

    def __init__(self):
        self.db = DatabaseService()
        self.embedding_service = EmbeddingService()
        self.location_service = LocationService()
        self.ai = AIClient()
        self._masters = self.db.masters()

    # ---------------------------- INTENT ROUTER ----------------------------

    def _classify_intent(self, user_input: str) -> str:
        """
        Classifies the user input into one of three categories:
        1. GREETING (Hello, thanks, bye)
        2. QUESTION (General knowledge, definitions, 'Why are trees brown?')
        3. SEARCH (Explicit requests for courses, degrees, 'Find me masters in biology')
        """
        # 1. Fast Regex Check for Greetings (Save API calls)
        common_greetings = r"^(hello|hi|hey|good morning|thanks|thank you|thx|bye)\W*$"
        if re.match(common_greetings, user_input.strip(), re.IGNORECASE):
            return "GREETING"

        # 2. Smart LLM Check
        classification_prompt = (
            f"Analyze this user input: '{user_input}'.\n"
            "Classify it into exactly one of these categories:\n"
            "- 'GREETING': If it is simple small talk or gratitude.\n"
            "- 'QUESTION': If the user is asking a general fact-based question (e.g., 'Why is the sky blue?', 'What is AI?') and NOT explicitly asking for a university course.\n"
            "- 'SEARCH': If the user is looking for a master's program, course, degree, or studying options.\n\n"
            "Reply with exactly one word: GREETING, QUESTION, or SEARCH."
        )
        
        try:
            response = self.ai.generate(classification_prompt).strip().upper()
            # Safety fallback: if LLM hallucinates, default to search if keywords exist
            if "QUESTION" in response: return "QUESTION"
            if "GREETING" in response: return "GREETING"
            return "SEARCH"
        except Exception:
            return "SEARCH"
    
# ---------------------------- HANDLERS ----------------------------

    def _handle_chitchat(self, user_input: str) -> str:
        """
        Handles small talk.
        FIX: Added instructions to be PROACTIVE (ask back).
        """
        prompt = (
            f"{SYSTEM_PERSONA}\n\n"
            f"The user said: '{user_input}'.\n"
            f"Reply naturally and empathetically. "
            f"Crucially, do not just answer; keep the conversation going by asking a polite follow-up question "
            f"related to their well-being or their study interests."
        )
        return self.ai.generate(prompt)

    def _handle_general_question(self, user_input: str) -> str:
        """
        Handles general questions or identity questions.
        FIX: Dynamic transition to sales pitch, only if relevant.
        """
        prompt = (
            f"{SYSTEM_PERSONA}\n\n"
            f"The user asked: '{user_input}'.\n"
            f"Instructions:\n"
            f"1. Answer the question clearly.\n"
            f"2. LOGIC CHECK: \n"
            f"   - If the user asked about YOU (your specialty, name, identity), answer that, but DO NOT ask to show courses yet. Just ask how you can help.\n"
            f"   - If the user asked about an ACADEMIC TOPIC (e.g., 'Why is history important?', 'What is MBA?'), answer the fact, and then naturally ask if they would like to see Master's programs related to that topic.\n"
            f"3. VARY YOUR PHRASING: Never use the exact same phrase twice. Be conversational."
        )
        return self.ai.generate(prompt)

    # ---------------------------- DIRECT MATCH ----------------------------

    def _detect_direct_reference(self, user_input: str) -> Dict | None:
        """
        If user mentions a master's program name exactly, return that document.
        """
        cursor = self._masters.find({}, {"master": 1})
        for doc in cursor:
            name = doc.get("master")
            if not name:
                continue
            if re.search(rf"\b{re.escape(name)}\b", user_input, re.IGNORECASE):
                return self._masters.find_one({"_id": doc["_id"]})
        return None

    # ---------------------------- FALLBACK SEARCH ----------------------------

    def _keyword_fallback(self, query: str, limit: int = 5) -> List[Dict]:
        regex = re.compile(re.escape(query), re.IGNORECASE)
        cursor = self._masters.find({"master": {"$regex": regex}})
        return list(cursor)[:limit]

    # ---------------------------- SEMANTIC SEARCH ----------------------------

    def _semantic_search(self, user_input: str, top_k: int = 5) -> List[Dict]:
        # ... (Keep your existing semantic search logic exactly as is) ...
        # For brevity, I am hiding the body, but keep your existing code here.
        
        # 1) Generate embedding
        user_emb = self.embedding_service.generate_embedding(user_input)

        # 2) Perform similarity search
        scored = self.embedding_service.search_similar(user_emb, top_k=top_k)
        if not scored:
            return []

        # Sort descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # 3) Extract clarity signals
        word_count = len(user_input.split())
        top_score = scored[0][0]

        # 4) Start with a base threshold
        threshold = 0.30

        if word_count <= 2:
            threshold -= 0.10
        elif word_count >= 8:
            threshold += 0.05

        if top_score >= 0.85:
            threshold += 0.05
        elif top_score <= 0.55:
            threshold -= 0.10

        threshold = max(0.35, min(threshold, 0.70))

        filtered = [doc for score, doc in scored if score >= threshold]
        return filtered[:top_k]

    # ---------------------------- MAIN PIPELINE ----------------------------

    def handle_user_query(self, user_input: str) -> str:
        """
        The main pipeline used by the Streamlit UI.
        """

        # --- STEP 0: DETERMINE INTENT ---
        intent = self._classify_intent(user_input)

        if intent == "GREETING":
            return self._handle_chitchat(user_input)
        
        if intent == "QUESTION":
            # This handles "Why are trees brown?"
            # It answers the fact, then asks "Do you want to see courses?"
            # It does NOT run the database search yet.
            return self._handle_general_question(user_input)
        
        # --- SEARCH PIPELINE (Runs only if intent is SEARCH) ---

        # 1) DIRECT MATCH
        direct = self._detect_direct_reference(user_input)
        if direct:
            docs = [direct]
        else:
            # 2) SEMANTIC SEARCH
            try:
                docs = self._semantic_search(user_input, top_k=5)
            except Exception as e:
                return f"❌ Error generating search results: {e}"

            # 3) FALLBACK
            if not docs:
                docs = self._keyword_fallback(user_input)

            if not docs:
                # If search fails, maybe it was a weird conversation? 
                # Optional: fallback to chat here if you want, 
                # but returning "No programs found" is usually safer.
                return "❌ No matching master's programs found."

        # 4) LLM EXPLANATION
        prompt = multi_program_prompt(docs, user_input)
        explanation = self.ai.generate(prompt)

        return explanation.strip() if explanation else "No elaborated text available."