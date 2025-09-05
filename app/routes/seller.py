from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Seller, Client, SubscriptionPlan, Commission
from app.utils.auth import jwt_required_custom
from app.models.project import Project
from datetime import datetime


seller_bp = Blueprint('seller', __name__)

@seller_bp.route('/dashboard', methods=['GET'])
@jwt_required_custom
def get_seller_dashboard1():
    current_user = get_jwt_identity()
    seller_id = current_user.get('id')
    
    seller = Seller.query.get(seller_id)
    if not seller:
        return jsonify({'message': 'Seller not found'}), 404
    
    # Get dashboard data
    clients = Client.query.filter_by(seller_id=seller_id).all()
    plans = SubscriptionPlan.query.filter_by(seller_id=seller_id).all()
    commissions = Commission.query.filter_by(seller_id=seller_id).all()
    
    dashboard_data = {
        'seller': {
            'id': seller.id,
            'name': seller.name,
            'subdomain': seller.subdomain
        },
        'stats': {
            'total_clients': len(clients),
            'active_clients': len([c for c in clients if c.status == 'active']),
            'total_plans': len(plans),
            'total_commissions': sum(c.commission_amount for c in commissions if c.status == 'paid')
        },
        'clients': [{
            'id': c.id,
            'name': c.name,
            'email': c.email,
            'company': c.company,
            'status': c.status
        } for c in clients],
        'plans': [{
            'id': p.id,
            'name': p.name,
            'price': float(p.price),
            'billing': p.billing,
            'active': p.active
        } for p in plans]
    }
    
    return jsonify(dashboard_data), 200

@seller_bp.route('/clients', methods=['POST'])
@jwt_required_custom
def add_client():
    current_user = get_jwt_identity()
    seller_id = current_user.get('id')
    
    data = request.get_json()
    
    try:
        new_client = Client(
            seller_id=seller_id,
            plan_id=data.get('plan_id'),
            name=data.get('name'),
            email=data.get('email'),
            company=data.get('company')
        )
        
        db.session.add(new_client)
        db.session.commit()
        
        return jsonify({
            'message': 'Client added successfully',
            'client_id': new_client.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error adding client: {str(e)}'}), 400

@seller_bp.route('/plans', methods=['POST'])
@jwt_required_custom
def add_plan():
    current_user = get_jwt_identity()
    seller_id = current_user.get('id')
    
    data = request.get_json()
    
    try:
        new_plan = SubscriptionPlan(
            seller_id=seller_id,
            name=data.get('name'),
            price=data.get('price'),
            currency=data.get('currency', 'USD'),
            billing=data.get('billing'),
            features=data.get('features'),
            max_clients=data.get('max_clients')
        )
        
        db.session.add(new_plan)
        db.session.commit()
        
        return jsonify({
            'message': 'Plan added successfully',
            'plan_id': new_plan.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error adding plan: {str(e)}'}), 400


@seller_bp.route('/dashboard', methods=['GET'])
@jwt_required_custom
def get_seller_dashboard():
    """Updated dashboard to match frontend expectations"""
    current_user = get_jwt_identity()
    seller_id = current_user.get('id')
    
    seller = Seller.query.get(seller_id)
    if not seller:
        return jsonify({'message': 'Seller not found'}), 404
    
    # Get dashboard data
    clients = Client.query.filter_by(seller_id=seller_id).all()
    plans = SubscriptionPlan.query.filter_by(seller_id=seller_id).all()
    
    # Calculate metrics
    active_clients = len([c for c in clients if c.status == 'active'])
    
    # Get all projects for revenue calculation
    client_ids = [client.id for client in clients]
    projects = Project.query.filter(Project.client_id.in_(client_ids)).all()
    active_projects = len([p for p in projects if p.status == 'active'])
    
    # Calculate monthly revenue (sum of project values)
    monthly_revenue = sum(float(p.project_value or 0) for p in projects)
    
    # Mock growth rate calculation
    growth_rate = 12.5  # You can implement actual calculation
    
    # Recent activity
    recent_activity = [
        {
            'id': str(i),
            'type': 'project_update',
            'description': f'Project {project.name} status updated',
            'timestamp': datetime.now().isoformat()
        }
        for i, project in enumerate(projects[:5])
    ]
    
    return jsonify({
        'metrics': {
            'total_clients': len(clients),
            'active_projects': active_projects,
            'monthly_revenue': monthly_revenue,
            'growth_rate': growth_rate
        },
        'recent_activity': recent_activity
    }), 200