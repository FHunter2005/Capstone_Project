# services/auth_service.py
import bcrypt
from datetime import datetime
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
            'created_at': datetime.now()
        })
        return True, "Account created successfully!"

    def login_user(self, username, password):
        user = self.users.find_one({'username': username})
        if user and self.verify_password(password, user['password']):
            return user
        return None

    # --- Gestão de Histórico ---
    
    def save_message(self, username, role, content):
        """Saves a single message in the user's history"""
        self.logs.update_one(
            {"username": username},
            {
                "$push": {"messages": {"role": role, "content": content, "timestamp": datetime.now()}},
                "$setOnInsert": {"created_at": datetime.now()} 
            },
            upsert=True
        )

    def load_history(self, username):
        """Carrega mensagens anteriores"""
        log = self.logs.find_one({"username": username})
        if log and "messages" in log:
            # Returns only the role and content for Streamlit format
            return [{"role": m["role"], "content": m["content"]} for m in log["messages"]]
        return []