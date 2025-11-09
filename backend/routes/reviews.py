from flask import Blueprint, request, jsonify
from models.review_model import reviews_collection
from models.order_model import orders_collection
from models.user_model import users_collection
from models.gig_model import gigs_collection
from bson import ObjectId
from datetime import datetime
import jwt
import os
from functools import wraps

reviews_bp = Blueprint("reviews", __name__)

# JWT token verification decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        
        try:
            token = token.split(" ")[1] if " " in token else token
            data = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
            current_user = users_collection.find_one({"_id": ObjectId(data["user_id"])})
            if not current_user:
                return jsonify({"error": "User not found"}), 401
        except Exception as e:
            return jsonify({"error": "Invalid token"}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated


# Helper function to calculate and update freelancer rating
def calculate_freelancer_rating(freelancer_id):
    """Calculate average rating and breakdown for a freelancer"""
    try:
        print(f"🔄 Calculating rating for freelancer: {freelancer_id}")  # DEBUG
        
        # Ensure freelancer_id is a string (handle ObjectId if passed)
        freelancer_id_str = str(freelancer_id)
        
        # Get all reviews for this freelancer
        reviews = list(reviews_collection.find({"freelancer_id": freelancer_id_str}))
        
        print(f"📊 Found {len(reviews)} reviews for freelancer {freelancer_id_str}")  # DEBUG
        
        if not reviews:
            # No reviews yet - set defaults
            print(f"⚠️ No reviews found, setting defaults")  # DEBUG
            result = users_collection.update_one(
                {"_id": ObjectId(freelancer_id_str)},
                {"$set": {
                    "average_rating": 0,
                    "total_reviews": 0,
                    "rating_breakdown": {
                        "5_star": 0,
                        "4_star": 0,
                        "3_star": 0,
                        "2_star": 0,
                        "1_star": 0
                    }
                }}
            )
            print(f"✅ Default rating set. Matched: {result.matched_count}, Modified: {result.modified_count}")  # DEBUG
            return True
        
        # Calculate average
        total_rating = sum(review["rating"] for review in reviews)
        average_rating = round(total_rating / len(reviews), 1)
        
        # Calculate breakdown
        breakdown = {
            "5_star": sum(1 for r in reviews if r["rating"] == 5),
            "4_star": sum(1 for r in reviews if r["rating"] == 4),
            "3_star": sum(1 for r in reviews if r["rating"] == 3),
            "2_star": sum(1 for r in reviews if r["rating"] == 2),
            "1_star": sum(1 for r in reviews if r["rating"] == 1)
        }
        
        print(f"📈 Calculated average: {average_rating}, Total: {len(reviews)}")  # DEBUG
        print(f"📊 Breakdown: {breakdown}")  # DEBUG
        
        # Update user document
        result = users_collection.update_one(
            {"_id": ObjectId(freelancer_id_str)},
            {"$set": {
                "average_rating": average_rating,
                "total_reviews": len(reviews),
                "rating_breakdown": breakdown,
                "updated_at": datetime.utcnow()
            }}
        )
        
        print(f"✅ Rating updated! Matched: {result.matched_count}, Modified: {result.modified_count}")  # DEBUG
        
        if result.matched_count == 0:
            print(f"❌ ERROR: User not found with _id: {freelancer_id_str}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error calculating rating: {str(e)}")  # DEBUG
        import traceback
        traceback.print_exc()
        return False


# CREATE REVIEW
@reviews_bp.route("/create", methods=["POST"])
@token_required
def create_review(current_user):
    """Create a new review (client only, after order completion)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get("order_id") or not data.get("rating"):
            return jsonify({"error": "Order ID and rating are required"}), 400
        
        # Validate rating (1-5)
        rating = int(data.get("rating"))
        if rating < 1 or rating > 5:
            return jsonify({"error": "Rating must be between 1 and 5"}), 400
        
        # Get order details
        order = orders_collection.find_one({"_id": ObjectId(data["order_id"])})
        if not order:
            return jsonify({"error": "Order not found"}), 404
        
        print(f"📦 Order found: {order}")  # DEBUG
        
        # Verify current user is the client of this order
        if str(order["client_id"]) != str(current_user["_id"]):
            return jsonify({"error": "You can only review your own orders"}), 403
        
        # Verify order is completed
        if order["status"] != "completed":
            return jsonify({"error": "Can only review completed orders"}), 400
        
        # Check if review already exists for this order
        existing_review = reviews_collection.find_one({"order_id": data["order_id"]})
        if existing_review:
            return jsonify({"error": "You have already reviewed this order"}), 400
        
        # Get gig details for context
        gig = gigs_collection.find_one({"_id": ObjectId(order["gig_id"])})
        gig_title = gig["title"] if gig else "Unknown Gig"
        
        # Get freelancer_id (ensure it's a string)
        freelancer_id = str(order["freelancer_id"])
        
        print(f"👤 Freelancer ID from order: {freelancer_id}")  # DEBUG
        
        # Create review document
        review = {
            "order_id": data["order_id"],
            "gig_id": order["gig_id"],
            "gig_title": gig_title,
            "freelancer_id": freelancer_id,  # Store as string
            "client_id": str(current_user["_id"]),
            "rating": rating,
            "review_text": data.get("review_text", "").strip(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert review
        result = reviews_collection.insert_one(review)
        print(f"✅ Review created with ID: {result.inserted_id}")  # DEBUG
        
        # Calculate and update freelancer's rating
        rating_updated = calculate_freelancer_rating(freelancer_id)
        
        if not rating_updated:
            print(f"⚠️ Warning: Rating calculation failed, but review was saved")
        
        # Return created review
        review["_id"] = str(result.inserted_id)
        review["created_at"] = review["created_at"].isoformat()
        review["updated_at"] = review["updated_at"].isoformat()
        
        return jsonify({
            "message": "Review created successfully",
            "review": review
        }), 201
        
    except Exception as e:
        print(f"❌ Error creating review: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to create review"}), 500


# GET FREELANCER REVIEWS
@reviews_bp.route("/freelancer/<freelancer_id>", methods=["GET"])
def get_freelancer_reviews(freelancer_id):
    """Get all reviews for a freelancer"""
    try:
        # Convert to string
        freelancer_id_str = str(freelancer_id)
        
        print(f"🔍 Fetching reviews for freelancer: {freelancer_id_str}")  # DEBUG
        
        # Verify freelancer exists
        try:
            freelancer = users_collection.find_one({"_id": ObjectId(freelancer_id_str)})
        except:
            return jsonify({"error": "Invalid freelancer ID"}), 400
        
        if not freelancer:
            return jsonify({"error": "Freelancer not found"}), 404
        
        # Get all reviews
        reviews = list(reviews_collection.find({"freelancer_id": freelancer_id_str}).sort("created_at", -1))
        
        print(f"📊 Found {len(reviews)} reviews")  # DEBUG
        
        # Format reviews
        formatted_reviews = []
        for review in reviews:
            # Get client info
            try:
                client = users_collection.find_one({"_id": ObjectId(review["client_id"])})
            except:
                client = None
            
            formatted_reviews.append({
                "_id": str(review["_id"]),
                "order_id": review["order_id"],
                "gig_title": review.get("gig_title", "Unknown Gig"),
                "rating": review["rating"],
                "review_text": review.get("review_text", ""),
                "client_name": client["name"] if client else "Anonymous",
                "created_at": review["created_at"].isoformat(),
                "updated_at": review["updated_at"].isoformat()
            })
        
        return jsonify({
            "success": True,
            "reviews": formatted_reviews,
            "total": len(formatted_reviews)
        }), 200
        
    except Exception as e:
        print(f"❌ Error getting reviews: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Failed to get reviews"}), 500


# GET ORDER REVIEW STATUS
@reviews_bp.route("/order/<order_id>", methods=["GET"])
@token_required
def get_order_review(current_user, order_id):
    """Check if an order has been reviewed"""
    try:
        # Check if review exists
        review = reviews_collection.find_one({"order_id": order_id})
        
        if not review:
            return jsonify({
                "success": True,
                "has_review": False,
                "review": None
            }), 200
        
        # Get client info
        try:
            client = users_collection.find_one({"_id": ObjectId(review["client_id"])})
        except:
            client = None
        
        formatted_review = {
            "_id": str(review["_id"]),
            "order_id": review["order_id"],
            "gig_title": review.get("gig_title", "Unknown Gig"),
            "rating": review["rating"],
            "review_text": review.get("review_text", ""),
            "client_name": client["name"] if client else "Anonymous",
            "created_at": review["created_at"].isoformat(),
            "updated_at": review["updated_at"].isoformat()
        }
        
        return jsonify({
            "success": True,
            "has_review": True,
            "review": formatted_review
        }), 200
        
    except Exception as e:
        print(f"❌ Error checking review: {str(e)}")
        return jsonify({"error": "Failed to check review"}), 500


# UPDATE REVIEW
@reviews_bp.route("/<review_id>", methods=["PUT"])
@token_required
def update_review(current_user, review_id):
    """Update an existing review"""
    try:
        data = request.get_json()
        
        # Get existing review
        review = reviews_collection.find_one({"_id": ObjectId(review_id)})
        if not review:
            return jsonify({"error": "Review not found"}), 404
        
        # Verify current user is the author
        if str(review["client_id"]) != str(current_user["_id"]):
            return jsonify({"error": "You can only edit your own reviews"}), 403
        
        # Prepare update data
        update_data = {"updated_at": datetime.utcnow()}
        
        if "rating" in data:
            rating = int(data["rating"])
            if rating < 1 or rating > 5:
                return jsonify({"error": "Rating must be between 1 and 5"}), 400
            update_data["rating"] = rating
        
        if "review_text" in data:
            update_data["review_text"] = data["review_text"].strip()
        
        # Update review
        reviews_collection.update_one(
            {"_id": ObjectId(review_id)},
            {"$set": update_data}
        )
        
        # Recalculate freelancer rating if rating changed
        if "rating" in update_data:
            calculate_freelancer_rating(review["freelancer_id"])
        
        # Get updated review
        updated_review = reviews_collection.find_one({"_id": ObjectId(review_id)})
        
        return jsonify({
            "message": "Review updated successfully",
            "review": {
                "_id": str(updated_review["_id"]),
                "rating": updated_review["rating"],
                "review_text": updated_review.get("review_text", ""),
                "updated_at": updated_review["updated_at"].isoformat()
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Error updating review: {str(e)}")
        return jsonify({"error": "Failed to update review"}), 500