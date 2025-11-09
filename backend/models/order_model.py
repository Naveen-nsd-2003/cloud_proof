"""
Order Model - Simple escrow system for gig orders
Handles order creation, tracking, and payment status
"""

from models.user_model import db

# Orders Collection
orders_collection = db['orders']

# Order Schema (for reference):
# {
#     "_id": ObjectId,
#     "gig_id": str,
#     "gig_title": str,  # Cached for display
#     "gig_price": float,  # Original gig price
#     "freelancer_id": str,
#     "client_id": str,
#     "amount": float,  # Payment amount
#     "status": str,  # "pending_payment", "in_progress", "delivered", "completed", "disputed", "cancelled"
#     "payment_status": str,  # "locked", "released", "refunded"
#     "description": str,  # Work description
#     "delivery_date": datetime,  # Expected delivery
#     "created_at": datetime,
#     "delivered_at": datetime,
#     "completed_at": datetime,
#     "notes": str  # Optional client notes
# }

# Order Status Options:
# - pending_payment: Order created, waiting for payment confirmation
# - in_progress: Payment locked, freelancer working
# - delivered: Freelancer marked as delivered, waiting for client approval
# - completed: Client approved, payment released
# - disputed: Dispute raised (future feature)
# - cancelled: Order cancelled

# Payment Status Options:
# - locked: Money secured in escrow
# - released: Payment released to freelancer
# - refunded: Payment refunded to client