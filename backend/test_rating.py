from models.user_model import users_collection
from models.review_model import reviews_collection
from bson import ObjectId

# Replace with your actual freelancer email
FREELANCER_EMAIL = "naveennsd1515@gmail.com"

# Find the freelancer
freelancer = users_collection.find_one({"email": FREELANCER_EMAIL})
if not freelancer:
    print("❌ Freelancer not found!")
    exit()

freelancer_id = str(freelancer["_id"])
print(f"✅ Found freelancer: {freelancer['name']}")
print(f"📋 User ID: {freelancer_id}")

# Find all reviews for this freelancer
reviews = list(reviews_collection.find({"freelancer_id": freelancer_id}))
print(f"📊 Found {len(reviews)} reviews with matching freelancer_id")

if len(reviews) == 0:
    # Try searching by email (in case that's what's stored)
    reviews = list(reviews_collection.find({"freelancer_id": FREELANCER_EMAIL}))
    print(f"📊 Found {len(reviews)} reviews with freelancer email")

# Calculate rating
if reviews:
    total_rating = sum(r["rating"] for r in reviews)
    average_rating = round(total_rating / len(reviews), 1)
    
    breakdown = {
        "5_star": sum(1 for r in reviews if r["rating"] == 5),
        "4_star": sum(1 for r in reviews if r["rating"] == 4),
        "3_star": sum(1 for r in reviews if r["rating"] == 3),
        "2_star": sum(1 for r in reviews if r["rating"] == 2),
        "1_star": sum(1 for r in reviews if r["rating"] == 1)
    }
    
    print(f"⭐ Average Rating: {average_rating}")
    print(f"📊 Breakdown: {breakdown}")
    
    # Update user
    result = users_collection.update_one(
        {"_id": ObjectId(freelancer_id)},
        {"$set": {
            "average_rating": average_rating,
            "total_reviews": len(reviews),
            "rating_breakdown": breakdown
        }}
    )
    
    print(f"✅ Update result: Matched={result.matched_count}, Modified={result.modified_count}")
    
    # Verify
    updated_user = users_collection.find_one({"_id": ObjectId(freelancer_id)})
    print(f"✅ Verified - New rating: {updated_user.get('average_rating')}")
else:
    print("❌ No reviews found!")