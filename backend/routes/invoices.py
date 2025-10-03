from flask import Blueprint, request, jsonify
from models.user_model import invoices_collection
from services.aws_service import upload_invoice_to_s3
from services.blockchain_service import approve_invoice_on_chain, get_blockchain_status
from bson import ObjectId
from datetime import datetime
import json

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

# Temporary verification function (placeholder)
def verify_invoice_on_chain(invoice_id):
    """Temporary placeholder for blockchain verification"""
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
    """Get all invoices"""
    try:
        invoices = list(invoices_collection.find())
        return json.dumps({"invoices": invoices}, cls=CustomJSONEncoder)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@invoices_bp.route("/create", methods=["POST"])
def create_invoice():
    """Create a new invoice"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ["freelancer_id", "client_id", "description", "amount"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate amount is numeric
        try:
            amount = float(data.get("amount"))
            if amount <= 0:
                return jsonify({"error": "Amount must be greater than 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Amount must be a valid number"}), 400
        
        invoice = {
            "freelancer_id": data.get("freelancer_id"),
            "client_id": data.get("client_id"),
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
    """Approve an invoice - ONLY BY ASSIGNED CLIENT"""
    try:
        # Validate ObjectId format
        try:
            object_id = ObjectId(invoice_id)
        except Exception:
            return jsonify({"error": "Invalid invoice ID format"}), 400
        
        # Check if invoice exists
        invoice = invoices_collection.find_one({"_id": object_id})
        if not invoice:
            return jsonify({"error": "Invoice not found"}), 404
        
        # Check if already approved
        if invoice.get("status") == "approved":
            return jsonify({"error": "Invoice is already approved"}), 400
        
        # Get client_id from request
        client_id = request.json.get("client_id") if request.json else None
        if not client_id:
            return jsonify({"error": "client_id is required"}), 400
        
        # AUTHORIZATION CHECK: Only assigned client can approve
        if invoice.get("client_id") != client_id:
            return jsonify({"error": "You are not authorized to approve this invoice"}), 403
        
        # Approve on blockchain
        blockchain_result = approve_invoice_on_chain(invoice_id, client_id)
        
        if not blockchain_result.get("success"):
            error_msg = blockchain_result.get("error", "Unknown error")
            return jsonify({"error": f"Blockchain approval failed: {error_msg}"}), 500
        
        # Prepare update data
        update_data = {
            "status": "approved",
            "approved_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "blockchain_verified": True
        }
        
        # Add blockchain data
        if blockchain_result.get("transaction_hash"):
            update_data["transaction_hash"] = blockchain_result["transaction_hash"]
        if blockchain_result.get("block_number"):
            update_data["block_number"] = blockchain_result["block_number"]
        if blockchain_result.get("gas_used"):
            update_data["gas_used"] = blockchain_result["gas_used"]
        
        # Update database
        invoices_collection.update_one({"_id": object_id}, {"$set": update_data})
        
        # Generate PDF
        try:
            pdf_bytes = generate_invoice_pdf(
                invoice_id=invoice_id,
                description=invoice['description'],
                amount=invoice['amount'],
                transaction_hash=blockchain_result.get("transaction_hash")
            )
            
            invoice_url = upload_invoice_to_s3(pdf_bytes, f"invoice_{invoice_id}.pdf")
            
            # Update with PDF URL
            invoices_collection.update_one(
                {"_id": object_id}, 
                {"$set": {"pdf_url": invoice_url, "updated_at": datetime.utcnow()}}
            )
            
            return jsonify({
                "message": "Invoice approved successfully ✅",
                "invoice_id": invoice_id,
                "pdf_url": invoice_url,
                "status": "approved",
                "blockchain_verified": True,
                "transaction_hash": blockchain_result.get("transaction_hash"),
                "block_number": blockchain_result.get("block_number"),
                "gas_used": blockchain_result.get("gas_used")
            })
            
        except Exception as upload_error:
            return jsonify({
                "message": "Invoice approved but PDF failed",
                "invoice_id": invoice_id,
                "status": "approved",
                "blockchain_verified": True,
                "transaction_hash": blockchain_result.get("transaction_hash"),
                "warning": str(upload_error)
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