from services.db_service import DatabaseService
db = DatabaseService()

doc = db.masters().find_one()
print(doc.keys())
