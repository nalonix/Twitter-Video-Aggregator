from mongoengine import connect

from core.constants import MONGODB_URI

DB_NAME = "main"

if not MONGODB_URI:
    raise ValueError("MONGODB_URI not set in core/constants.py")

connect(db=DB_NAME, host=MONGODB_URI)
print("✅ MongoDB connected successfully!")
