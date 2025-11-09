from flask import Blueprint, request, jsonify
from models.order_model import orders_collection
from models.gig_model import gigs_collection
from models.user_model import users_collection
from bson import ObjectId
from datetime import datetime, timedelta
import json

orders_bp = Blueprint("orders", __name__)

# JSON Encoder for MongoDB ObjectId
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# ✅ Create Order (Client orders a gig - payment locked)
@orders_bp.route("/create", methods=["POST"])
def create_order():
    try:
        data = request.json
        
        # Validate required fields
        required = ["gig_id", "client_id"]
        for field in required:
            if not data.get(field):
                return jsonify({"error": f"Missing field: {field}"}), 400
        
        # Get gig details
        gig = gigs_collection.find_one({"_id": ObjectId(data["gig_id"])})
        if not gig:
            return jsonify({"error": "Gig not found"}), 404
        
        # Create order
        order = {
            "gig_id": data["gig_id"],
            "gig_title": gig.get("title"),
            "gig_price": gig.get("price"),
            "freelancer_id": gig.get("freelancer_id"),  # ← FIXED! Now gets USER_ID instead of email ✅
            "client_id": data["client_id"],
            "amount": gig.get("price"),
            "status": "in_progress",  # Payment assumed locked
            "payment_status": "locked",  # Money secured
            "description": data.get("description", gig.get("description")),
            "delivery_date": datetime.utcnow() + timedelta(days=7),  # Default 7 days
            "created_at": datetime.utcnow(),
            "delivered_at": None,
            "completed_at": None,
            "notes": data.get("notes", "")
        }
        
        result = orders_collection.insert_one(order)
        order["_id"] = str(result.inserted_id)
        
        return json.dumps({
            "success": True,
            "message": "Order created successfully! Payment secured.",
            "order": order
        }, cls=CustomJSONEncoder), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Get All Orders (for a specific user)
@orders_bp.route("/user/<user_id>", methods=["GET"])
def get_user_orders(user_id):
    try:
        # Get orders where user is either freelancer or client
        orders = list(orders_collection.find({
            "$or": [
                {"freelancer_id": user_id},
                {"client_id": user_id}
            ]
        }).sort("created_at", -1))
        
        return json.dumps({
            "success": True,
            "orders": orders
        }, cls=CustomJSONEncoder), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Get Single Order Details
@orders_bp.route("/<order_id>", methods=["GET"])
def get_order(order_id):
    try:
        order = orders_collection.find_one({"_id": ObjectId(order_id)})
        
        if not order:
            return jsonify({"error": "Order not found"}), 404
        
        # Get user details for display
        freelancer = users_collection.find_one({"_id": ObjectId(order["freelancer_id"])})
        client = users_collection.find_one({"_id": ObjectId(order["client_id"])})
        
        order["freelancer_name"] = freelancer.get("name") if freelancer else "Unknown"
        order["client_name"] = client.get("name") if client else "Unknown"
        
        return json.dumps({
            "success": True,
            "order": order
        }, cls=CustomJSONEncoder), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Mark Order as Delivered (Freelancer action)
@orders_bp.route("/<order_id>/deliver", methods=["POST"])
def deliver_order(order_id):
    try:
        data = request.json
        freelancer_id = data.get("freelancer_id")
        
        order = orders_collection.find_one({"_id": ObjectId(order_id)})
        if not order:
            return jsonify({"error": "Order not found"}), 404
        
        # Verify freelancer
        if order["freelancer_id"] != freelancer_id:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Update status
        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {
                "status": "delivered",
                "delivered_at": datetime.utcnow()
            }}
        )
        
        return jsonify({
            "success": True,
            "message": "Order marked as delivered! Waiting for client approval."
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Approve Order & Release Payment (Client action)
@orders_bp.route("/<order_id>/approve", methods=["POST"])
def approve_order(order_id):
    try:
        data = request.json
        client_id = data.get("client_id")
        
        order = orders_collection.find_one({"_id": ObjectId(order_id)})
        if not order:
            return jsonify({"error": "Order not found"}), 404
        
        # Verify client
        if order["client_id"] != client_id:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Verify order is delivered
        if order["status"] != "delivered":
            return jsonify({"error": "Order must be delivered first"}), 400
        
        # Update status - Release payment
        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {
                "status": "completed",
                "payment_status": "released",
                "completed_at": datetime.utcnow()
            }}
        )
        
        return jsonify({
            "success": True,
            "message": "Payment released to freelancer! ✅"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Cancel Order (Before delivery only)
@orders_bp.route("/<order_id>/cancel", methods=["POST"])
def cancel_order(order_id):
    try:
        data = request.json
        user_id = data.get("user_id")
        
        order = orders_collection.find_one({"_id": ObjectId(order_id)})
        if not order:
            return jsonify({"error": "Order not found"}), 404
        
        # Only allow cancel if not delivered yet
        if order["status"] in ["delivered", "completed"]:
            return jsonify({"error": "Cannot cancel delivered/completed order"}), 400
        
        # Update status
        orders_collection.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": {
                "status": "cancelled",
                "payment_status": "refunded"
            }}
        )
        
        return jsonify({
            "success": True,
            "message": "Order cancelled. Payment refunded."
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500