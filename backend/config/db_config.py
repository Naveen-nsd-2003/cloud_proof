from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Read URI from .env
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI not found in .env. Please set it before running.")

# Connect to MongoDB
client = MongoClient(MONGODB_URI)

# Use a database (name: cloudcred)
db = client["cloudcred"]

print("✅ Connected to MongoDB successfully.")
