# Project/services/location_service.py
import re
from services.db_service import DatabaseService


class LocationService:
    """
    Geospatial Data Service.

    This service abstracts the logic for retrieving location-specific data 
    (specifically Google Maps links) for universities. It ensures that the 
    application can resolve institution names to navigable URLs, used primarily 
    by the Map visualization and the AI agent tools.
    """

    def __init__(self):
        """
        Initializes the service by connecting to the 'Maps_Location' collection.
        """
        self.db = DatabaseService()
        self._maps = self.db.maps_location()

    def get_location_link(self, institution_name: str) -> str | None:
        """
        Retrieves the Google Maps URL for a specific institution.

        This method employs a case-insensitive regex search to ensure robust matching,
        handling slight variations in capitalization provided by the user or the LLM
        (e.g., "Instituto superior tecnico" vs "Instituto Superior Técnico").

        Args:
            institution_name (str): The name of the university.

        Returns:
            str | None: The Google Maps URL if found, otherwise None.
        """
        # Perform a case-insensitive exact match search.
        # Regex Breakdown:
        #   ^             : Start of string anchor (ensures exact match, not partial)
        #   re.escape(...) : Safely escapes special chars (like brackets) in the name
        #   $             : End of string anchor
        #   $options: "i" : MongoDB flag for case-insensitivity
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