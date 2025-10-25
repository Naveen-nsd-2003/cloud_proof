from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from .user_model import db  # Reuse your existing MongoDB connection

profiles_collection = db["profiles"]

def create_or_update_profile(user_id, name, bio, photo_url):
    profile_data = {
        "user_id": ObjectId(user_id),
        "name": name,
        "bio": bio,
        "photo_url": photo_url,
        "updated_at": datetime.utcnow()
    }
    profiles_collection.update_one(
        {"user_id": ObjectId(user_id)},
        {"$set": profile_data},
        upsert=True
    )
    return profile_data

def get_profile(user_id):
    profile = profiles_collection.find_one({"user_id": ObjectId(user_id)})
    if profile:
        profile["_id"] = str(profile["_id"])
        profile["user_id"] = str(profile["user_id"])
    return profile
