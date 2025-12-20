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

    def hash_password(self, password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def verify_password(self, password, hashed):
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def register_user(self, username, name, password):
        if self.users.find_one({'username': username}):
            return False, "Username already exists."
        
        self.users.insert_one({
            'username': username,
            'name': name,
            'password': self.hash_password(password),
            'created_at': datetime.now(),
            'favorites': []
        })
        return True, "Account created successfully!"

    def login_user(self, username, password):
        user = self.users.find_one({'username': username})
        if user and self.verify_password(password, user['password']):
            return user
        return None

    def save_message(self, username, role, content):
        self.logs.update_one(
            {"username": username},
            {
                "$push": {"messages": {"role": role, "content": content, "timestamp": datetime.now()}},
                "$setOnInsert": {"created_at": datetime.now()} 
            },
            upsert=True
        )

    def load_history(self, username):
        log = self.logs.find_one({"username": username})
        if log and "messages" in log:
            return [{"role": m["role"], "content": m["content"]} for m in log["messages"]]
        return []

    def add_favorite(self, username, master_data):
        """Adds a program to the user's 'favorites' array."""
        
        fav_item = {
            "master": master_data.get("master"),
            "university": master_data.get("university"),
            "location": master_data.get("Location"),
            "tuition": master_data.get("Tuition Fee"),
            "saved_at": datetime.now()
        }

        result = self.users.update_one(
            {"username": username},
            {"$addToSet": {"favorites": fav_item}}
        )

        if result.modified_count > 0:
            return True, "Saved to favorites!"
        else:
            return False, "Already in favorites!"

    def get_user_favorites(self, username):
        """Returns the favorites list from the user document."""
        user = self.users.find_one({"username": username}, {"favorites": 1})
        if user and "favorites" in user:
            return user["favorites"]
        return []

    def remove_favorite(self, username, master_name):
        """Removes an item from the array where 'master' matches the name."""
        self.users.update_one(
            {"username": username},
            {"$pull": {"favorites": {"master": master_name}}}
        )

    def create_new_thread(self, username, title="New Chat"):
        """Creates a new conversation document and returns its ID."""
        new_thread = {
            "username": username,
            "title": title,
            "created_at": datetime.now(),
            "messages": []
        }
        result = self.logs.insert_one(new_thread)
        # Return the ID as a string so Streamlit can use it easily
        return str(result.inserted_id)
    
    def get_user_threads(self, username):
        """Returns a list of all conversation threads for the user, newest first."""
        cursor = self.logs.find({"username": username}).sort("created_at", -1)
        
        threads = []
        for doc in cursor:
            threads.append({
                "id": str(doc["_id"]),
                "title": doc.get("title", "Untitled Chat"),
                "date": doc["created_at"].strftime("%Y-%m-%d %H:%M")
            })
        return threads
    
    def load_thread_messages(self, thread_id):
        """Loads messages for a specific conversation ID."""
        if not thread_id:
            return []
        try:
            # This requires 'from bson.objectid import ObjectId' at the top
            doc = self.logs.find_one({"_id": ObjectId(thread_id)})
            if doc and "messages" in doc:
                return [{"role": m["role"], "content": m["content"]} for m in doc["messages"]]
        except Exception as e:
            print(f"Error loading thread: {e}")
        return []

    def save_message(self, thread_id, role, content):
        """Saves a message to a SPECIFIC conversation."""
        if not thread_id:
            return
            
        self.logs.update_one(
            {"_id": ObjectId(thread_id)},
            {
                "$push": {"messages": {"role": role, "content": content, "timestamp": datetime.now()}},
                # Optional: Update title based on first message if needed
            }
        )

    def delete_thread(self, thread_id):
        """Deletes a specific conversation."""
        self.logs.delete_one({"_id": ObjectId(thread_id)})

    def update_thread_title(self, thread_id, new_title):
        """Renames the chat thread."""
        try:
            self.logs.update_one({"_id": ObjectId(thread_id)}, {"$set": {"title": new_title}})
        except:
            pass
    