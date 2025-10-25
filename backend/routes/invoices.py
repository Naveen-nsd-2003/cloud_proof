
from flask import Blueprint, request, jsonify
from models.user_model import invoices_collection, db, users_collection
from models.gig_model import gigs_collection
from services.aws_service import upload_invoice_to_s3
from services.blockchain_service import approve_invoice_on_chain, get_blockchain_status, create_invoice_on_chain
from services.email_service import send_invoice_created_email, send_invoice_approved_email
from bson import ObjectId
from datetime import datetime
import json
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


# Define Blueprint
invoices_bp = Blueprint("invoices", __name__)

# ---------------- PDF Generator ----------------
def generate_invoice_pdf(invoice_id, description, amount, transaction_hash=None):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setTitle(f"Invoice {invoice_id}")
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "CLOUDCRED INVOICE")

    p.setFont("Helvetica", 12)
    p.drawString(100, 700, f"Invoice ID: {invoice_id}")
    p.drawString(100, 680, f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    p.drawString(100, 660, f"Status: APPROVED")

    p.drawString(100, 620, "Description:")
    desc_lines = [description[i:i+80] for i in range(0, len(description), 80)]
    y_pos = 600
    for line in desc_lines[:3]:
        p.drawString(120, y_pos, line)
        y_pos -= 20

    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 540, f"Amount: ${amount}")

    p.setFont("Helvetica", 10)
    p.drawString(100, 500, "Payment verified on blockchain")
    if transaction_hash:
        p.drawString(100, 480, f"TX: {transaction_hash[:30]}...")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.getvalue()

# ---------------- JSON Encoder ----------------
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# ---------------- ROUTES ----------------

# ✅ List all invoices
@invoices_bp.route("/", methods=["GET"])
def list_invoices():
    try:
        invoices = list(invoices_collection.find())
        return json.dumps({"invoices": invoices}, cls=CustomJSONEncoder)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Create new invoice + Send email to client
@invoices_bp.route("/create", methods=["POST"])
def create_invoice():
    try:
        data = request.json
        required_fields = ["freelancer_id", "client_id", "gig_id", "description", "amount"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        try:
            amount = float(data.get("amount"))
            if amount <= 0:
                return jsonify({"error": "Amount must be greater than 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid amount format"}), 400

        try:
            freelancer_object_id = ObjectId(data.get("freelancer_id"))
            client_object_id = ObjectId(data.get("client_id"))
            gig_object_id = ObjectId(data.get("gig_id"))
        except:
            return jsonify({"error": "Invalid ObjectId format"}), 400

        gig = gigs_collection.find_one({"_id": gig_object_id})
        if not gig:
            return jsonify({"error": "Gig not found"}), 404
        if gig.get("freelancer_id") != data.get("freelancer_id"):
            return jsonify({"error": "Gig does not belong to the freelancer"}), 403

        invoice = {
            "freelancer_id": data.get("freelancer_id"),
            "client_id": data.get("client_id"),
            "gig_id": data.get("gig_id"),
            "description": data.get("description"),
            "amount": amount,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = invoices_collection.insert_one(invoice)
        invoice["_id"] = str(result.inserted_id)

        blockchain_result = create_invoice_on_chain(
            invoice["_id"], data["freelancer_id"], data["client_id"], data["amount"], data["description"]
        )

        if not blockchain_result.get("success"):
            return jsonify({"error": "Blockchain registration failed"}), 500

        # 📧 Send email notification to client
        try:
            freelancer = users_collection.find_one({"_id": freelancer_object_id})
            client = users_collection.find_one({"_id": client_object_id})
            
            if client and client.get("email"):
                email_result = send_invoice_created_email(
                    client_email=client["email"],
                    client_name=client.get("name", "Client"),
                    freelancer_name=freelancer.get("name", "Freelancer") if freelancer else "Unknown",
                    invoice_data={
                        "invoice_id": invoice["_id"],
                        "amount": invoice["amount"],
                        "description": invoice["description"],
                        "created_at": invoice["created_at"].strftime('%B %d, %Y at %I:%M %p')
                    }
                )
                
                if email_result["success"]:
                    print(f"✅ Invoice notification email sent to {client['email']}")
                else:
                    print(f"⚠️ Failed to send email: {email_result.get('error')}")
        except Exception as email_error:
            print(f"⚠️ Email notification error: {str(email_error)}")

        return jsonify({"message": "Invoice created successfully ✅", "invoice": invoice}), 201

    except Exception as e:
        return jsonify({"error": f"Failed to create invoice: {str(e)}"}), 500

# ✅ Approve invoice + Send email to freelancer
@invoices_bp.route("/approve/<invoice_id>", methods=["POST"])
def approve_invoice(invoice_id):
    try:
        object_id = ObjectId(invoice_id)
        invoice = invoices_collection.find_one({"_id": object_id})
        if not invoice:
            return jsonify({"error": "Invoice not found"}), 404

        if invoice.get("status") == "approved":
            return jsonify({"error": "Invoice already approved"}), 400

        client_id = request.json.get("client_id") if request.json else None
        if not client_id:
            return jsonify({"error": "client_id is required"}), 400
        if invoice.get("client_id") != client_id:
            return jsonify({"error": "Unauthorized client"}), 403

        blockchain_result = approve_invoice_on_chain(invoice_id, client_id)
        if not blockchain_result.get("success"):
            return jsonify({"error": "Blockchain approval failed"}), 500

        update_data = {
            "status": "approved",
            "approved_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "blockchain_verified": True,
            "transaction_hash": blockchain_result.get("transaction_hash"),
            "block_number": blockchain_result.get("block_number")
        }

        invoices_collection.update_one({"_id": object_id}, {"$set": update_data})

        # Generate PDF and upload
        gig = gigs_collection.find_one({"_id": ObjectId(invoice["gig_id"])})
        gig_title = gig.get("title") if gig else "Project"
        pdf_bytes = generate_invoice_pdf(
            invoice_id, 
            f"{gig_title}: {invoice['description']}", 
            invoice['amount'], 
            blockchain_result.get("transaction_hash")
        )
        pdf_url = upload_invoice_to_s3(pdf_bytes, f"invoice_{invoice_id}.pdf")

        invoices_collection.update_one({"_id": object_id}, {"$set": {"pdf_url": pdf_url}})

        # 📧 Send email notification to freelancer
        try:
            freelancer_object_id = ObjectId(invoice["freelancer_id"])
            client_object_id = ObjectId(client_id)
            
            freelancer = users_collection.find_one({"_id": freelancer_object_id})
            client = users_collection.find_one({"_id": client_object_id})
            
            if freelancer and freelancer.get("email"):
                email_result = send_invoice_approved_email(
                    freelancer_email=freelancer["email"],
                    freelancer_name=freelancer.get("name", "Freelancer"),
                    client_name=client.get("name", "Client") if client else "Unknown",
                    invoice_data={
                        "invoice_id": invoice_id,
                        "amount": invoice["amount"],
                        "transaction_hash": blockchain_result.get("transaction_hash"),
                        "pdf_url": pdf_url
                    }
                )
                
                if email_result["success"]:
                    print(f"✅ Approval notification email sent to {freelancer['email']}")
                else:
                    print(f"⚠️ Failed to send email: {email_result.get('error')}")
        except Exception as email_error:
            print(f"⚠️ Email notification error: {str(email_error)}")

        return jsonify({
            "message": "Invoice approved successfully ✅",
            "pdf_url": pdf_url,
            "transaction_hash": blockchain_result.get("transaction_hash"),
            "block_number": blockchain_result.get("block_number"),
            "status": "approved"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Get invoice by ID
@invoices_bp.route("/<invoice_id>", methods=["GET"])
def get_invoice(invoice_id):
    try:
        object_id = ObjectId(invoice_id)
        invoice = invoices_collection.find_one({"_id": object_id})
        if not invoice:
            return jsonify({"error": "Invoice not found"}), 404
        return json.dumps({"invoice": invoice}, cls=CustomJSONEncoder)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ Fetch invoices by user (for dashboard UI)
@invoices_bp.route("/user/<user_id>", methods=["GET"])
def get_invoices_by_user(user_id):
    try:
        invoices = list(invoices_collection.find({
            "$or": [{"freelancer_id": user_id}, {"client_id": user_id}]
        }))
        return json.dumps({"invoices": invoices}, cls=CustomJSONEncoder)
    except Exception as e:
        return jsonify({"error": str(e)}), 500