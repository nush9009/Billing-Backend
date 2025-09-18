from flask import Blueprint, jsonify
from app import db
from app.models import Tier1Seller, Tier2Seller, Admin, Project
from app.models.billing import Invoice
from app.utils.auth import admin_required,jwt_required_custom
from datetime import date
from sqlalchemy import or_
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_admin_dashboard():
    """Provides a complete overview of the system for the admin."""
    try:
        # Counts
        total_tier1 = Tier1Seller.query.count()
        total_tier2 = Tier2Seller.query.count()
        total_projects = Project.query.count()
    

        # Monthly Revenue (sum of paid invoices issued this month)
        today = date.today()
        monthly_invoices = Invoice.query.filter(
            db.extract('year', Invoice.paid_date) == today.year,
            db.extract('month', Invoice.paid_date) == today.month,
            Invoice.status == 'paid'
        ).all()

        monthly_revenue = sum(float(inv.total_amount) for inv in monthly_invoices)

        return jsonify({
            'stats': {
                'total_tier1_sellers': total_tier1,
                'total_tier2_sellers': total_tier2,
                'total_projects': total_projects,
                'monthly_revenue': monthly_revenue
            }
        }), 200

    except Exception as e:
        return jsonify({'message': f'Error fetching admin data: {str(e)}'}), 500



@admin_bp.route('/dashboard/tier1/<tier1_id>', methods=['GET'])
@jwt_required_custom
def get_tier1_dashboard(tier1_id):
    """
    Provides an overview for a specific Tier1 seller with updated logic.
    - Monthly Revenue: Sum of paid invoices from their associated Tier 2 sellers.
    - Total Projects: Count of projects assigned ONLY to the Tier 1 seller.
    """
    try:
        # --- Total Tier 2 sellers count remains the same ---
        total_tier2 = Tier2Seller.query.filter_by(tier1_seller_id=tier1_id).count()

        # --- MODIFIED: Count only projects assigned to Tier 1, not delegated ---
        total_projects = Project.query.filter_by(
            tier1_seller_id=tier1_id, 
            tier2_seller_id=None  # This ensures we only count projects not assigned to a Tier 2
        ).count()

        # --- CORRECT: Revenue from Tier 2 sellers' paid bills ---
        # 1. Get all Tier 2 seller IDs managed by this Tier 1 seller
        tier2_seller_ids = [
            seller.id for seller in Tier2Seller.query.filter_by(tier1_seller_id=tier1_id).all()
        ]

        monthly_revenue = 0
        # 2. Only calculate revenue if there are associated Tier 2 sellers
        if tier2_seller_ids:
            today = date.today()
            # 3. Sum paid invoices for projects assigned to those Tier 2 sellers
            monthly_invoices = (
                Invoice.query.join(Project, Invoice.project_id == Project.id)
                .filter(
                    Project.tier2_seller_id.in_(tier2_seller_ids),
                    db.extract('year', Invoice.paid_date) == today.year,
                    db.extract('month', Invoice.paid_date) == today.month,
                    Invoice.status == 'paid'
                )
                .all()
            )
            monthly_revenue = sum(float(inv.total_amount) for inv in monthly_invoices)

        return jsonify({
            'stats': {
                'tier1_seller_id': tier1_id,
                'total_tier2_sellers': total_tier2,
                'total_projects': total_projects,
                'monthly_revenue': monthly_revenue
            }
        }), 200
       
    except Exception as e:
        return jsonify({'message': f'Error fetching Tier1 dashboard: {str(e)}'}), 500

# # In your admin blueprint file (e.g., admin.py)
# from sqlalchemy import or_ # <-- Make sure to import or_
# from datetime import date
# # ... other necessary imports

# @admin_bp.route('/dashboard/tier1/<tier1_id>', methods=['GET'])
# @jwt_required_custom
# def get_tier1_dashboard(tier1_id):
#     """Provides overview of the system for a specific Tier1 seller (admin view)."""
#     try:
#         # --- CORRECTED LOGIC FOR COUNTS AND REVENUE ---

#         # 1. Find all Tier 2 sellers that belong to this Tier 1 seller.
#         managed_tier2_ids = [
#             seller.id for seller in Tier2Seller.query.filter_by(tier1_seller_id=tier1_id).all()
#         ]

#         # 2. Correctly count total projects (Tier 1's own + their Tier 2's projects)
#         total_projects = Project.query.filter(
#             or_(
#                 Project.tier1_seller_id == tier1_id,
#                 Project.tier2_seller_id.in_(managed_tier2_ids)
#             )
#         ).count()

#         # 3. This count is correct as is.
#         total_tier2 = len(managed_tier2_ids)

#         # 4. Correctly calculate monthly revenue (from Tier 1's own + their Tier 2's projects)
#         today = date.today()
#         monthly_invoices = (
#             Invoice.query.join(Project, Invoice.project_id == Project.id)
#             .filter(
#                 or_( # Use the same OR condition here
#                     Project.tier1_seller_id == tier1_id,
#                     Project.tier2_seller_id.in_(managed_tier2_ids)
#                 ),
#                 db.extract('year', Invoice.paid_date) == today.year,
#                 db.extract('month', Invoice.paid_date) == today.month,
#                 Invoice.status == 'paid'
#             )
#             .all()
#         )
#         monthly_revenue = sum(float(inv.total_amount) for inv in monthly_invoices)

#         # --- END OF CORRECTION ---

#         return jsonify({
#             'stats': {
#                 'tier1_seller_id': tier1_id,
#                 'total_tier2_sellers': total_tier2,
#                 'total_projects': total_projects,
#                 'monthly_revenue': monthly_revenue
#             }
#         }), 200
       
#     except Exception as e:
#         return jsonify({'message': f'Error fetching Tier1 dashboard: {str(e)}'}), 500


# Add this endpoint after your get_tier1_dashboard function

@admin_bp.route('/dashboard/tier2/<tier2_id>', methods=['GET'])
@jwt_required_custom  # Assuming a logged-in tier2 seller can access their own data
def get_tier2_dashboard(tier2_id):
    """Provides an overview for a specific Tier-2 seller."""
    try:
        # 1. Count total projects for this Tier-2 seller
        total_projects = Project.query.filter_by(tier2_seller_id=tier2_id).count()

        # 2. Calculate monthly revenue for this Tier-2 seller
        today = date.today()
        monthly_invoices = (
            Invoice.query
            .join(Project, Invoice.project_id == Project.id)
            .filter(
                Project.tier2_seller_id == tier2_id,
                db.extract('year', Invoice.paid_date) == today.year,
                db.extract('month', Invoice.paid_date) == today.month,
                Invoice.status == 'paid'
            )
            .all()
        )

        monthly_revenue = sum(float(inv.total_amount) for inv in monthly_invoices)

        return jsonify({
            'stats': {
                'tier2_seller_id': tier2_id,
                'total_projects': total_projects,
                'monthly_revenue': monthly_revenue
            }
        }), 200

    except Exception as e:
        return jsonify({'message': f'Error fetching Tier-2 dashboard: {str(e)}'}), 500