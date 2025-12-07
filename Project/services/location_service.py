# services/location_service.py
import re
from services.db_service import DatabaseService


class LocationService:
    def __init__(self):
        self.db = DatabaseService()
        self._maps = self.db.maps_location()

    def get_location_link(self, institution_name: str) -> str | None:
        """
        Return Google Maps link for a given university/institution name,
        using case-insensitive exact match.
        """
        doc = self._maps.find_one(
            {
                "Institution": {
                    "$regex": f"^{re.escape(institution_name)}$",
                    "$options": "i",
                }
            }
        )
        if not doc:
            return None
        return doc.get("GoogleMaps")