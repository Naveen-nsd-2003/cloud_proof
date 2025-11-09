from flask import Blueprint, request, jsonify
from models.user_model import users_collection
from services.aws_service import upload_invoice_to_s3 
from services.aws_service import upload_profile_photo_to_s3 # Reuse for photo upload
from bson import ObjectId
from datetime import datetime
import jwt
import os
import json

profile_bp = Blueprint("profile_bp", __name__)
JWT_SECRET = os.getenv("JWT_SECRET", "secret")

class CustomJSONEncoder(json.JSONEncoder):
    """Handle ObjectId and datetime serialization"""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def get_user_from_token():
    """Extract user from JWT token"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("user_id")
    except:
        return None

@profile_bp.route("/", methods=["GET"])
def get_profile():
    """Get current user's profile"""
    try:
        user_id = get_user_from_token()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Return profile data (exclude password)
        profile_data = {
            "id": str(user["_id"]),
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "role": user.get("role", ""),
            "bio": user.get("bio", ""),
            "profileImage": user.get("profileImage", ""),
            # ← ADD RATING FIELDS
            "average_rating": user.get("average_rating", 0),
            "total_reviews": user.get("total_reviews", 0),
            "rating_breakdown": user.get("rating_breakdown", {
                "5_star": 0,
                "4_star": 0,
                "3_star": 0,
                "2_star": 0,
                "1_star": 0
            }),
            "created_at": user.get("created_at"),
            "updated_at": user.get("updated_at")
        }
        
        return json.dumps({
            "success": True,
            "data": profile_data
        }, cls=CustomJSONEncoder), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch profile: {str(e)}"}), 500

@profile_bp.route("/update", methods=["POST"])
def update_profile():
    """Update current user's profile"""
    try:
        user_id = get_user_from_token()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Build update data
        update_data = {"updated_at": datetime.utcnow()}
        
        # Update allowed fields
        if "name" in data and data["name"].strip():
            update_data["name"] = data["name"].strip()
        
        if "bio" in data:
            update_data["bio"] = data["bio"].strip()[:500]  # Max 500 chars
        
        if "profileImage" in data:
            update_data["profileImage"] = data["profileImage"].strip()
        
        # Update in database
        result = users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0 and result.matched_count == 0:
            return jsonify({"error": "User not found"}), 404
        
        # Get updated user data
        updated_user = users_collection.find_one({"_id": ObjectId(user_id)})
        
        profile_data = {
            "id": str(updated_user["_id"]),
            "name": updated_user.get("name", ""),
            "email": updated_user.get("email", ""),
            "role": updated_user.get("role", ""),
            "bio": updated_user.get("bio", ""),
            "profileImage": updated_user.get("profileImage", ""),
            # ← ADD RATING FIELDS
            "average_rating": updated_user.get("average_rating", 0),
            "total_reviews": updated_user.get("total_reviews", 0),
            "rating_breakdown": updated_user.get("rating_breakdown", {
                "5_star": 0,
                "4_star": 0,
                "3_star": 0,
                "2_star": 0,
                "1_star": 0
            }),
            "updated_at": updated_user.get("updated_at")
        }
        
        return json.dumps({
            "success": True,
            "message": "Profile updated successfully ✅",
            "data": profile_data
        }, cls=CustomJSONEncoder), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to update profile: {str(e)}"}), 500

@profile_bp.route("/upload-photo", methods=["POST"])
def upload_photo():
    """Upload profile photo to S3"""
    try:
        user_id = get_user_from_token()
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401
        
        if 'photo' not in request.files:
            return jsonify({"error": "No photo file provided"}), 400
        
        file = request.files['photo']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Check file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        
        if file_ext not in allowed_extensions:
            return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, gif, webp"}), 400
        
        # Read file content
        file_content = file.read()
        
        # Upload to S3 using dedicated profile photo function
        from services.aws_service import upload_profile_photo_to_s3
        photo_url = upload_profile_photo_to_s3(file_content, f"profile_{user_id}.{file_ext}")
        
        # Update user profile with photo URL
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"profileImage": photo_url, "updated_at": datetime.utcnow()}}
        )
        
        return jsonify({
            "success": True,
            "message": "Photo uploaded successfully ✅",
            "photoUrl": photo_url
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Photo upload failed: {str(e)}"}), 500

@profile_bp.route("/<user_id>", methods=["GET"])
def get_user_profile(user_id):
    """Get any user's public profile (for displaying names/photos in app)"""
    try:
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Return only public information
        public_profile = {
            "id": str(user["_id"]),
            "name": user.get("name", "Unknown User"),
            "role": user.get("role", ""),
            "bio": user.get("bio", ""),
            "profileImage": user.get("profileImage", ""),
            # ← ADD RATING FIELDS (for displaying on gigs/profile cards)
            "average_rating": user.get("average_rating", 0),
            "total_reviews": user.get("total_reviews", 0),
            "rating_breakdown": user.get("rating_breakdown", {
                "5_star": 0,
                "4_star": 0,
                "3_star": 0,
                "2_star": 0,
                "1_star": 0
            })
        }
        
        return jsonify({
            "success": True,
            "data": public_profile
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch profile: {str(e)}"}), 500