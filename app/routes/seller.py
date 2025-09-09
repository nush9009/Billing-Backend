from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, bcrypt
# UPDATED: Import the new, renamed models
from app.models import Tier1Seller, Tier2Seller, Admin, Project, Commission, User
from app.utils.auth import jwt_required_custom
from datetime import datetime

seller_bp = Blueprint('seller', __name__)

# UPDATED: Added explicit 'endpoint' names to prevent conflicts
@seller_bp.route('/tier2-sellers', methods=['POST'], endpoint='add_tier2_seller')
@jwt_required_custom
def add_tier2_seller():
    """Allows a logged-in Tier1Seller to add a new Tier2Seller."""
    current_user = get_jwt_identity()
    
    if current_user.get('role') != 'tier1_seller':
        return jsonify({'message': 'Tier 1 Seller access required'}), 403
    
    data = request.get_json()
    # ... (rest of the logic is the same)
    password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    new_tier2_seller = Tier2Seller(
        tier1_seller_id=current_user.get('id'),
        name=data['name'],
        subdomain=data['subdomain'],
        admin_email=data['admin_email'],
        password_hash=password_hash
    )
    db.session.add(new_tier2_seller)
    db.session.commit()
    return jsonify({'message': 'Tier-2 Seller created successfully'}), 201

@seller_bp.route('/admins/<admin_id>', methods=['DELETE'], endpoint='delete_admin_by_seller')
@jwt_required_custom
def delete_admin(admin_id):
    """Allows a Tier1Seller to soft-delete an Admin they own."""
    current_user = get_jwt_identity()
    admin = Admin.query.get(admin_id)

    if not admin:
        return jsonify({'message': 'Admin account not found'}), 404
    
    # Verify the logged-in Tier1Seller owns this Admin
    if current_user.get('role') == 'tier1_seller' and admin.tier1_seller_id == current_user.get('id'):
        try:
            admin.status = 'inactive'
            db.session.commit()
            return jsonify({'message': 'Admin account deleted successfully'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': str(e)}), 500

    return jsonify({'message': 'Access denied'}), 403


@seller_bp.route('/dashboard', methods=['GET'], endpoint='get_seller_dashboard')
@jwt_required_custom
def get_comprehensive_seller_dashboard():
    """Provides dashboard data for a logged-in Tier1 or Tier2 seller."""
    current_user = get_jwt_identity()
    user_id = current_user.get('id')
    user_role = current_user.get('role')

    # ... (rest of dashboard logic using Admin and Tier1Seller models)
    if user_role == 'tier1_seller':
        seller = Tier1Seller.query.get(user_id)
        admins = Admin.query.filter_by(tier1_seller_id=user_id).all()
        tier2s = Tier2Seller.query.filter_by(tier1_seller_id=user_id).all()
    elif user_role == 'tier2_seller':
        seller = Tier2Seller.query.get(user_id)
        admins = Admin.query.filter_by(tier2_seller_id=user_id).all()
        tier2s = []
    else:
        return jsonify({'message': 'Access denied'}), 403

    if not seller:
        return jsonify({'message': 'Seller account not found'}), 404

    # The rest of your comprehensive dashboard logic can go here.
    # This is a simplified version for now.
    return jsonify({
        'sellerData': {
            'id': seller.id,
            'name': seller.name,
            'type': user_role,
            'total_clients': len(admins)
        },
        'clients': [{'id': a.id, 'name': a.name, 'company': a.company} for a in admins],
        'tier2_sellers': [{'id': t2.id, 'name': t2.name} for t2 in tier2s]
    }), 200

