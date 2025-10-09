""" from flask import Blueprint, request, jsonify
from models.user_model import invoices_collection, db  # import db for gigs
from services.aws_service import upload_invoice_to_s3
from services.blockchain_service import approve_invoice_on_chain, get_blockchain_status
from bson import ObjectId
from datetime import datetime
import json
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Define gigs_collection here using your existing db connection
gigs_collection = db["gigs"]

# Temporary verification function (placeholder)
def verify_invoice_on_chain(invoice_id):
  
    try:
        status = get_blockchain_status()
        return {"success": status.get("connected", False), "approved": False}
    except:
        return {"success": False, "error": "Verification not available"}

# Function to generate a real PDF invoice
def generate_invoice_pdf(invoice_id, description, amount, transaction_hash=None):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # PDF content
    p.setTitle(f"Invoice {invoice_id}")
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "CLOUDCRED INVOICE")
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 700, f"Invoice ID: {invoice_id}")
    p.drawString(100, 680, f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    p.drawString(100, 660, f"Status: APPROVED")
    
    p.drawString(100, 620, "Description:")
    # Handle long descriptions
    desc_lines = [description[i:i+80] for i in range(0, len(description), 80)]
    y_pos = 600
    for line in desc_lines[:3]:  # Max 3 lines
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

invoices_bp = Blueprint("invoices", __name__)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

@invoices_bp.route("/", methods=["GET"])
def list_invoices():
    try:
        invoices = list(invoices_collection.find())
        return json.dumps({"invoices": invoices}, cls=CustomJSONEncoder)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@invoices_bp.route("/create", methods=["POST"])
def create_invoice():
    try:
        data = request.json

        # Validate required fields
        required_fields = ["freelancer_id", "client_id", "gig_id", "description", "amount"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate amount
        try:
            amount = float(data.get("amount"))
            if amount <= 0:
                return jsonify({"error": "Amount must be greater than 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Amount must be a valid number"}), 400

        # Validate ObjectId
        try:
            freelancer_object_id = ObjectId(data.get("freelancer_id"))
            client_object_id = ObjectId(data.get("client_id"))
            gig_object_id = ObjectId(data.get("gig_id"))
        except Exception:
            return jsonify({"error": "Invalid ObjectId format"}), 400

        # Check that gig belongs to freelancer
        gig = gigs_collection.find_one({"_id": gig_object_id})
        if not gig:
            return jsonify({"error": "Gig not found"}), 404
        if gig.get("freelancer_id") != data.get("freelancer_id"):
            return jsonify({"error": "This gig does not belong to the freelancer"}), 403

        # Create invoice
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

        return json.dumps({
            "message": "Invoice created successfully ✅",
            "invoice": invoice
        }, cls=CustomJSONEncoder), 201

    except Exception as e:
        return jsonify({"error": f"Failed to create invoice: {str(e)}"}), 500





@invoices_bp.route("/approve/<invoice_id>", methods=["POST"])
def approve_invoice(invoice_id):
    
    try:
        # Validate invoice_id format
        try:
            object_id = ObjectId(invoice_id)
        except Exception:
            return jsonify({"error": "Invalid invoice ID format"}), 400

        # Fetch invoice
        invoice = invoices_collection.find_one({"_id": object_id})
        if not invoice:
            return jsonify({"error": "Invoice not found"}), 404

        # Prevent double approval
        if invoice.get("status") == "approved":
            return jsonify({"error": "Invoice is already approved"}), 400

        # Get client_id from request
        client_id = request.json.get("client_id") if request.json else None
        if not client_id:
            return jsonify({"error": "client_id is required"}), 400

        # AUTHORIZATION: Only assigned client can approve
        if invoice.get("client_id") != client_id:
            return jsonify({"error": "❌ You are not authorized to approve this invoice"}), 403

        # Blockchain approval
        blockchain_result = approve_invoice_on_chain(invoice_id, client_id)
        if not blockchain_result.get("success"):
            return jsonify({
                "error": f"Blockchain approval failed: {blockchain_result.get('error', 'Unknown error')}"
            }), 500

        # Update invoice in DB
        update_data = {
            "status": "approved",
            "approved_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "blockchain_verified": True
        }
        # Add blockchain info
        for key in ["transaction_hash", "block_number", "gas_used"]:
            if blockchain_result.get(key):
                update_data[key] = blockchain_result[key]

        invoices_collection.update_one({"_id": object_id}, {"$set": update_data})

        # Generate PDF
        try:
            gig_id = invoice.get("gig_id")
            from models.gig_model import gigs_collection  # safe import
            gig = gigs_collection.find_one({"_id": ObjectId(gig_id)})
            gig_title = gig.get("title") if gig else "Project"

            pdf_bytes = generate_invoice_pdf(
                invoice_id=invoice_id,
                description=f"{gig_title}: {invoice['description']}",
                amount=invoice['amount'],
                transaction_hash=blockchain_result.get("transaction_hash")
            )

            pdf_url = upload_invoice_to_s3(pdf_bytes, f"invoice_{invoice_id}.pdf")
            invoices_collection.update_one(
                {"_id": object_id},
                {"$set": {"pdf_url": pdf_url, "updated_at": datetime.utcnow()}}
            )

            return jsonify({
                "message": "Invoice approved successfully ✅",
                "invoice_id": invoice_id,
                "pdf_url": pdf_url,
                "status": "approved",
                "blockchain_verified": True,
                "transaction_hash": blockchain_result.get("transaction_hash"),
                "block_number": blockchain_result.get("block_number"),
                "gas_used": blockchain_result.get("gas_used")
            })

        except Exception as pdf_error:
            # Approval succeeded, but PDF failed
            return jsonify({
                "message": "Invoice approved but PDF generation failed",
                "invoice_id": invoice_id,
                "status": "approved",
                "blockchain_verified": True,
                "transaction_hash": blockchain_result.get("transaction_hash"),
                "warning": str(pdf_error)
            }), 207

    except Exception as e:
        return jsonify({"error": f"Failed to approve invoice: {str(e)}"}), 500

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

@invoices_bp.route("/verify-blockchain/<invoice_id>", methods=["GET"])
def verify_invoice_blockchain(invoice_id):
   
    try:
        object_id = ObjectId(invoice_id)
        invoice = invoices_collection.find_one({"_id": object_id})
        
        if not invoice:
            return jsonify({"error": "Invoice not found"}), 404
        
        blockchain_result = verify_invoice_on_chain(invoice_id)
        
        return jsonify({
            "invoice_id": invoice_id,
            "database_status": invoice.get("status"),
            "blockchain_verified": blockchain_result.get("success", False),
            "transaction_hash": invoice.get("transaction_hash"),
            "block_number": invoice.get("block_number")
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500 """
    
from flask import Blueprint, request, jsonify
from models.user_model import invoices_collection, db  # import db for gigs
from models.gig_model import gigs_collection
from services.aws_service import upload_invoice_to_s3
from services.blockchain_service import approve_invoice_on_chain, get_blockchain_status, create_invoice_on_chain
from bson import ObjectId
from datetime import datetime
import json
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter



# Define gigs_collection here using your existing db connection
gigs_collection = db["gigs"]

# Temporary verification function (placeholder)
def verify_invoice_on_chain(invoice_id):
    try:
        status = get_blockchain_status()
        return {"success": status.get("connected", False), "approved": False}
    except:
        return {"success": False, "error": "Verification not available"}

# Function to generate a real PDF invoice
def generate_invoice_pdf(invoice_id, description, amount, transaction_hash=None):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # PDF content
    p.setTitle(f"Invoice {invoice_id}")
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "CLOUDCRED INVOICE")
    
    p.setFont("Helvetica", 12)
    p.drawString(100, 700, f"Invoice ID: {invoice_id}")
    p.drawString(100, 680, f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    p.drawString(100, 660, f"Status: APPROVED")
    
    p.drawString(100, 620, "Description:")
    # Handle long descriptions
    desc_lines = [description[i:i+80] for i in range(0, len(description), 80)]
    y_pos = 600
    for line in desc_lines[:3]:  # Max 3 lines
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

invoices_bp = Blueprint("invoices", __name__)

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle ObjectId and datetime objects"""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

@invoices_bp.route("/", methods=["GET"])
def list_invoices():
    try:
        invoices = list(invoices_collection.find())
        return json.dumps({"invoices": invoices}, cls=CustomJSONEncoder)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- FIXED create_invoice -------------------
@invoices_bp.route("/create", methods=["POST"])
def create_invoice():
    try:
        data = request.json

        # Validate required fields
        required_fields = ["freelancer_id", "client_id", "gig_id", "description", "amount"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate amount
        try:
            amount = float(data.get("amount"))
            if amount <= 0:
                return jsonify({"error": "Amount must be greater than 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Amount must be a valid number"}), 400

        # Validate ObjectId
        try:
            freelancer_object_id = ObjectId(data.get("freelancer_id"))
            client_object_id = ObjectId(data.get("client_id"))
            gig_object_id = ObjectId(data.get("gig_id"))
        except Exception:
            return jsonify({"error": "Invalid ObjectId format"}), 400

        # Check that gig belongs to freelancer
        gig = gigs_collection.find_one({"_id": gig_object_id})
        if not gig:
            return jsonify({"error": "Gig not found"}), 404
        if gig.get("freelancer_id") != data.get("freelancer_id"):
            return jsonify({"error": "This gig does not belong to the freelancer"}), 403

        # Create invoice
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

        # ------------------- ADDED: Register invoice on blockchain -------------------
        blockchain_result = create_invoice_on_chain(
            invoice["_id"],
            data.get("freelancer_id"),
            data.get("client_id"),
            data.get("amount"),
            data.get("description")
        )

        if not blockchain_result.get("success"):
            return jsonify({
                "error": f"Failed to register invoice on blockchain: {blockchain_result.get('error')}"
            }), 500
        # -------------------------------------------------------------------------------

        return json.dumps({
            "message": "Invoice created successfully ✅",
            "invoice": invoice
        }, cls=CustomJSONEncoder), 201

    except Exception as e:
        return jsonify({"error": f"Failed to create invoice: {str(e)}"}), 500
# -------------------------------------------------------------------------------

@invoices_bp.route("/approve/<invoice_id>", methods=["POST"])
def approve_invoice(invoice_id):
    """Approve an invoice - ONLY BY ASSIGNED CLIENT"""
    try:
        # Validate invoice_id format
        try:
            object_id = ObjectId(invoice_id)
        except Exception:
            return jsonify({"error": "Invalid invoice ID format"}), 400

        # Fetch invoice
        invoice = invoices_collection.find_one({"_id": object_id})
        if not invoice:
            return jsonify({"error": "Invoice not found"}), 404

        # Prevent double approval
        if invoice.get("status") == "approved":
            return jsonify({"error": "Invoice is already approved"}), 400

        # Get client_id from request
        client_id = request.json.get("client_id") if request.json else None
        if not client_id:
            return jsonify({"error": "client_id is required"}), 400

        # AUTHORIZATION: Only assigned client can approve
        if invoice.get("client_id") != client_id:
            return jsonify({"error": "❌ You are not authorized to approve this invoice"}), 403

        # Blockchain approval
        blockchain_result = approve_invoice_on_chain(invoice_id, client_id)
        if not blockchain_result.get("success"):
            return jsonify({
                "error": f"Blockchain approval failed: {blockchain_result.get('error', 'Unknown error')}"
            }), 500

        # Update invoice in DB
        update_data = {
            "status": "approved",
            "approved_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "blockchain_verified": True
        }
        # Add blockchain info
        for key in ["transaction_hash", "block_number", "gas_used"]:
            if blockchain_result.get(key):
                update_data[key] = blockchain_result[key]

        invoices_collection.update_one({"_id": object_id}, {"$set": update_data})

        # Generate PDF
        try:
            gig_id = invoice.get("gig_id")
           # from models.gig_model import gigs_collection  # safe import
            gig = gigs_collection.find_one({"_id": ObjectId(gig_id)})
            gig_title = gig.get("title") if gig else "Project"

            pdf_bytes = generate_invoice_pdf(
                invoice_id=invoice_id,
                description=f"{gig_title}: {invoice['description']}",
                amount=invoice['amount'],
                transaction_hash=blockchain_result.get("transaction_hash")
            )

            pdf_url = upload_invoice_to_s3(pdf_bytes, f"invoice_{invoice_id}.pdf")
            invoices_collection.update_one(
                {"_id": object_id},
                {"$set": {"pdf_url": pdf_url, "updated_at": datetime.utcnow()}}
            )

            return jsonify({
                "message": "Invoice approved successfully ✅",
                "invoice_id": invoice_id,
                "pdf_url": pdf_url,
                "status": "approved",
                "blockchain_verified": True,
                "transaction_hash": blockchain_result.get("transaction_hash"),
                "block_number": blockchain_result.get("block_number"),
                "gas_used": blockchain_result.get("gas_used")
            })

        except Exception as pdf_error:
            # Approval succeeded, but PDF failed
            return jsonify({
                "message": "Invoice approved but PDF generation failed",
                "invoice_id": invoice_id,
                "status": "approved",
                "blockchain_verified": True,
                "transaction_hash": blockchain_result.get("transaction_hash"),
                "warning": str(pdf_error)
            }), 207

    except Exception as e:
        return jsonify({"error": f"Failed to approve invoice: {str(e)}"}), 500

@invoices_bp.route("/<invoice_id>", methods=["GET"])
def get_invoice(invoice_id):
    """Get a specific invoice"""
    try:
        object_id = ObjectId(invoice_id)
        invoice = invoices_collection.find_one({"_id": object_id})
        
        if not invoice:
            return jsonify({"error": "Invoice not found"}), 404
        
        return json.dumps({"invoice": invoice}, cls=CustomJSONEncoder)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@invoices_bp.route("/verify-blockchain/<invoice_id>", methods=["GET"])
def verify_invoice_blockchain(invoice_id):
    """Verify blockchain consistency"""
    try:
        object_id = ObjectId(invoice_id)
        invoice = invoices_collection.find_one({"_id": object_id})
        
        if not invoice:
            return jsonify({"error": "Invoice not found"}), 404
        
        blockchain_result = verify_invoice_on_chain(invoice_id)
        
        return jsonify({
            "invoice_id": invoice_id,
            "database_status": invoice.get("status"),
            "blockchain_verified": blockchain_result.get("success", False),
            "transaction_hash": invoice.get("transaction_hash"),
            "block_number": invoice.get("block_number")
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
