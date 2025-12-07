# services/query_engine.py

import re
from typing import List, Dict

from services.db_service import DatabaseService
from services.embedding_service import EmbeddingService
from services.location_service import LocationService
from ai.ai_client import AIClient
from ai.prompts import multi_program_prompt


class QueryEngine:
    """
    Full search + explanation pipeline.
    Replaces all logic previously in testing.py.
    """

    def __init__(self):
        self.db = DatabaseService()
        self.embedding_service = EmbeddingService()
        self.location_service = LocationService()
        self.ai = AIClient()
        self._masters = self.db.masters()

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
        user_emb = self.embedding_service.generate_embedding(user_input)
        scored = self.embedding_service.search_similar(user_emb, top_k=top_k)  
        # scored = [(score, doc), ...]

        if not scored:
            return []

        # Sort again just in case
        scored.sort(key=lambda x: x[0], reverse=True)

        MIN_ABS_SCORE = 0.55        # absolute threshold
        DROP_RATIO = 0.70           # relative threshold compared to best score

        top_score = scored[0][0]
        filtered = []

        for score, doc in scored:
            if score < MIN_ABS_SCORE:
                break
            if score < top_score * DROP_RATIO:
                break
            filtered.append(doc)

        return filtered

    # ---------------------------- MAIN PIPELINE ----------------------------

    def handle_user_query(self, user_input: str) -> str:
        """
        The main pipeline used by the Streamlit UI.
        """

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
                return "❌ No matching master's programs found."

        
        # 4) LLM EXPLANATION
        prompt = multi_program_prompt(docs, user_input)
        explanation = self.ai.generate(prompt)

        return explanation.strip() if explanation else "No elaborated text available."