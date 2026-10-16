from database import DatabaseManager

try:
    db = DatabaseManager()
    print("✅ Successfully connected to Supabase!")
except Exception as e:
    print(f"❌ Connection failed: {e}")