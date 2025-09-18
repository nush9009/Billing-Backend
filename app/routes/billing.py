# billing_routes.py (API Endpoints)

from flask import Blueprint, request, jsonify
from app import db
from app.utils.auth import jwt_required_custom
from app.models import Project, Client
from app.models.billing import ProjectBilling, Invoice
from datetime import date, timedelta
import uuid
from decimal import Decimal
from app.routes.projects import get_current_user,get_jwt_identity,is_admin,is_tier1,is_tier2

billing_bp = Blueprint('billing', __name__)

# ---------------- CREATE A BILL ----------------
@billing_bp.route('/bill/create', methods=['POST'])
@jwt_required_custom
def create_bill():
    """Create a new bill (ProjectBilling record) for a project."""
    data = request.get_json()
    project_id = data.get('project_id')
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404

    new_bill = ProjectBilling(
        project_id=project.id,
        billing_type=data.get('billing_type', 'General'),
        amount=Decimal(data.get('amount', 0)),
        description=data.get('description'),
        status='pending', # Starts as pending
        due_date=data.get('due_date')
    )
    db.session.add(new_bill)
    db.session.commit()

    return jsonify({
        'message': 'Bill created successfully. Ready to be invoiced.',
        'bill_id': new_bill.id
    }), 201

# ---------------- GENERATE INVOICE FROM A BILL ----------------
# billing_routes.py (API Endpoint)

@billing_bp.route('/invoice/generate', methods=['POST'])
@jwt_required_custom
def generate_invoice_from_bill():
    """Generate a single invoice from a single pending bill."""
    data = request.get_json()
    bill_id = data.get('bill_id')
    if not bill_id:
        return jsonify({'message': 'bill_id is required'}), 400

    bill = ProjectBilling.query.get(bill_id)
    if not bill:
        return jsonify({'message': 'Bill not found'}), 404
    if bill.status != 'pending':
        return jsonify({'message': f'Bill is not pending. Current status: {bill.status}'}), 400

    # REMOVED: Logic to find the client is no longer necessary.
    # The invoice is strictly tied to the project.

    try:
        new_invoice = Invoice(
            billing_record_id=bill.id,
            project_id=bill.project_id, # Link directly to the project
            invoice_number=f"INV-{uuid.uuid4().hex[:6].upper()}",
            total_amount=bill.amount,
            issue_date=date.today(),
            due_date=bill.due_date or (date.today() + timedelta(days=30)),
            status='sent'
        )
        
        bill.status = 'invoiced'
        
        db.session.add(new_invoice)
        db.session.commit()
        
        return jsonify({
            'message': 'Invoice generated successfully',
            'invoice_id': new_invoice.id,
            'invoice_number': new_invoice.invoice_number
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500

# ---------------- MARK INVOICE AS PAID ----------------
@billing_bp.route('/invoice/<invoice_id>/mark_paid', methods=['POST'])
@jwt_required_custom
def mark_invoice_paid(invoice_id):
    """Mark an invoice and its associated bill as paid."""
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({'message': 'Invoice not found'}), 404
    if invoice.status == 'paid':
        return jsonify({'message': 'Invoice is already marked as paid'}), 400

    # Update invoice status
    invoice.status = 'paid'
    invoice.paid_date = date.today()

    # Update the original bill's status via the relationship
    if invoice.billing_record:
        invoice.billing_record.status = 'paid'

    db.session.commit()
    return jsonify({'message': f'Invoice {invoice.invoice_number} marked as paid.'}), 200

# ---------------- GET ALL BILLS FOR A PROJECT (PAID/UNPAID VIEW) ----------------
@billing_bp.route('/project/<project_id>/bills', methods=['GET'])
@jwt_required_custom
def get_project_bills(project_id):
    """Get all billing records for a project, showing paid/unpaid status."""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404
    
    bills = ProjectBilling.query.filter_by(project_id=project_id).order_by(ProjectBilling.created_at.desc()).all()
    
    return jsonify([
        {
            'bill_id': bill.id,
            'amount': float(bill.amount),
            'description': bill.description,
            'status': bill.status, # This is the key field for paid/unpaid status
            'due_date': bill.due_date.isoformat() if bill.due_date else None,
            'invoice_id': bill.invoice.id if bill.invoice else None
        } for bill in bills
    ]), 200


# @billing_bp.route('/revenue', methods=['GET'])
# @jwt_required_custom
# def revenue_overview():
#     """Get overall revenue stats + billing details for dashboard."""
#     from app.models import Client, Tier1Seller, Tier2Seller  # make sure they exist

#     bills = ProjectBilling.query.join(Project).all()

#     total_bills = len(bills)
#     total_value = sum(float(b.amount) for b in bills)

#     paid_bills = [b for b in bills if b.status == 'paid']
#     pending_bills = [b for b in bills if b.status in ['pending', 'invoiced']]
#     overdue_bills = [
#         b for b in bills if b.status in ['pending', 'invoiced'] and b.due_date and b.due_date < date.today()
#     ]

#     summary = {
#         "total_bills": total_bills,
#         "total_value": total_value,
#         "paid_bills": len(paid_bills),
#         "collected_amount": sum(float(b.amount) for b in paid_bills),
#         "pending_bills": len(pending_bills),
#         "outstanding_amount": sum(float(b.amount) for b in pending_bills),
#         "overdue_bills": len(overdue_bills)
#     }

#     details = []
#     for bill in bills:
#         # client_name = None
#         # tier = None

#         # # resolve client & tier
#         # if bill.project and bill.project.name:
#         #     client_name = bill.project.name
#         # if bill.project and bill.project.tier1_seller_id:
#         #     tier = "Tier-1"
#         # elif bill.project and bill.project.tier2_seller_id:
#         #     tier = "Tier-2"
#         client_name = bill.project.name if bill.project and bill.project.name else "Unknown"
#         tier = "Tier-2" if bill.project and bill.project.tier2_seller_id else ("Tier-1" if bill.project and bill.project.tier1_seller_id else None)

#         details.append({
#             "client_name": client_name or "Unknown",
#             "invoice_id": bill.invoice.invoice_number if bill.invoice else None,
#             "bill_amount": float(bill.amount),
#             "due_date": bill.due_date.isoformat() if bill.due_date else None,
#             "status": (
#                 "Overdue" if bill.status in ["pending", "invoiced"] and bill.due_date and bill.due_date < date.today()
#                 else bill.status.capitalize()
#             ),
#             "payment_date": bill.invoice.paid_date.isoformat() if (bill.invoice and bill.invoice.paid_date) else None,
#             "tier": tier
#         })

#     return jsonify({
#         "summary": summary,
#         "billing_details": details
#     }), 200


# billing_routes.py

# ... (other imports remain the same)
from sqlalchemy import or_ # <-- 

# ... (all other routes remain the same) ...


@billing_bp.route('/revenue', methods=['GET'])
@jwt_required_custom
def revenue_overview():
    """
    Get overall revenue stats + billing details for the dashboard,
    filtered by the current user's role and permissions.
    """
    # --- MODIFICATION START ---

    # 1. Get the current user's identity and role
    user_id = get_jwt_identity()
    current_user = get_current_user(user_id)
    if not current_user:
        return jsonify({'message': 'User not found or invalid token'}), 401

    # Import models here as in the original code
    from app.models import Admin, Tier1Seller, Tier2Seller

    # 2. Build the base query to join ProjectBilling with Project
    base_query = ProjectBilling.query.join(Project, ProjectBilling.project_id == Project.id)

    # 3. Apply role-based filtering to the query
    if is_admin(current_user):
        # Admin sees everything, no additional filters needed.
        bills = base_query.all()
    
    elif is_tier1(current_user):
        # Tier 1 Seller sees their own projects AND projects of Tier 2 sellers they manage.
        
        # Get IDs of all Tier 2 sellers managed by this Tier 1 seller
        managed_tier2_ids = [
            seller.id for seller in Tier2Seller.query.filter_by(tier1_seller_id=current_user['id']).all()
        ]
        
        bills = base_query.filter(
            or_(
                Project.tier1_seller_id == current_user['id'],
                Project.tier2_seller_id.in_(managed_tier2_ids)
            )
        ).all()

    elif is_tier2(current_user):
        # Tier 2 Seller sees only their own projects.
        bills = base_query.filter(Project.tier2_seller_id == current_user['id']).all()
    
    else:
        # If user has no recognizable role, return no bills.
        bills = []
        
    # --- MODIFICATION END ---

    # The rest of the function processes the filtered `bills` list
    total_bills = len(bills)
    total_value = sum(float(b.amount) for b in bills)

    paid_bills = [b for b in bills if b.status == 'paid']
    pending_bills = [b for b in bills if b.status in ['pending', 'invoiced']]
    overdue_bills = [
        b for b in bills if b.status in ['pending', 'invoiced'] and b.due_date and b.due_date < date.today()
    ]

    summary = {
        "total_bills": total_bills,
        "total_value": total_value,
        "paid_bills": len(paid_bills),
        "collected_amount": sum(float(b.amount) for b in paid_bills),
        "pending_bills": len(pending_bills),
        "outstanding_amount": sum(float(b.amount) for b in pending_bills),
        "overdue_bills": len(overdue_bills)
    }

    details = []
    for bill in bills:
        client_name = bill.project.name if bill.project and bill.project.name else "Unknown"
        tier = "Tier-2" if bill.project and bill.project.tier2_seller_id else ("Tier-1" if bill.project and bill.project.tier1_seller_id else None)

        details.append({
            "client_name": client_name or "Unknown",
            "invoice_id": bill.invoice.invoice_number if bill.invoice else None,
            "bill_amount": float(bill.amount),
            "due_date": bill.due_date.isoformat() if bill.due_date else None,
            "status": (
                "Overdue" if bill.status in ["pending", "invoiced"] and bill.due_date and bill.due_date < date.today()
                else bill.status.capitalize()
            ),
            "payment_date": bill.invoice.paid_date.isoformat() if (bill.invoice and bill.invoice.paid_date) else None,
            "tier": tier
        })

    return jsonify({
        "summary": summary,
        "billing_details": details
    }), 200
