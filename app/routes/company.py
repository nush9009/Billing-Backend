from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from app import db, bcrypt
# UPDATED: Import the new, renamed models
from app.models import Tier1Seller, Tier2Seller, Admin, Project, User

company_bp = Blueprint('company', __name__)

@company_bp.route('/<company>/info', methods=['GET'])
def get_company_info(company):
    """Get company information based on subdomain, updated for new models."""
    # UPDATED: Query the Tier1Seller model instead of Seller
    tier1_seller = Tier1Seller.query.filter_by(subdomain=company).first()
    tier2_seller = Tier2Seller.query.filter_by(subdomain=company).first()
    
    if tier1_seller:
        # UPDATED: Query Admins (formerly Clients) linked to this Tier1Seller
        admins = Admin.query.filter_by(tier1_seller_id=tier1_seller.id).all()
        admin_names = [admin.name for admin in admins]
        
        return jsonify({
            'id': tier1_seller.id,
            'name': tier1_seller.name,
            'subdomain': tier1_seller.subdomain,
            'type': 'tier1_seller',
            'color': '#3B82F6',  # Blue for tier1
            'clients': admin_names, # 'clients' here refers to the Admins they manage
            'hasAdmin': True,
            'description': f'Tier-1 seller with {len(admins)} clients'
        }), 200
    
    elif tier2_seller:
        # UPDATED: Query Admins linked to this Tier2Seller
        admins = Admin.query.filter_by(tier2_seller_id=tier2_seller.id).all()
        admin_names = [admin.name for admin in admins]
        
        return jsonify({
            'id': tier2_seller.id,
            'name': tier2_seller.name,
            'subdomain': tier2_seller.subdomain,
            'type': 'tier2_seller',
            'color': '#10B981',  # Green for tier2
            'clients': admin_names,
            'hasAdmin': True,
            'description': f'Tier-2 seller with {len(admins)} clients'
        }), 200
    
    # Check if it's the root admin company
    elif company in ['admin', 'jupiterbrains']:
        # UPDATED: The "clients" of the root admin are all other Tier1Sellers
        all_tier1_sellers = Tier1Seller.query.filter(Tier1Seller.subdomain != 'admin').all()
        return jsonify({
            'id': 'admin',
            'name': 'JupiterBrains',
            'subdomain': 'admin',
            'type': 'root_admin',
            'color': '#8B5CF6',  # Purple for admin
            'clients': [s.name for s in all_tier1_sellers],
            'hasAdmin': True,
            'description': 'Root administrator managing all sellers'
        }), 200
    
    return jsonify({'message': 'Company not found'}), 404

@company_bp.route('/<company>/clients', methods=['GET'])
def get_company_clients(company):
    """Get list of clients (Admins) for a company, updated for new models."""
    # UPDATED: Query Tier1Seller
    tier1_seller = Tier1Seller.query.filter_by(subdomain=company).first()
    tier2_seller = Tier2Seller.query.filter_by(subdomain=company).first()
    
    if tier1_seller:
        # UPDATED: Query Admins linked to the Tier1Seller
        admins = Admin.query.filter_by(tier1_seller_id=tier1_seller.id).all()
        admin_names = [admin.name for admin in admins]
        return jsonify(admin_names), 200
    
    elif tier2_seller:
        # UPDATED: Query Admins linked to the Tier2Seller
        admins = Admin.query.filter_by(tier2_seller_id=tier2_seller.id).all()
        admin_names = [admin.name for admin in admins]
        return jsonify(admin_names), 200
    
    return jsonify([]), 200

@company_bp.route('/client/<admin_name>/config', methods=['GET'])
def get_client_config(admin_name):
    """Get client (Admin) configuration, updated for new models."""
    # UPDATED: Query the Admin model by name
    admin = Admin.query.filter_by(name=admin_name).first()
    
    if not admin:
        return jsonify({'message': 'Admin account not found'}), 404
    
    # Theme generation logic remains the same, but uses the admin_name
    theme_configs = {
        'John Smith (Admin)': {'bgPattern': 'dots', 'accentColor': '#3B82F6', 'icon': '🏢'},
        'Jane Doe (Admin)': {'bgPattern': 'grid', 'accentColor': '#10B981', 'icon': '📊'},
    }
    default_theme = {'bgPattern': 'dots', 'accentColor': '#6B7280', 'icon': '🏢'}
    theme = theme_configs.get(admin_name, default_theme)
    
    return jsonify({
        'id': admin.id,
        'name': admin.name,
        'company': admin.company,
        'tagline': f'Professional services for {admin.company}',
        'description': f'Comprehensive business solutions and consulting services for {admin.company}',
        'theme_config': theme
    }), 200

@company_bp.route('/client/<admin_name>/login', methods=['POST'])
def authenticate_client(admin_name):
    """Client-specific authentication, updated for new models."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'message': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401
    
    # UPDATED: Verify the user belongs to the correct Admin entity
    admin = Admin.query.get(user.client_id)
    if not admin or admin.name != admin_name:
        return jsonify({'message': 'Invalid credentials or user does not belong to this company'}), 401
    
    # UPDATED: Use the bcrypt object from the app context
    if bcrypt.check_password_hash(user.password_hash, password):
        user_data = {
            'id': user.id,
            'email': email,
            'name': user.name,
            'user_type': 'client', # This refers to the 'Client Portal User'
            'company': admin.company,
            'client_id': admin.id # This is the ID of the Admin record
        }
        
        access_token = create_access_token(identity=user_data)
        return jsonify({
            'token': access_token,
            'user': user_data
        }), 200
    
    return jsonify({'message': 'Invalid credentials'}), 401
