from flask import Flask, jsonify
from flask_cors import CORS
from routes.users import users_bp
from routes.invoices import invoices_bp
from routes.gigs import gigs_bp
from routes.profile_routes import profile_bp

app = Flask(__name__)
CORS(app)

# Register Blueprints (Routes)
app.register_blueprint(users_bp, url_prefix="/api/users")
app.register_blueprint(invoices_bp, url_prefix="/api/invoices")
app.register_blueprint(gigs_bp, url_prefix="/api/gigs")
app.register_blueprint(profile_bp, url_prefix="/api/profile")

@app.route("/")
def home():
    return jsonify({"message": "CloudCred backend is running ✅"})

if __name__ == "__main__":
    app.run(debug=True)
