# Project/services/auth_service.py
import bcrypt
import os
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from services.db_service import DatabaseService

class AuthService:
    """
    Handles User Authentication, Profile Management, and Chat Persistence.

    This service acts as the intermediary between the API/Frontend and the MongoDB database.
    It encapsulates all logic related to:
    1. User Security (Registration, Login, Password Hashing).
    2. User Profile Data (CVs, Preferences, Favorites).
    3. Chat History (Creating threads, saving messages, retrieving logs).
    """

    def __init__(self):
        """
        Initializes the service by connecting to the specific MongoDB collections.
        """
        self.db = DatabaseService()
        self.users = self.db.users()       # Collection for user credentials & profiles
        self.logs = self.db.chat_logs()    # Collection for chat history threads

    # --- Security Methods ---

    def hash_password(self, password: str) -> str:
        """
        Hashes a plain-text password using bcrypt with a generated salt.
        """
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verifies a plain-text password against a stored bcrypt hash.
        """
        return bcrypt.checkpw(password.encode(), hashed.encode())

    # --- User Management ---

    def register_user(self, username: str, name: str, password: str):
        """
        Creates a new user document in the database.
        Returns (success: bool, message: str).
        """
        # Check for duplicates to enforce unique usernames
        if self.users.find_one({"username": username}):
            return False, "Username already exists."

        self.users.insert_one(
            {
                "username": username,
                "name": name,
                "password": self.hash_password(password),
                "created_at": datetime.now(),
                "favorites": [], # Initialize empty favorites list
            }
        )
        return True, "Account created successfully!"

    def login_user(self, username: str, password: str):
        """
        Authenticates a user.
        Returns the User object (dict) if successful, or None if invalid.
        """
        user = self.users.find_one({"username": username})
        if user and self.verify_password(password, user["password"]):
            return user
        return None

    # --- Favorites Logic ---

    def add_favorite(self, username: str, master_data: dict):
        """
        Adds a Master's program to the user's favorites list.
        Prevents duplicates by checking if the (master, university) pair already exists.
        """
        # Check if this specific program is already in the array
        existing = self.users.find_one({
            "username": username,
            "favorites": {
                "$elemMatch": {
                    "master": master_data.get("master"),
                    "university": master_data.get("university") 
                }
            }
        })

        if existing:
            return False, "Already in favorites!"

        # Create a standardized favorite object
        fav_item = {
            "master": master_data.get("master"),
            "university": master_data.get("university"),
            "location": master_data.get("Location"),
            "tuition": master_data.get("Tuition Fee"),
            "about": master_data.get("about"),
            "saved_at": datetime.now(),
        }

        # Atomically push to the favorites array
        self.users.update_one(
            {"username": username},
            {"$push": {"favorites": fav_item}},
        )

        return True, "Saved to favorites!"

    def get_user_favorites(self, username: str):
        """Returns the list of saved programs for a user."""
        user = self.users.find_one({"username": username}, {"favorites": 1})
        if user and "favorites" in user:
            return user["favorites"]
        return []

    def remove_favorite(self, username: str, master_name: str, university_name: str):
        """
        Removes a specific program from the favorites array based on master/uni name.
        """
        self.users.update_one(
            {"username": username},
            {"$pull": {"favorites": {"master": master_name, "university": university_name}}}
        )

    # --- Chat History & Threads ---

    def create_new_thread(self, username: str, title: str = "New Chat") -> str:
        """
        Starts a new conversation thread.
        Returns the new Thread ID (str).
        """
        new_thread = {
            "username": username,
            "title": title,
            "created_at": datetime.now(),
            "messages": [],
        }
        result = self.logs.insert_one(new_thread)
        return str(result.inserted_id)

    def get_user_threads(self, username: str):
        """
        Retrieves all conversation threads for a user, sorted by most recent.
        Used to populate the sidebar history list.
        """
        cursor = self.logs.find({"username": username}).sort("created_at", -1)
        threads = []
        for doc in cursor:
            threads.append(
                {
                    "id": str(doc["_id"]),
                    "title": doc.get("title", "Untitled Chat"),
                    "date": doc["created_at"].strftime("%Y-%m-%d %H:%M"),
                }
            )
        return threads

    def load_thread_messages(self, thread_id: str):
        """
        Fetches the full message history for a specific thread ID.
        Returns a list of dicts: [{"role": "user", "content": "..."}, ...]
        """
        if not thread_id:
            return []
        try:
            doc = self.logs.find_one({"_id": ObjectId(thread_id)})
            if doc and "messages" in doc:
                # Transform to standard format expected by Frontend/AI Client
                return [{"role": m["role"], "content": m["content"]} for m in doc["messages"]]
        except Exception:
            return []
        return []

    def save_message(self, thread_id: str, role: str, content: str):
        """
        Appends a new message (User or Assistant) to an existing thread.
        """
        if not thread_id:
            return
        self.logs.update_one(
            {"_id": ObjectId(thread_id)},
            {"$push": {"messages": {"role": role, "content": content, "timestamp": datetime.now()}}},
        )

    def delete_thread(self, thread_id: str):
        """Permanently deletes a conversation thread."""
        if not thread_id:
            return
        self.logs.delete_one({"_id": ObjectId(thread_id)})

    def update_thread_title(self, thread_id: str, new_title: str):
        """Renames a conversation thread (e.g., based on the first user query)."""
        if not thread_id:
            return
        try:
            self.logs.update_one({"_id": ObjectId(thread_id)}, {"$set": {"title": new_title}})
        except Exception:
            return

    # --- Profile & CV Management ---

    def update_profile(self, username: str, profile_data: dict):
        """
        Updates the user's demographic/CV data.
        
        CRITICAL: This method explicitly $unsets (deletes) the cached 'profile.summary'.
        This forces the AI to regenerate the 'User Persona' on the next chat interaction,
        ensuring the AI always acts on the most up-to-date data.
        """
        try:
            # Flatten the dictionary to dot notation for MongoDB updates (e.g., "profile.budget")
            update_fields = {f"profile.{key}": value for key, value in profile_data.items()}

            self.users.update_one(
                {"username": username},
                {
                    "$set": update_fields,
                    "$unset": {"profile.summary": ""} # Invalidate cache
                }
            )
            return True, "Profile updated successfully!"
        except Exception as e:
            return False, str(e)

    def save_profile_summary(self, username: str, summary: str):
        """
        Saves the AI-generated 'User Persona' summary to the database.
        This acts as a cache so we don't need to re-run the summarization LLM every turn.
        """
        try:
            self.users.update_one(
                {"username": username},
                {"$set": {"profile.summary": summary}}
            )
        except Exception as e:
            print(f"Error saving summary: {e}")

    def get_profile(self, username: str) -> dict:
        """Retrieves the full user profile dictionary (budget, gpa, CV text, summary)."""
        user = self.users.find_one({"username": username})
        return user.get("profile", {}) if user else {}