from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, bcrypt
from app.models import Seller, Tier2Seller, Client, SubscriptionPlan, Project
from app.utils.auth import admin_required, jwt_required_custom
import uuid

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/sellers', methods=['POST'])
@jwt_required_custom
def add_tier1_seller():
    """Add new Tier-1 seller - AdminPortal.tsx, AddSellerForm.tsx"""
    current_user = get_jwt_identity()
    
    # Verify admin access
    if current_user.get('role') != 'seller' or current_user.get('id') != 'admin':
        return jsonify({'message': 'Admin access required'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'subdomain', 'admin_email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'{field} is required'}), 400
    
    # Check if subdomain or email already exists
    existing_seller = Seller.query.filter(
        (Seller.subdomain == data['subdomain']) | 
        (Seller.admin_email == data['admin_email'])
    ).first()
    
    if existing_seller:
        return jsonify({'message': 'Subdomain or email already exists'}), 400
    
    try:
        # Hash password
        password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        
        new_seller = Seller(
            name=data['name'],
            subdomain=data['subdomain'],
            admin_email=data['admin_email'],
            password_hash=password_hash,
            commission_type=data.get('commission_type', 'percentage'),
            commission_value=data.get('commission_value', 15.0),
            status='active'
        )
        
        db.session.add(new_seller)
        db.session.commit()
        
        return jsonify({
            'message': 'Seller created successfully',
            'seller_id': new_seller.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating seller: {str(e)}'}), 500

@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required_custom
def get_admin_dashboard():
    """Enhanced admin dashboard with comprehensive data"""
    current_user = get_jwt_identity()
    
    if current_user.get('role') != 'seller':
        return jsonify({'message': 'Admin access required'}), 403
    
    try:
        sellers = Seller.query.all()
        tier2_sellers = Tier2Seller.query.all()
        clients = Client.query.all()
        projects = Project.query.all()
        
        # Calculate metrics
        total_revenue = 0
        active_projects = 0
        
        for project in projects:
            if project.project_value:
                total_revenue += float(project.project_value)
            if project.status == 'active':
                active_projects += 1
        
        # Seller performance data
        seller_performance = []
        for seller in sellers:
            seller_clients = Client.query.filter_by(seller_id=seller.id).count()
            seller_projects = Project.query.join(Client).filter(Client.seller_id == seller.id).count()
            
            seller_performance.append({
                'id': seller.id,
                'name': seller.name,
                'subdomain': seller.subdomain,
                'total_clients': seller_clients,
                'total_projects': seller_projects,
                'status': seller.status
            })
        
        return jsonify({
            'stats': {
                'total_sellers': len(sellers),
                'total_tier2_sellers': len(tier2_sellers),
                'total_clients': len(clients),
                'total_projects': len(projects),
                'active_projects': active_projects,
                'total_revenue': total_revenue
            },
            'sellers': seller_performance,
            'recent_activity': [
                {
                    'id': str(i),
                    'type': 'system',
                    'description': f'New seller {seller.name} added',
                    'timestamp': seller.created_at.isoformat() if seller.created_at else None
                }
                for i, seller in enumerate(sellers[-5:])
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Error fetching admin data: {str(e)}'}), 500
