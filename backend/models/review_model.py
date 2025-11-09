from config.db_config import db

# Reviews collection
reviews_collection = db["reviews"]

"""
Review Schema:
{
    _id: ObjectId,
    order_id: str,                    # Link to order
    gig_id: str,                      # Link to gig (for context)
    gig_title: str,                   # Gig title (for display)
    freelancer_id: str,               # Who is being rated
    client_id: str,                   # Who is rating
    rating: int,                      # 1-5 stars (required)
    review_text: str,                 # Review text (optional)
    created_at: datetime,             # When review was created
    updated_at: datetime              # When review was last updated
}
"""

# Create indexes for faster queries
reviews_collection.create_index("order_id", unique=True)  # One review per order
reviews_collection.create_index("freelancer_id")          # Query by freelancer
reviews_collection.create_index("client_id")              # Query by client
reviews_collection.create_index("gig_id")                 # Query by gig