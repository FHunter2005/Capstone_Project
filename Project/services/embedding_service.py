# services/embedding_service.py
from ai.ai_client import AIClient
from services.db_service import DatabaseService

class EmbeddingService:
    def __init__(self):
        self.ai = AIClient()
        self.db = DatabaseService()

    def generate_embedding(self, text: str) -> list:
        """Generates the vector (list of floats) for the text."""
        # MongoDB accepts normal Python lists
        return self.ai.embed(text)

    def search_similar(self, user_emb: list, top_k: int = 5):
        """
        Uses MongoDB Atlas Vector Search to find similar documents.
        Returns a list of tuples: (score, doc)
        """
        collection = self.db.masters()

        # The vector search pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "embedding",   
                    "queryVector": user_emb,    
                    "numCandidates": top_k * 20, 
                    "limit": top_k                
                }
            },
            {
                "$project": {
                    "embedding": 0,  # Does not bring back the huge vector (saves internet)
                    "score": {"$meta": "vectorSearchScore"}  # Includes the similarity score
                }
            }
        ]

        # Executes the search on the Mongo server
        cursor = collection.aggregate(pipeline)

        # Formats the results to maintain compatibility with your query_engine.py
        # Expected format: [(score, doc), (score, doc), ...]
        results = []
        for doc in cursor:
            # Removes the score from the document and stores it separately
            score = doc.pop("score", 0.0)
            results.append((score, doc))

        return results