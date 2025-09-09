from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, bcrypt
# UPDATED: Import the new models
from app.models import Tier1Seller, Tier2Seller, Admin, Project
from app.utils.auth import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/sellers', methods=['POST'])
@admin_required
def add_tier1_seller():
    """Add new Tier-1 seller - Accessible only by an admin."""
    data = request.get_json()
    
    required_fields = ['name', 'subdomain', 'admin_email', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Missing required fields'}), 400
    
    if Tier1Seller.query.filter((Tier1Seller.subdomain == data['subdomain']) | (Tier1Seller.admin_email == data['admin_email'])).first():
        return jsonify({'message': 'Subdomain or email already exists'}), 400
    
    try:
        password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        # UPDATED: Create a Tier1Seller object
        new_seller = Tier1Seller(
            name=data['name'],
            subdomain=data['subdomain'],
            admin_email=data['admin_email'],
            password_hash=password_hash,
            role='tier1_seller' # Explicitly set role
        )
        db.session.add(new_seller)
        db.session.commit()
        return jsonify({'message': 'Tier-1 Seller created successfully', 'seller_id': new_seller.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating seller: {str(e)}'}), 500

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_admin_dashboard():
    """Provides a complete overview of the system for the admin."""
    try:
        # UPDATED: Query the new models
        tier1_sellers = Tier1Seller.query.filter_by(role='tier1_seller').all()
        tier2_sellers = Tier2Seller.query.all()
        admins = Admin.query.all()
        projects = Project.query.all()
        
        return jsonify({
            'stats': {
                'total_tier1_sellers': len(tier1_sellers),
                'total_tier2_sellers': len(tier2_sellers),
                'total_admins': len(admins),
                'total_projects': len(projects),
            }
        }), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching admin data: {str(e)}'}), 500
