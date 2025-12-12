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
        """
        Semantic search with dynamic thresholding:
        - Adjusts similarity threshold based on query length and top score.
        - Returns up to top_k results that meet the dynamic threshold.
        """

        # 1) Generate embedding
        user_emb = self.embedding_service.generate_embedding(user_input)

        # 2) Perform similarity search → list of (score, doc)
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

        # Adjust based on length of query
        if word_count <= 2:
            threshold -= 0.10       # vague query → lower threshold
        elif word_count >= 8:
            threshold += 0.05       # very specific → raise threshold

        # Adjust based on semantic strength (top similarity)
        if top_score >= 0.85:
            threshold += 0.05       # strong signal → stricter
        elif top_score <= 0.55:
            threshold -= 0.10       # weak signal → more lenient

        # Clamp between 0.35 and 0.75
        threshold = max(0.35, min(threshold, 0.70))

        # 5) Filter based on dynamic threshold
        filtered = [doc for score, doc in scored if score >= threshold]

        # 6) Return up to top_k
        return filtered[:top_k]

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