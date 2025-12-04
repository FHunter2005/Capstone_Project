import re
from ai.ai_client import AIClient
from ai.prompts import elaboration_prompt
from services.embedding_service import EmbeddingService
from services.location_service import LocationService
from services.db_service import DatabaseService
from ai.ai_client import AIClient


"""class MasterService:
    def __init__(self):
        self.db = DatabaseService()

    def fallback_search(self, query: str):
        regex = re.compile(re.escape(query), re.IGNORECASE)
        cursor = self.db.masters().find({"master": {"$regex": regex}})
        return list(cursor)[:5]


class MasterService:
    def __init__(self):
        self.ai = AIClient()
        self.db = DatabaseService()
        self.location_service = LocationService()

    def elaborate_answer(self, master_doc: dict, user_query: str) -> str:
        prompt = elaboration_prompt(master_doc, user_query)
        try:
            response = self.ai.generate(prompt)
            return response.text or "No elaborated text available."
        except Exception as e:
            return f"(Could not generate elaboration: {e})"



class MasterService:

    def __init__(self):
        self.db = DatabaseService()
        self.embedding_service = EmbeddingService()
        self.location_service = LocationService()
        self.ai = AIClient()

    def handle_query(self, user_input: str) -> list[dict]:
        '''
        Returns a list of master program dictionaries, each enriched with:
        - elaborated_text
        - location_link
        '''

        # 1. Check for direct match
        direct = self._search_by_exact_name(user_input)
        if direct:
            return [self._enrich_master(direct, user_input)]

        # 2. Semantic search
        try:
            user_emb = self.embedding_service.generate_embedding(user_input)
            matches = self.embedding_service.search_similar(user_emb, top_k=5)
        except Exception:
            matches = []

        # 3. Fallback
        if not matches:
            matches = self.fallback_search(user_input)

        if not matches:
            return []

        # 4. Enrich all results
        return [self._enrich_master(doc, user_input) for doc in matches]"""

class MasterService:
    def __init__(self):
        self.db = DatabaseService()
        self.embedding_service = EmbeddingService()
        self.location_service = LocationService()
        self.ai = AIClient()

    def _search_by_exact_name(self, name: str):
        return self.db.masters().find_one({"master": {"$regex": f"^{re.escape(name)}$", "$options": "i"}})

    def fallback_search(self, query: str):
        regex = re.compile(re.escape(query), re.IGNORECASE)
        cursor = self.db.masters().find({"master": {"$regex": regex}})
        return list(cursor)[:5]

    def elaborate_answer(self, master_doc: dict, user_query: str) -> str:
        prompt = elaboration_prompt(master_doc, user_query)
        try:
            response = self.ai.generate(prompt)
            return response.text or "No elaborated text available."
        except Exception as e:
            return f"(Could not generate elaboration: {e})"
    
    def _enrich_master(self, master_doc: dict, user_query: str) -> dict:
        enriched = master_doc.copy()
        print("DEBUG DOCUMENT master_doc:", master_doc)
        enriched["location"] = master_doc.get("Location")
        enriched["tuition_fee"] = master_doc.get("Tuition Fee")
        enriched["duration"] = master_doc.get("Duration")
        # Generate elaborated answer
        enriched["elaborated_text"] = self.elaborate_answer(master_doc, user_query)
        print("DEBUG DOCUMENT enriched:", enriched)

    
        return enriched


    def handle_query(self, user_input: str) -> list[dict]:
        direct = self._search_by_exact_name(user_input)
        if direct:
            return [self._enrich_master(direct, user_input)]
         # 2. Semantic search
        try:
            user_emb = self.embedding_service.generate_embedding(user_input)
            matches = self.embedding_service.search_similar(user_emb, top_k=5)
        except Exception:
            matches = []

        # 3. Fallback
        if not matches:
            matches = self.fallback_search(user_input)

        if not matches:
            return []

        # 4. Enrich all results
        return [self._enrich_master(doc, user_input) for doc in matches]
    