# services/embedding_service.py
import numpy as np
from ai.ai_client import AIClient
from services.db_service import DatabaseService
from tools.similarity_tool import cosine_similarity

class EmbeddingService:
    def __init__(self):
        self.ai = AIClient()
        self.db = DatabaseService()

    def generate_embedding(self, text: str) -> np.ndarray:
        values = self.ai.embed(text)
        return np.array(values, dtype=float)

    def ensure_embeddings(self):
        masters = self.db.masters()
        for doc in masters.find():
            if not doc.get("embedding"):
                source = doc.get("about") or doc.get("master", "")
                if not source:
                    continue
                emb = self.generate_embedding(source)
                masters.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"embedding": emb.tolist()}},
                )

    def search_similar(self, user_emb: np.ndarray, top_k: int = 5):
        """Return top_k results as (score, doc) tuples."""

        results = []
        masters = self.db.masters()

        for doc in masters.find():
            emb_list = doc.get("embedding", [])
            if not emb_list:
                continue

            emb = np.array(emb_list, dtype=float)
            score = cosine_similarity(user_emb, emb)

            results.append((score, doc))

    # Sort and return top_k tuples
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]

