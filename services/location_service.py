import re
from services.db_service import DatabaseService

class LocationService:
    def __init__(self):
        self.db = DatabaseService()

    def get_location_link(self, university_name: str):
        collection = self.db.locations()
        doc = collection.find_one(
            {"Institution": {"$regex": f"^{re.escape(university_name)}$", "$options": "i"}}
        )
        return doc.get("GoogleMaps") if doc else None
