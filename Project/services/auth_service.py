# services/auth_service.py
import bcrypt
from datetime import datetime
from bson.objectid import ObjectId
from services.db_service import DatabaseService


class AuthService:
    def __init__(self):
        self.db = DatabaseService()
        self.users = self.db.users()
        self.logs = self.db.chat_logs()

    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def register_user(self, username: str, name: str, password: str):
        if self.users.find_one({"username": username}):
            return False, "Username already exists."

        self.users.insert_one(
            {
                "username": username,
                "name": name,
                "password": self.hash_password(password),
                "created_at": datetime.now(),
                "favorites": [],
            }
        )
        return True, "Account created successfully!"

    def login_user(self, username: str, password: str):
        user = self.users.find_one({"username": username})
        if user and self.verify_password(password, user["password"]):
            return user
        return None

    def add_favorite(self, username: str, master_data: dict):
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

        fav_item = {
            "master": master_data.get("master"),
            "university": master_data.get("university"),
            "location": master_data.get("Location"),
            "tuition": master_data.get("Tuition Fee"),
            "about": master_data.get("about"),
            "saved_at": datetime.now(),
        }

        self.users.update_one(
            {"username": username},
            {"$push": {"favorites": fav_item}},
        )

        return True, "Saved to favorites!"

    def get_user_favorites(self, username: str):
        user = self.users.find_one({"username": username}, {"favorites": 1})
        if user and "favorites" in user:
            return user["favorites"]
        return []

    def remove_favorite(self, username: str, master_name: str, university_name: str):
        self.users.update_one(
            {"username": username},
            {"$pull": {"favorites": {"master": master_name, "university": university_name}}}
        )

    def create_new_thread(self, username: str, title: str = "New Chat") -> str:
        new_thread = {
            "username": username,
            "title": title,
            "created_at": datetime.now(),
            "messages": [],
        }
        result = self.logs.insert_one(new_thread)
        return str(result.inserted_id)

    def get_user_threads(self, username: str):
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
        if not thread_id:
            return []
        try:
            doc = self.logs.find_one({"_id": ObjectId(thread_id)})
            if doc and "messages" in doc:
                return [{"role": m["role"], "content": m["content"]} for m in doc["messages"]]
        except Exception:
            return []
        return []

    def save_message(self, thread_id: str, role: str, content: str):
        if not thread_id:
            return
        self.logs.update_one(
            {"_id": ObjectId(thread_id)},
            {"$push": {"messages": {"role": role, "content": content, "timestamp": datetime.now()}}},
        )

    def delete_thread(self, thread_id: str):
        if not thread_id:
            return
        self.logs.delete_one({"_id": ObjectId(thread_id)})

    def update_thread_title(self, thread_id: str, new_title: str):
        if not thread_id:
            return
        try:
            self.logs.update_one({"_id": ObjectId(thread_id)}, {"$set": {"title": new_title}})
        except Exception:
            return


    def update_profile(self, username: str, profile_data: dict):
        """Saves the user's background/CV."""
        try:
            self.users.update_one(
                {"username": username},
                {"$set": {"profile": profile_data}}
            )
            return True, "Profile updated successfully!"
        except Exception as e:
            return False, str(e)

    def get_profile(self, username: str) -> dict:
        """Gets the user's background/CV."""
        user = self.users.find_one({"username": username})
        return user.get("profile", {}) if user else {}