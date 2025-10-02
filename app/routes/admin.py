from flask import Blueprint, jsonify
from app import db
from app.models import Tier1Seller, Tier2Seller, Admin, Project
from app.models.billing import Invoice
from app.utils.auth import admin_required,jwt_required_custom
from datetime import date
from sqlalchemy import or_
admin_bp = Blueprint('admin', __name__)
# Make sure to import these models at the top of your admin routes file
from app.models.billing import ProjectBilling, Invoice
from app.models.project import SubscriptionPlan
from app.models.seller import Tier1Seller, Tier2Seller
from app.models import Project
from decimal import Decimal
from datetime import date
from app import db
from app.utils.auth import admin_required # Assuming you have this decorator

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_admin_dashboard():
    """Provides a complete, commission-based overview of the system for the admin."""
    try:
        # --- 1. Counts (No changes needed) ---
        total_tier1 = Tier1Seller.query.count()
        total_tier2 = Tier2Seller.query.count()
        total_projects = Project.query.count()
    
        # --- 2. NEW: Commission-based Monthly Revenue Calculation ---
        monthly_revenue = Decimal('0.0')
        today = date.today()

        # Find all bills that were paid in the current month
        paid_bills_this_month = db.session.query(ProjectBilling).join(
            Invoice, ProjectBilling.id == Invoice.billing_record_id
        ).filter(
            db.extract('year', Invoice.paid_date) == today.year,
            db.extract('month', Invoice.paid_date) == today.month,
            Invoice.status == 'paid'
        ).all()

        for bill in paid_bills_this_month:
            plan = bill.project.subscription_plan
            
            if plan and plan.admin_commission_pct is not None:
                base_price = Decimal(plan.price)
                admin_pct = Decimal(plan.admin_commission_pct)

                # Case A: Commission from a Tier-1 seller's direct project
                if bill.project.tier1_seller_id and not bill.project.tier2_seller_id:
                    admin_commission = base_price * (admin_pct / 100)
                    monthly_revenue += admin_commission
                
                # Case B: Admin's share of commission from a Tier-2 seller's project
                elif bill.project.tier2_seller_id and plan.tier1_commission_pct is not None:
                    tier1_pct = Decimal(plan.tier1_commission_pct)
                    
                    # First, find the commission the Tier-1 seller earned
                    tier1_commission_earned = base_price * (tier1_pct / 100)
                    # Then, find the admin's share of that commission
                    admin_share = tier1_commission_earned * (admin_pct / 100)
                    monthly_revenue += admin_share

        return jsonify({
            'stats': {
                'total_tier1_sellers': total_tier1,
                'total_tier2_sellers': total_tier2,
                'total_projects': total_projects,
                'monthly_revenue': float(monthly_revenue)
            }
        }), 200

    except Exception as e:
        return jsonify({'message': f'Error fetching admin data: {str(e)}'}), 500


# Make sure to import these models at the top of your admin routes file
from app.models.billing import ProjectBilling, Invoice
from app.models.project import SubscriptionPlan
from app.models.seller import Tier2Seller
from app.models import Project # Ensure Project is imported
from decimal import Decimal
from datetime import date
from app import db # Ensure db is imported

@admin_bp.route('/dashboard/tier1/<tier1_id>', methods=['GET'])
@jwt_required_custom
def get_tier1_dashboard(tier1_id):
    """
    Provides a dashboard overview for a specific Tier-1 seller based on commission logic.
    """
    try:
        # --- 1. Total Tier 2 sellers and Total Projects (No changes needed) ---
        total_tier2 = Tier2Seller.query.filter_by(tier1_seller_id=tier1_id).count()
        total_projects = Project.query.filter_by(
            tier1_seller_id=tier1_id, 
            tier2_seller_id=None
        ).count()

        # --- 2. Calculate Total Revenue (Commission received from PAID Tier 2 seller bills) ---
        tier2_seller_ids = [
            seller.id for seller in Tier2Seller.query.filter_by(tier1_seller_id=tier1_id).all()
        ]
        
        total_revenue_from_tier2 = Decimal('0.0')
        tier2_bills = []
        if tier2_seller_ids:
            tier2_bills = db.session.query(ProjectBilling).join(
                Project, ProjectBilling.project_id == Project.id
            ).filter(
                Project.tier2_seller_id.in_(tier2_seller_ids)
            ).all()

            for bill in tier2_bills:
                if bill.status == 'paid':
                    plan = bill.project.subscription_plan
                    if plan and plan.tier1_commission_pct is not None:
                        base_price = Decimal(plan.price)
                        commission_pct = Decimal(plan.tier1_commission_pct)
                        total_revenue_from_tier2 += base_price * (commission_pct / 100)

        # --- 3. Calculate Paid and Pending Commission (Owed to Admin) ---
        total_paid_to_admin = Decimal('0.0')
        pending_amount_to_admin = Decimal('0.0')

        # Part A: Commission from the Tier 1 seller's own projects
        tier1_own_bills = db.session.query(ProjectBilling).join(
            Project, ProjectBilling.project_id == Project.id
        ).filter(
            Project.tier1_seller_id == tier1_id,
            Project.tier2_seller_id == None
        ).all()

        for bill in tier1_own_bills:
            plan = bill.project.subscription_plan
            if plan and plan.admin_commission_pct is not None:
                base_price = Decimal(plan.price)
                commission_pct = Decimal(plan.admin_commission_pct)
                commission_amount = base_price * (commission_pct / 100)

                if bill.status == 'paid':
                    total_paid_to_admin += commission_amount
                elif bill.status in ['pending', 'invoiced']:
                    pending_amount_to_admin += commission_amount

        # --- NEW LOGIC ---
        # Part B: Admin's share of the commission from Tier 2 seller projects
        for bill in tier2_bills:
            plan = bill.project.subscription_plan
            if plan and plan.tier1_commission_pct is not None and plan.admin_commission_pct is not None:
                base_price = Decimal(plan.price)
                tier1_pct = Decimal(plan.tier1_commission_pct)
                admin_pct = Decimal(plan.admin_commission_pct)

                # First, find the commission the Tier 1 earned
                tier1_commission_earned = base_price * (tier1_pct / 100)
                # Then, find the admin's share of that commission
                admin_share = tier1_commission_earned * (admin_pct / 100)

                if bill.status == 'paid':
                    total_paid_to_admin += admin_share
                elif bill.status in ['pending', 'invoiced']:
                    pending_amount_to_admin += admin_share


        return jsonify({
            'stats': {
                'tier1_seller_id': tier1_id,
                'total_tier2_sellers': total_tier2,
                'total_projects': total_projects,
                'total_revenue': float(total_revenue_from_tier2),
                'total_paid': float(total_paid_to_admin),
                'pending_amount': float(pending_amount_to_admin)
            }
        }), 200
       
    except Exception as e:
        return jsonify({'message': f'Error fetching Tier1 dashboard: {str(e)}'}), 500

# You will need to import these models at the top of your routes file
from app.models.billing import ProjectBilling
from app.models.project import SubscriptionPlan
from decimal import Decimal

@admin_bp.route('/dashboard/tier2/<tier2_id>', methods=['GET'])
@jwt_required_custom
def get_tier2_dashboard(tier2_id):
    """
    Provides a dashboard overview for a specific Tier-2 seller, 
    calculating paid and pending commissions owed to their Tier-1 parent.
    """
    try:
        # 1. Get all billing records for the Tier-2 seller's projects
        bills = db.session.query(ProjectBilling).join(
            Project, ProjectBilling.project_id == Project.id
        ).filter(Project.tier2_seller_id == tier2_id).all()

        total_projects = Project.query.filter_by(tier2_seller_id=tier2_id).count()
        paid_commission = Decimal('0.0')
        pending_commission = Decimal('0.0')

        # 2. Iterate through each bill to calculate commission
        for bill in bills:
            plan = bill.project.subscription_plan
            
            # Proceed only if the project has a plan with T1 commission
            if plan and plan.tier1_commission_pct is not None:
                base_price = Decimal(plan.price)
                commission_pct = Decimal(plan.tier1_commission_pct)
                
                # Calculate the commission amount from the plan's base price
                commission_amount = base_price * (commission_pct / 100)

                # 3. Add the commission to the correct bucket based on status
                if bill.status == 'paid':
                    paid_commission += commission_amount
                elif bill.status in ['pending', 'invoiced']:
                    pending_commission += commission_amount
        
        return jsonify({
            'stats': {
                'tier2_seller_id': tier2_id,
                'total_projects': total_projects,
                'paid_amount': float(paid_commission),
                'pending_amount': float(pending_commission)
            }
        }), 200

    except Exception as e:
        # It's helpful to log the error for debugging
        # import logging
        # logging.error(f"Error fetching Tier-2 dashboard: {str(e)}")
        return jsonify({'message': f'Error fetching Tier-2 dashboard: {str(e)}'}), 500