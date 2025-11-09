from flask import Blueprint, request, jsonify
from models.user_model import users_collection
from utils.validators import validate_email, validate_password
import bcrypt, jwt, os
from datetime import datetime, timedelta

import json
from bson import ObjectId
from datetime import datetime

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle ObjectId and datetime objects"""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

users_bp = Blueprint("users", __name__)
JWT_SECRET = os.getenv("JWT_SECRET", "secret")

@users_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    name, email, password, role = data.get("name"), data.get("email"), data.get("password"), data.get("role")
    
    if not validate_email(email):
        return jsonify({"error": "Invalid email"}), 400
    if not validate_password(password):
        return jsonify({"error": "Password too short"}), 400

    if users_collection.find_one({"email": email}):
        return jsonify({"error": "Email already exists"}), 400

    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    users_collection.insert_one({
        "name": name,
        "email": email,
        "password": hashed_pw,
        "role": role,
        "created_at": datetime.utcnow(),
        "is_active": True,
        "average_rating": 0,  # NEW
        "total_reviews": 0,   # NEW
        "rating_breakdown": { # NEW
            "5_star": 0,
            "4_star": 0,
            "3_star": 0,
            "2_star": 0,
            "1_star": 0
        }
    })

    return jsonify({"message": "User registered successfully ✅"}), 201


@users_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email, password = data.get("email"), data.get("password")
    user = users_collection.find_one({"email": email})

    if not user or not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = jwt.encode(
        {"user_id": str(user["_id"]), "exp": datetime.utcnow() + timedelta(hours=2)},
        JWT_SECRET,
        algorithm="HS256"
    )
    return jsonify({
        "token": token, 
        "user": {
            "id": str(user["_id"]),
            "name": user["name"], 
            "role": user["role"],
            "average_rating": user.get("average_rating", 0),  # NEW
            "total_reviews": user.get("total_reviews", 0)      # NEW
        }
    })

@users_bp.route("/", methods=["GET"])
def list_users():
    """List all users (basic info only)"""
    try:
        # Get query parameters for filtering
        role = request.args.get("role")
        limit = min(int(request.args.get("limit", 50)), 100)  # Max 100 users
        
        # Build query
        query = {}
        if role and role in ["freelancer", "client"]:
            query["role"] = role
        
        # Get users (exclude passwords, include ratings)
        users = list(users_collection.find(
            query,
            {"password": 0}  # Exclude password field
        ).limit(limit))
        
        # Add default rating fields if missing
        for user in users:
            user.setdefault("average_rating", 0)
            user.setdefault("total_reviews", 0)
            user.setdefault("rating_breakdown", {
                "5_star": 0,
                "4_star": 0,
                "3_star": 0,
                "2_star": 0,
                "1_star": 0
            })
        
        return json.dumps({"users": users}, cls=CustomJSONEncoder)
        
    except ValueError:
        return jsonify({"error": "Invalid limit parameter"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to list users: {str(e)}"}), 500