import os
from dotenv import load_dotenv
from mongoengine import connect
from constants import MONGODB_URI

load_dotenv()

# MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_URI = MONGODB_URI
DB_NAME = "main"

if not MONGODB_URI:
    raise ValueError("MONGODB_URI not set in .env")

connect(db=DB_NAME, host=MONGODB_URI)
print("✅ MongoDB connected successfully!")
