
from flask import Blueprint, request, jsonify
from config.db_config import db
from bson import ObjectId
from models.user_model import users_collection
import jwt
import os
from functools import wraps
from datetime import datetime
import json

# Blueprint for gigs routes
gigs_bp = Blueprint("gigs", __name__)

JWT_SECRET = os.getenv("JWT_SECRET", "secret")


class CustomJSONEncoder(json.JSONEncoder):
    # Custom JSON encoder to handle ObjectId and datetime objects
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def token_required(f):
    # Decorator to require JWT authentication
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            # Decode the token
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])

            # Get user info from database using user_id from token
            user = users_collection.find_one({"_id": ObjectId(payload['user_id'])})
            if not user:
                return jsonify({'error': 'User not found'}), 401

            current_user = {
                'user_id': payload['user_id'],
                'email': user['email'],
                'role': user['role']
            }

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'error': f'Authentication error: {str(e)}'}), 401

        return f(current_user, *args, **kwargs)

    return decorated_function


# GET all gigs
@gigs_bp.route("/", methods=["GET"])
def get_gigs():
    # Get all gigs with optional filtering
    try:
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        search = request.args.get('search', '')
        created_by = request.args.get('created_by', '')
        limit = min(int(request.args.get('limit', 50)), 100)

        query_filter = {}

        if min_price is not None or max_price is not None:
            price_filter = {}
            if min_price is not None:
                price_filter['$gte'] = min_price
            if max_price is not None:
                price_filter['$lte'] = max_price
            query_filter['price'] = price_filter

        if search:
            query_filter['$or'] = [
                {'title': {'$regex': search, '$options': 'i'}},
                {'description': {'$regex': search, '$options': 'i'}}
            ]

        if created_by:
            query_filter['created_by'] = created_by

        gigs_cursor = db.gigs.find(query_filter).limit(limit).sort('created_at', -1)
        gigs = list(gigs_cursor)

        return json.dumps({"gigs": gigs, "count": len(gigs)}, cls=CustomJSONEncoder)

    except ValueError as e:
        return jsonify({"error": f"Invalid query parameters: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to fetch gigs: {str(e)}"}), 500


# POST create a new gig (Freelancer only)
@gigs_bp.route("/", methods=["POST"])
@token_required
def create_gig(current_user):
    try:
        if current_user.get('role') != 'freelancer':
            return jsonify({"error": "Only freelancers can create gigs"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ['title', 'description', 'price']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        try:
            price = float(data['price'])
            if price <= 0:
                return jsonify({"error": "Price must be greater than 0"}), 400
            if price > 1000000:
                return jsonify({"error": "Price cannot exceed $1,000,000"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Price must be a valid number"}), 400

        title = data['title'].strip()
        description = data['description'].strip()

        if len(title) < 5 or len(title) > 100:
            return jsonify({"error": "Title must be between 5 and 100 characters"}), 400

        if len(description) < 20 or len(description) > 1000:
            return jsonify({"error": "Description must be between 20 and 1000 characters"}), 400

        gig = {
            "title": title,
            "description": description,
            "price": price,
            "created_by": current_user["email"],
            "freelancer_id": current_user["user_id"],
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "tags": data.get("tags", []),
            "delivery_time": data.get("delivery_time", "7 days"),
            "category": data.get("category", "General")
        }

        result = db.gigs.insert_one(gig)
        gig["_id"] = str(result.inserted_id)

        return json.dumps({"message": "Gig created successfully ✅", "gig": gig}, cls=CustomJSONEncoder), 201

    except Exception as e:
        return jsonify({"error": f"Failed to create gig: {str(e)}"}), 500


# GET a specific gig by ID
@gigs_bp.route("/<gig_id>", methods=["GET"])
def get_gig(gig_id):
    try:
        try:
            object_id = ObjectId(gig_id)
        except Exception:
            return jsonify({"error": "Invalid gig ID format"}), 400

        gig = db.gigs.find_one({"_id": object_id})
        if not gig:
            return jsonify({"error": "Gig not found"}), 404

        return json.dumps({"gig": gig}, cls=CustomJSONEncoder)

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve gig: {str(e)}"}), 500


# PUT update a gig (Owner only)
@gigs_bp.route("/<gig_id>", methods=["PUT"])
@token_required
def update_gig(current_user, gig_id):
    try:
        try:
            object_id = ObjectId(gig_id)
        except Exception:
            return jsonify({"error": "Invalid gig ID format"}), 400

        gig = db.gigs.find_one({"_id": object_id})
        if not gig:
            return jsonify({"error": "Gig not found"}), 404

        if gig['created_by'] != current_user['email']:
            return jsonify({"error": "You can only update your own gigs"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        update_data = {"updated_at": datetime.utcnow()}

        allowed_fields = ['title', 'description', 'price', 'status', 'tags', 'delivery_time', 'category']
        for field in allowed_fields:
            if field in data:
                if field == 'price':
                    try:
                        price = float(data[field])
                        if price <= 0:
                            return jsonify({"error": "Price must be greater than 0"}), 400
                        update_data[field] = price
                    except (ValueError, TypeError):
                        return jsonify({"error": "Price must be a valid number"}), 400
                elif field == 'status' and data[field] not in ['active', 'inactive', 'completed']:
                    return jsonify({"error": "Status must be active, inactive, or completed"}), 400
                else:
                    update_data[field] = data[field]

        db.gigs.update_one({"_id": object_id}, {"$set": update_data})
        updated_gig = db.gigs.find_one({"_id": object_id})

        return json.dumps({"message": "Gig updated successfully ✅", "gig": updated_gig}, cls=CustomJSONEncoder)

    except Exception as e:
        return jsonify({"error": f"Failed to update gig: {str(e)}"}), 500


# DELETE a gig (Owner only)
@gigs_bp.route("/<gig_id>", methods=["DELETE"])
@token_required
def delete_gig(current_user, gig_id):
    try:
        try:
            object_id = ObjectId(gig_id)
        except Exception:
            return jsonify({"error": "Invalid gig ID format"}), 400

        gig = db.gigs.find_one({"_id": object_id})
        if not gig:
            return jsonify({"error": "Gig not found"}), 404

        if gig['created_by'] != current_user['email']:
            return jsonify({"error": "You can only delete your own gigs"}), 403

        db.gigs.delete_one({"_id": object_id})

        return jsonify({"message": "Gig deleted successfully ✅"})

    except Exception as e:
        return jsonify({"error": f"Failed to delete gig: {str(e)}"}), 500
