# app/routes/billing.py

from flask import Blueprint, request, jsonify, current_app
from app import db
from app.utils.auth import jwt_required_custom
from app.models import Project
from app.models.project import Client
from app.models.billing import ProjectBilling, Invoice
from app.models.seller import Tier1Seller, Tier2Seller
from datetime import date, timedelta
import uuid
from decimal import Decimal
import stripe # <-- ADD IMPORT

billing_bp = Blueprint('billing', __name__)
# app/routes/billing.py


# ---------------- CREATE A BILL (UPDATED) ----------------
@billing_bp.route('/bill/create', methods=['POST'])
@jwt_required_custom
def create_bill():
    data = request.get_json()
    project_id = data.get('project_id')
    
    project = Project.query.options(db.joinedload(Project.subscription_plan)).get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404

    # --- FIX: Get the amount from the subscription plan, not the request ---
    if not project.subscription_plan or not project.subscription_plan.price:
        return jsonify({'message': 'Project does not have a subscription plan with a price.'}), 400
    
    bill_amount = Decimal(project.subscription_plan.price)
    # --- END OF FIX ---

    new_bill = ProjectBilling(
        project_id=project.id,
        billing_type=data.get('billing_type', 'General'),
        amount=bill_amount, # Use the correct amount from the plan
        description=data.get('description'),
        status='pending',
        due_date=data.get('due_date')
    )
    db.session.add(new_bill)
    db.session.commit()

    return jsonify({
        'message': 'Bill created successfully with correct amount. Ready to be invoiced.',
        'bill_id': new_bill.id
    }), 201



# ---------------- GENERATE INVOICE FROM BILL (NO CHANGE) ----------------
@billing_bp.route('/invoice/generate', methods=['POST'])
@jwt_required_custom
def generate_invoice_from_bill():
    data = request.get_json()
    bill_id = data.get('bill_id')
    if not bill_id:
        return jsonify({'message': 'bill_id is required'}), 400

    bill = ProjectBilling.query.get(bill_id)
    if not bill:
        return jsonify({'message': 'Bill not found'}), 404
    if bill.status != 'pending':
        return jsonify({'message': f'Bill is not pending. Current status: {bill.status}'}), 400

    try:
        new_invoice = Invoice(
            billing_record_id=bill.id,
            project_id=bill.project_id,
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


# ---------------- INITIATE PAYMENT FOR AN INVOICE (UPDATED) ----------------
@billing_bp.route('/invoice/<invoice_id>/initiate-payment', methods=['POST'])
@jwt_required_custom
def initiate_invoice_payment(invoice_id):
    """
    Creates a Stripe PaymentIntent for the correct commission amount.
    Tier-2 → pays Tier-1's commission, which is then split.
    Tier-1 → pays Admin's commission directly.
    """
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    
    current_user = get_current_user(get_jwt_identity())
    user_role = 'tier2' if is_tier2(current_user) else 'tier1' if is_tier1(current_user) else None
    if not user_role:
        return jsonify({'message': 'Unauthorized role'}), 403

    # Use joinedload to efficiently fetch related objects
    invoice = Invoice.query.options(
        db.joinedload(Invoice.project).joinedload(Project.subscription_plan)
    ).filter_by(invoice_number=invoice_id).first()

    if not invoice:
        return jsonify({'message': 'Invoice not found'}), 404
    if invoice.status not in ['draft', 'sent', 'pending', 'overdue']:
        return jsonify({'message': f'Invoice cannot be paid. Status: {invoice.status}'}), 400

    project = invoice.project
    plan = project.subscription_plan
    if not plan:
        return jsonify({'message': 'Project has no subscription plan configured'}), 500

    # --- FIX: CALCULATE THE CORRECT PAYABLE AMOUNT BASED ON ROLE ---
    amount_to_pay = Decimal('0.0')
    
    if user_role == 'tier2' and plan.tier1_commission_pct is not None:
        commission_pct = Decimal(plan.tier1_commission_pct)
        amount_to_pay = Decimal(invoice.total_amount) * (commission_pct / 100)
    
    elif user_role == 'tier1' and plan.admin_commission_pct is not None:
        commission_pct = Decimal(plan.admin_commission_pct)
        amount_to_pay = Decimal(invoice.total_amount) * (commission_pct / 100)
        
    else:
        return jsonify({'message': 'Commission not configured for this plan'}), 400

    amount_in_cents = int(amount_to_pay * 100)
    
    # --- FIX: MAKE CURRENCY FLEXIBLE ---
    # Assumes the plan might have a currency, otherwise falls back to config.
    currency = getattr(plan, 'currency', None) or current_app.config.get('STRIPE_CURRENCY', 'usd')

    # Safeguard against Stripe's minimum charge amount (e.g., 50 cents for USD)
    if amount_in_cents < 50:
        return jsonify({'message': 'Payable amount is below the minimum charge.'}), 400

    try:
        # ----- Tier-2 Seller Flow -----
        if user_role == 'tier2':
            # This logic correctly splits the amount_in_cents (the commission)
            # between the Tier-1 seller and the Admin.
            admin_pct = Decimal(plan.admin_commission_pct or 0)
            admin_amount = int(amount_in_cents * (admin_pct / 100))
            tier1_amount = amount_in_cents - admin_amount

            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=currency,
                payment_method_types=['card'],
                description=f"Commission Payment for Invoice #{invoice.invoice_number}",
                transfer_group=invoice.invoice_number,
                metadata={'invoice_id': invoice.id, 'role': 'tier2'},
            )

            # store split data for webhook handling
            invoice.transfer_data = {
                # 'tier1_account_id': project.tier1_seller.stripe_account_id if project.tier1_seller else None,
                'tier1_amount': tier1_amount,
                # 'admin_account_id': current_app.config.get('ADMIN_STRIPE_ACCOUNT_ID'),
                'admin_amount': admin_amount,
            }

        # ----- Tier-1 Seller Flow -----
        elif user_role == 'tier1':
            intent = stripe.PaymentIntent.create(
                amount=amount_in_cents,
                currency=currency,
                payment_method_types=['card'],
                description=f"Commission Payment for Invoice #{invoice.invoice_number}",
                metadata={'invoice_id': invoice.id, 'role': 'tier1'},
            )

            admin_amount = amount_in_cents
            invoice.transfer_data = {
                'admin_amount': admin_amount
            }
 

        # Save intent ID to the invoice for tracking
        invoice.stripe_payment_intent_id = intent.id
        db.session.commit()
        return jsonify({'client_secret': intent.client_secret}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Stripe Error: {str(e)}'}), 500


# ---------------- STRIPE WEBHOOK (NO CHANGE) ----------------
@billing_bp.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = current_app.config['STRIPE_WEBHOOK_SECRET']

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return 'Invalid payload or signature', 400

    if event['type'] == 'payment_intent.succeeded':
        intent = event['data']['object']
        invoice_id = intent.get('metadata', {}).get('invoice_id')
        if not invoice_id:
            return 'Missing invoice_id in metadata', 400

        with db.session.begin():
            invoice = Invoice.query.filter_by(id=invoice_id).first()
            if invoice and invoice.status != 'paid':
                invoice.status = 'paid'
                invoice.paid_date = date.today()
                if invoice.billing_record:
                    invoice.billing_record.status = 'paid'

                project = invoice.project
                if project and project.tier2_seller_id:
                    handle_tier2_transfers(intent, project, invoice)

    elif event['type'] == 'payment_intent.payment_failed':
        intent = event['data']['object']
        invoice_id = intent.get('metadata', {}).get('invoice_id')
        if invoice_id:
            with db.session.begin():
                invoice = Invoice.query.filter_by(id=invoice_id).first()
                if invoice:
                    invoice.status = 'failed'

    return jsonify({'status': 'success'}), 200


# ---------------- HANDLE TIER-2 TRANSFERS (NO CHANGE) ----------------
def handle_tier2_transfers(payment_intent, project, invoice):
    """Performs post-payment fund transfers for Tier-2 payment (Tier-1 + Admin)."""
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    
    transfer_info = getattr(invoice, 'transfer_data', None)
    if not transfer_info:
        return

    # Use the currency from the payment intent for consistency
    currency = payment_intent.get('currency', 'usd')

    tier1_amount = int(transfer_info.get('tier1_amount', 0))
    admin_amount = int(transfer_info.get('admin_amount', 0))
    # tier1_account = transfer_info.get('tier1_account_id')
    # admin_account = transfer_info.get('admin_account_id')

    source_txn = payment_intent.get('latest_charge')
    transfer_group = payment_intent.get('transfer_group')

    # Tier-1 transfer (after admin deduction)
    # stripe.Transfer.create(
    #     amount=tier1_amount,
    #     currency=currency,
    #     destination=tier1_account,
    #     source_transaction=source_txn,
    #     transfer_group=transfer_group
    # )
    # # Admin transfer
    # stripe.Transfer.create(
    #     amount=admin_amount,
    #     currency=currency,
    #     destination=admin_account,
    #     source_transaction=source_txn,
    #     transfer_group=transfer_group
    # )



# ---------------- NEW: MARK INVOICE AS PAID (FOR LOCAL TESTING) ----------------
@billing_bp.route('/invoice/<invoice_id>/mark-paid', methods=['POST'])
@jwt_required_custom
def mark_invoice_as_paid_manually(invoice_id):
    """
    A temporary endpoint to simulate a successful webhook call for local development.
    Marks an invoice and its billing record as 'paid'.
    """
    invoice = Invoice.query.filter_by(invoice_number=invoice_id).first()
    if not invoice:
        return jsonify({'message': 'Invoice not found'}), 404

    try:
        if invoice.status != 'paid':
            invoice.status = 'paid'
            invoice.paid_date = date.today()
            if invoice.billing_record:
                invoice.billing_record.status = 'paid'
            db.session.commit()
            return jsonify({'message': f'Invoice {invoice_id} marked as paid.'}), 200
        else:
            return jsonify({'message': 'Invoice is already paid.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating invoice: {str(e)}'}), 500





# ---------------- GET ALL BILLS FOR A PROJECT (NO CHANGE) ----------------
@billing_bp.route('/project/<project_id>/bills', methods=['GET'])
@jwt_required_custom
def get_project_bills(project_id):
    # ... this function remains exactly the same
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404
    
    bills = ProjectBilling.query.filter_by(project_id=project_id).order_by(ProjectBilling.created_at.desc()).all()
    
    return jsonify([
        {
            'bill_id': bill.id,
            'amount': float(bill.amount),
            'description': bill.description,
            'status': bill.status,
            'due_date': bill.due_date.isoformat() if bill.due_date else None,
            'invoice_id': bill.invoice.id if bill.invoice else None
        } for bill in bills
    ]), 200

# ---------------- DELETE ALL BILLS (AND INVOICES) FOR A PROJECT (NO CHANGE) ----------------
@billing_bp.route('/project/<project_id>/bills/delete', methods=['DELETE'])
@jwt_required_custom
def delete_project_bills(project_id):
    # ... this function remains exactly the same
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404

    try:
        bills = ProjectBilling.query.filter_by(project_id=project_id).all()
        if not bills:
            return jsonify({'message': 'No bills found for this project'}), 404

        for bill in bills:
            if bill.invoice:
                db.session.delete(bill.invoice)
            db.session.delete(bill)

        db.session.commit()
        return jsonify({'message': f'All bills (and invoices) for project {project_id} have been deleted'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting bills: {str(e)}'}), 500

from sqlalchemy import or_ # <-- 

# ... (all other routes remain the same) ...


# @billing_bp.route('/revenue', methods=['GET'])
# @jwt_required_custom
# def revenue_overview():
#     """
#     Get overall revenue stats + billing details for the dashboard,
#     filtered by the current user's role and permissions.
#     """
#     # --- MODIFICATION START ---

#     # 1. Get the current user's identity and role
#     user_id = get_jwt_identity()
#     current_user = get_current_user(user_id)
#     if not current_user:
#         return jsonify({'message': 'User not found or invalid token'}), 401

#     # Import models here as in the original code
#     from app.models import Admin, Tier1Seller, Tier2Seller

#     # 2. Build the base query to join ProjectBilling with Project
#     base_query = ProjectBilling.query.join(Project, ProjectBilling.project_id == Project.id)

#     # 3. Apply role-based filtering to the query
#     if is_admin(current_user):
#         # Admin sees everything, no additional filters needed.
#         bills = base_query.all()
    
#     elif is_tier1(current_user):
#         # Tier 1 Seller sees their own projects AND projects of Tier 2 sellers they manage.
        
#         # Get IDs of all Tier 2 sellers managed by this Tier 1 seller
#         managed_tier2_ids = [
#             seller.id for seller in Tier2Seller.query.filter_by(tier1_seller_id=current_user['id']).all()
#         ]
        
#         bills = base_query.filter(
#             or_(
#                 Project.tier1_seller_id == current_user['id'],
#                 Project.tier2_seller_id.in_(managed_tier2_ids)
#             )
#         ).all()

#     elif is_tier2(current_user):
#         # Tier 2 Seller sees only their own projects.
#         bills = base_query.filter(Project.tier2_seller_id == current_user['id']).all()
    
#     else:
#         # If user has no recognizable role, return no bills.
#         bills = []
        
#     # --- MODIFICATION END ---

#     # The rest of the function processes the filtered `bills` list
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


# In app/routes/billing.py

# Make sure SubscriptionPlan is imported at the top of the file
from app.models.project import SubscriptionPlan
from sqlalchemy import or_
from decimal import Decimal
from datetime import date

# ... (keep all other routes as they are) ...
# In app/routes/billing.py

# @billing_bp.route('/revenue', methods=['GET'])
# @jwt_required_custom
# def revenue_overview():
#     """
#     Get overall revenue stats + billing details for the dashboard,
#     filtered by the current user's role and permissions.
#     """
#     user_id = get_jwt_identity()
#     current_user = get_current_user(user_id)
#     if not current_user:
#         return jsonify({'message': 'User not found or invalid token'}), 401

#     base_query = db.session.query(ProjectBilling).join(
#         Project, ProjectBilling.project_id == Project.id
#     ).outerjoin(
#         SubscriptionPlan, Project.subscription_plan_id == SubscriptionPlan.id
#     )

#     # --- Role-based filtering (no changes here) ---
#     if is_admin(current_user):
#         bills = base_query.all()
#     elif is_tier1(current_user):
#         managed_tier2_ids = [
#             seller.id for seller in Tier2Seller.query.filter_by(tier1_seller_id=current_user['id']).all()
#         ]
#         bills = base_query.filter(
#             or_(
#                 Project.tier1_seller_id == current_user['id'],
#                 Project.tier2_seller_id.in_(managed_tier2_ids)
#             )
#         ).all()
#     elif is_tier2(current_user):
#         bills = base_query.filter(Project.tier2_seller_id == current_user['id']).all()
#     else:
#         bills = []
    
#     # --- Summary calculation (no changes here) ---
#     # ... (summary logic remains the same)
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

#     # --- MODIFICATION START ---
#     details = []
#     for bill in bills:
#         plan = bill.project.subscription_plan if bill.project else None
#         client_name = bill.project.name if bill.project else "Unknown"
        
#         # Default values
#         project_value = float(bill.amount) # Fallback to bill amount if no plan
#         commission_pct = None
#         commission_amount = 0

#         if plan:
#             # 1. "Project Value" is now the plan's base price
#             base_price = Decimal(plan.price)
#             project_value = float(base_price)
            
#             # 2. Determine the correct commission percentage based on user role
#             pct_to_use = None
#             if is_tier2(current_user) and plan.tier1_commission_pct is not None:
#                 pct_to_use = Decimal(plan.tier1_commission_pct)
#             elif is_tier1(current_user) and plan.admin_commission_pct is not None:
#                 pct_to_use = Decimal(plan.admin_commission_pct)
#             elif is_admin(current_user) and plan.admin_commission_pct is not None:
#                 pct_to_use = Decimal(plan.admin_commission_pct)

#             # 3. "Amount" is now the commission calculated from the base price
#             if pct_to_use is not None:
#                 commission_pct = float(pct_to_use)
#                 commission_amount = float(base_price * (pct_to_use / 100))

#         details.append({
#             "client_name": client_name,
#             "invoice_id": bill.invoice.invoice_number if bill.invoice else None,
            
#             # Updated fields to match your new logic
#             "project_value": project_value,         # Changed from bill_amount
#             "commission_percentage": commission_pct,
#             "commission_amount": commission_amount, # Now based on plan price
            
#             "due_date": bill.due_date.isoformat() if bill.due_date else None,
#             "status": (
#                 "Overdue" if bill.status in ["pending", "invoiced"] and bill.due_date and bill.due_date < date.today()
#                 else bill.status.capitalize()
#             ),
#             "payment_date": bill.invoice.paid_date.isoformat() if (bill.invoice and bill.invoice.paid_date) else None,
#         })
#     # --- MODIFICATION END ---

#     return jsonify({
#         "summary": summary,
#         "billing_details": details
#     }), 200

# In app/routes/billing.py

# In app/routes/billing.py

# Make sure all necessary models and libraries are imported at the top of the file
# In app/routes/billing.py

# In app/routes/billing.py

from app.models.project import SubscriptionPlan, Project
from app.models.billing import ProjectBilling
from app.models.seller import Tier1Seller, Tier2Seller
from sqlalchemy import or_
from decimal import Decimal
from datetime import date
from app import db 
from app.routes.projects import get_current_user, get_jwt_identity, is_admin, is_tier1, is_tier2
from app.utils.auth import jwt_required_custom

@billing_bp.route('/revenue', methods=['GET'])
@jwt_required_custom
def revenue_overview():
    """
    Get overall revenue stats + billing details for the dashboard,
    filtered by the current user's role and permissions.
    """
    user_id = get_jwt_identity()
    current_user = get_current_user(user_id)
    if not current_user:
        return jsonify({'message': 'User not found or invalid token'}), 401

    # --- UPDATED QUERY to include joins for seller names ---
    base_query = db.session.query(
        ProjectBilling, Project, SubscriptionPlan, Tier1Seller, Tier2Seller
    ).select_from(ProjectBilling).join(
        Project, ProjectBilling.project_id == Project.id
    ).outerjoin(
        SubscriptionPlan, Project.subscription_plan_id == SubscriptionPlan.id
    ).outerjoin(
        Tier1Seller, Project.tier1_seller_id == Tier1Seller.id
    ).outerjoin(
        Tier2Seller, Project.tier2_seller_id == Tier2Seller.id
    )

    # --- Logic for Tier 1 Seller ---
    if is_tier1(current_user):
        tier1_project_details = []
        tier2_project_details = []

        managed_tier2_ids = [
            seller.id for seller in Tier2Seller.query.filter_by(tier1_seller_id=user_id).all()
        ]
        
        related_bills_query = base_query.filter(
            or_(
                Project.tier1_seller_id == user_id,
                Project.tier2_seller_id.in_(managed_tier2_ids)
            )
        )
        
        for bill, project, plan, t1_seller, t2_seller in related_bills_query.all():
            detail_data = {
                "client_name": project.name if project else "Unknown",
                "invoice_id": bill.invoice.invoice_number if bill.invoice else None,
                "project_value": 0, "commission_percentage": None, "commission_amount": 0,
                "due_date": bill.due_date.isoformat() if bill.due_date else None,
                "status": ("Overdue" if bill.status in ["pending", "invoiced"] and bill.due_date and bill.due_date < date.today() else bill.status.capitalize()),
                "payment_date": bill.invoice.paid_date.isoformat() if (bill.invoice and bill.invoice.paid_date) else None,
                "admin_commission_percentage": None, "admin_commission_amount": 0
            }

            if plan:
                base_price = Decimal(plan.price)
                detail_data["project_value"] = float(base_price)

                if project.tier1_seller_id == user_id and not project.tier2_seller_id:
                    if plan.admin_commission_pct is not None:
                        pct = Decimal(plan.admin_commission_pct)
                        detail_data["commission_percentage"] = float(pct)
                        detail_data["commission_amount"] = float(base_price * (pct / 100))
                    tier1_project_details.append(detail_data)
                
                elif project.tier2_seller_id in managed_tier2_ids:
                    tier1_commission_earned = Decimal('0.0')
                    if plan.tier1_commission_pct is not None:
                        pct = Decimal(plan.tier1_commission_pct)
                        detail_data["commission_percentage"] = float(pct)
                        tier1_commission_earned = base_price * (pct / 100)
                        detail_data["commission_amount"] = float(tier1_commission_earned)
                    
                    if plan.admin_commission_pct is not None:
                        admin_pct = Decimal(plan.admin_commission_pct)
                        detail_data["admin_commission_percentage"] = float(admin_pct)
                        admin_commission_to_pay = tier1_commission_earned * (admin_pct / 100)
                        detail_data["admin_commission_amount"] = float(admin_commission_to_pay)
                    tier2_project_details.append(detail_data)

        return jsonify({
            "tier1_project_billing": tier1_project_details,
            "tier2_project_billing": tier2_project_details
        }), 200

    # --- Logic for Admin ---
    elif is_admin(current_user):
        bills_result = base_query.all()
        direct_revenue_details = []
        indirect_revenue_details = []

        for bill, project, plan, t1_seller, t2_seller in bills_result:
            detail_data = {
                "client_name": project.name if project else "Unknown",
                "invoice_id": bill.invoice.invoice_number if bill.invoice else None,
                "project_value": 0,
                "due_date": bill.due_date.isoformat() if bill.due_date else None,
                "status": ("Overdue" if bill.status in ["pending", "invoiced"] and bill.due_date and bill.due_date < date.today() else bill.status.capitalize()),
                "payment_date": bill.invoice.paid_date.isoformat() if (bill.invoice and bill.invoice.paid_date) else None,
            }

            if plan:
                base_price = Decimal(plan.price)
                detail_data["project_value"] = float(base_price)

                if project.tier1_seller_id and not project.tier2_seller_id:
                    detail_data["seller_name"] = t1_seller.name if t1_seller else "N/A"
                    if plan.admin_commission_pct is not None:
                        pct = Decimal(plan.admin_commission_pct)
                        detail_data["commission_percentage"] = float(pct)
                        detail_data["commission_amount"] = float(base_price * (pct / 100))
                    direct_revenue_details.append(detail_data)

                elif project.tier2_seller_id:
                    detail_data["tier1_seller_name"] = t1_seller.name if t1_seller else "N/A"
                    detail_data["tier2_seller_name"] = t2_seller.name if t2_seller else "N/A"
                    tier1_commission_earned = Decimal('0.0')
                    
                    if plan.tier1_commission_pct is not None:
                        t1_pct = Decimal(plan.tier1_commission_pct)
                        tier1_commission_earned = base_price * (t1_pct / 100)
                        detail_data["tier1_commission_amount"] = float(tier1_commission_earned)

                    if plan.admin_commission_pct is not None:
                        admin_pct = Decimal(plan.admin_commission_pct)
                        admin_share = tier1_commission_earned * (admin_pct / 100)
                        detail_data["admin_commission_amount"] = float(admin_share)
                    indirect_revenue_details.append(detail_data)
        
        return jsonify({
            "summary": { "total_bills": len(bills_result) },
            "direct_revenue_details": direct_revenue_details,
            "indirect_revenue_details": indirect_revenue_details
        }), 200

    # --- Logic for Tier 2 Seller ---
    elif is_tier2(current_user):
        bills_result = base_query.filter(Project.tier2_seller_id == user_id).all()
        
        summary = { "total_bills": len(bills_result) }
        details = []
        for bill, project, plan, t1_seller, t2_seller in bills_result:
            project_value = float(bill.amount)
            commission_pct = None
            commission_amount = 0

            if plan:
                base_price = Decimal(plan.price)
                project_value = float(base_price)
                if plan.tier1_commission_pct is not None:
                    pct_to_use = Decimal(plan.tier1_commission_pct)
                    commission_pct = float(pct_to_use)
                    commission_amount = float(base_price * (pct_to_use / 100))

            details.append({
                "client_name": project.name if project else "Unknown",
                "invoice_id": bill.invoice.invoice_number if bill.invoice else None,
                "project_value": project_value,
                "commission_percentage": commission_pct,
                "commission_amount": commission_amount,
                "due_date": bill.due_date.isoformat() if bill.due_date else None,
                "status": ("Overdue" if bill.status in ["pending", "invoiced"] and bill.due_date and bill.due_date < date.today() else bill.status.capitalize()),
                "payment_date": bill.invoice.paid_date.isoformat() if (bill.invoice and bill.invoice.paid_date) else None,
            })
        
        return jsonify({ "summary": summary, "billing_details": details }), 200
    
    # Fallback for any other user type
    else:
        return jsonify({ "summary": {}, "billing_details": [] }), 200