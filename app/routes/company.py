from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Seller, Tier2Seller, Client, Project, User
from app.utils.auth import jwt_required_custom
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token

company_bp = Blueprint('company', __name__)

@company_bp.route('/<company>/info', methods=['GET'])
def get_company_info(company):
    """Get company information"""
    # Map company subdomain to actual company
    seller = Seller.query.filter_by(subdomain=company).first()
    tier2_seller = Tier2Seller.query.filter_by(subdomain=company).first()
    
    if seller:
        # Get clients under this seller
        clients = Client.query.filter_by(seller_id=seller.id).all()
        client_names = [client.name for client in clients]
        
        return jsonify({
            'id': seller.id,
            'name': seller.name,
            'subdomain': seller.subdomain,
            'type': 'tier1_seller',
            'color': '#3B82F6',  # Blue for tier1
            'clients': client_names,
            'hasAdmin': True,
            'description': f'Tier-1 seller with {len(clients)} clients'
        }), 200
    
    elif tier2_seller:
        clients = Client.query.filter_by(tier2_seller_id=tier2_seller.id).all()
        client_names = [client.name for client in clients]
        
        return jsonify({
            'id': tier2_seller.id,
            'name': tier2_seller.name,
            'subdomain': tier2_seller.subdomain,
            'type': 'tier2_seller',
            'color': '#10B981',  # Green for tier2
            'clients': client_names,
            'hasAdmin': True,
            'description': f'Tier-2 seller with {len(clients)} clients'
        }), 200
    
    # Check if it's admin company
    elif company in ['admin', 'jupiterbrains']:
        all_sellers = Seller.query.all()
        return jsonify({
            'id': 'admin',
            'name': 'JupiterBrains',
            'subdomain': 'admin',
            'type': 'root_admin',
            'color': '#8B5CF6',  # Purple for admin
            'clients': [seller.name for seller in all_sellers],
            'hasAdmin': True,
            'description': 'Root administrator managing all sellers'
        }), 200
    
    return jsonify({'message': 'Company not found'}), 404

@company_bp.route('/<company>/clients', methods=['GET'])
def get_company_clients(company):
    """Get list of clients for a company"""
    seller = Seller.query.filter_by(subdomain=company).first()
    tier2_seller = Tier2Seller.query.filter_by(subdomain=company).first()
    
    if seller:
        clients = Client.query.filter_by(seller_id=seller.id).all()
        client_names = [client.name for client in clients]
        return jsonify(client_names), 200
    
    elif tier2_seller:
        clients = Client.query.filter_by(tier2_seller_id=tier2_seller.id).all()
        client_names = [client.name for client in clients]
        return jsonify(client_names), 200
    
    return jsonify([]), 200

# ==========================================
# NEW ENDPOINTS: Client Configuration and Authentication
# ==========================================

@company_bp.route('/client/<client_name>/config', methods=['GET'])
def get_client_config(client_name):
    """Get client configuration"""
    client = Client.query.filter_by(name=client_name).first()
    
    if not client:
        return jsonify({'message': 'Client not found'}), 404
    
    # Generate theme based on client name
    theme_configs = {
        'John Smith': {
            'bgPattern': 'dots',
            'accentColor': '#3B82F6',
            'icon': '🏢'
        },
        'Sarah Johnson': {
            'bgPattern': 'grid',
            'accentColor': '#10B981',
            'icon': '📊'
        },
        'Mike Davis': {
            'bgPattern': 'diagonal',
            'accentColor': '#F59E0B',
            'icon': '🏭'
        },
        'Lisa Wong': {
            'bgPattern': 'circuit',
            'accentColor': '#8B5CF6',
            'icon': '⚡'
        }
    }
    
    default_theme = {
        'bgPattern': 'dots',
        'accentColor': '#6B7280',
        'icon': '🏢'
    }
    
    theme = theme_configs.get(client_name, default_theme)
    
    return jsonify({
        'id': client.id,
        'name': client.name,
        'company': client.company,
        'tagline': f'Professional services for {client.company}',
        'description': f'Comprehensive business solutions and consulting services for {client.company}',
        'theme_config': theme
    }), 200

@company_bp.route('/client/<client_name>/login', methods=['POST'])
def authenticate_client(client_name):
    """Client-specific authentication"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'message': 'Email and password required'}), 400
    
    # Find user by email and verify they belong to the specified client
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({'message': 'Invalid credentials'}), 401
    
    client = Client.query.get(user.client_id)
    if not client or client.name != client_name:
        return jsonify({'message': 'Invalid credentials'}), 401
    
    if Bcrypt.check_password_hash(user.password_hash, password):
        user_data = {
            'id': user.id,
            'email': email,
            'name': user.name,
            'user_type': 'client',
            'company': client.company,
            'client_id': client.id
        }
        
        access_token = create_access_token(identity=user_data)
        return jsonify({
            'token': access_token,
            'user': user_data
        }), 200
    
    return jsonify({'message': 'Invalid credentials'}), 401