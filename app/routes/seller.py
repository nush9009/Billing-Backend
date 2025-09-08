from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, bcrypt
from app.models import Seller, Client, SubscriptionPlan, Commission,Tier2Seller
from app.utils.auth import jwt_required_custom
from app.models.project import Project
from datetime import datetime


seller_bp = Blueprint('seller', __name__)

@seller_bp.route('/tier2-sellers', methods=['POST'])
@jwt_required_custom
def add_tier2_seller():
    """Add new Tier-2 seller - SellerAdminPortal.tsx, AddTier2SellerForm.tsx"""
    current_user = get_jwt_identity()
    seller_id = current_user.get('id')
    
    if current_user.get('role') != 'seller':
        return jsonify({'message': 'Seller access required'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'subdomain', 'admin_email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'{field} is required'}), 400
    
    # Check if subdomain or email already exists
    existing_tier2 = Tier2Seller.query.filter(
        (Tier2Seller.subdomain == data['subdomain']) | 
        (Tier2Seller.admin_email == data['admin_email'])
    ).first()
    
    if existing_tier2:
        return jsonify({'message': 'Subdomain or email already exists'}), 400
    
    try:
        # Hash password
        password_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        
        new_tier2_seller = Tier2Seller(
            tier1_seller_id=seller_id,
            name=data['name'],
            subdomain=data['subdomain'],
            admin_email=data['admin_email'],
            password_hash=password_hash,
            commission_type=data.get('commission_type', 'percentage'),
            commission_value=data.get('commission_value', 10.0)
        )
        
        db.session.add(new_tier2_seller)
        db.session.commit()
        
        return jsonify({
            'message': 'Tier-2 Seller created successfully',
            'seller_id': new_tier2_seller.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating Tier-2 seller: {str(e)}'}), 500

@seller_bp.route('/clients/<client_id>', methods=['DELETE'])
@jwt_required_custom
def delete_client(client_id):
    """Soft delete client - SellerAdminPortal.tsx, useSellerData.ts"""
    current_user = get_jwt_identity()
    
    client = Client.query.get(client_id)
    if not client:
        return jsonify({'message': 'Client not found'}), 404
    
    # Verify access
    if current_user.get('role') == 'seller':
        if client.seller_id != current_user.get('id'):
            return jsonify({'message': 'Access denied'}), 403
    elif current_user.get('role') == 'tier2_seller':
        if client.tier2_seller_id != current_user.get('id'):
            return jsonify({'message': 'Access denied'}), 403
    else:
        return jsonify({'message': 'Access denied'}), 403
    
    try:
        # Soft delete by setting status to inactive
        client.status = 'inactive'
        
        # Also set related users to inactive
        from app.models.project import User
        users = User.query.filter_by(client_id=client_id).all()
        for user in users:
            user.status = 'inactive'
        
        # Set related projects to cancelled
        projects = Project.query.filter_by(client_id=client_id).all()
        for project in projects:
            project.status = 'cancelled'
        
        db.session.commit()
        
        return jsonify({'message': 'Client deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting client: {str(e)}'}), 500

@seller_bp.route('/plans/<plan_id>', methods=['PUT', 'PATCH'])
@jwt_required_custom
def update_plan(plan_id):
    """Update subscription plan - SellerAdminPortal.tsx, AddPlanForm.tsx"""
    current_user = get_jwt_identity()
    
    plan = SubscriptionPlan.query.get(plan_id)
    if not plan:
        return jsonify({'message': 'Plan not found'}), 404
    
    # Verify access
    if current_user.get('role') == 'seller':
        if plan.seller_id != current_user.get('id'):
            return jsonify({'message': 'Access denied'}), 403
    elif current_user.get('role') == 'tier2_seller':
        if plan.tier2_seller_id != current_user.get('id'):
            return jsonify({'message': 'Access denied'}), 403
    else:
        return jsonify({'message': 'Access denied'}), 403
    
    data = request.get_json()
    
    try:
        # Update plan fields
        if 'name' in data:
            plan.name = data['name']
        if 'price' in data:
            plan.price = data['price']
        if 'billing' in data:
            plan.billing = data['billing']
        if 'features' in data:
            plan.features = data['features']
        if 'max_clients' in data:
            plan.max_clients = data['max_clients']
        if 'active' in data:
            plan.active = data['active']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Plan updated successfully',
            'plan_id': plan_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating plan: {str(e)}'}), 500

@seller_bp.route('/plans/<plan_id>', methods=['DELETE'])
@jwt_required_custom
def delete_plan(plan_id):
    """Soft delete plan - SellerAdminPortal.tsx, useSellerData.ts"""
    current_user = get_jwt_identity()
    
    plan = SubscriptionPlan.query.get(plan_id)
    if not plan:
        return jsonify({'message': 'Plan not found'}), 404
    
    # Verify access
    if current_user.get('role') == 'seller':
        if plan.seller_id != current_user.get('id'):
            return jsonify({'message': 'Access denied'}), 403
    elif current_user.get('role') == 'tier2_seller':
        if plan.tier2_seller_id != current_user.get('id'):
            return jsonify({'message': 'Access denied'}), 403
    else:
        return jsonify({'message': 'Access denied'}), 403
    
    try:
        # Soft delete by setting active to false
        plan.active = False
        db.session.commit()
        
        return jsonify({'message': 'Plan deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting plan: {str(e)}'}), 500

@seller_bp.route('/tier2-sellers/<seller_id>', methods=['DELETE'])
@jwt_required_custom
def delete_tier2_seller(seller_id):
    """Soft delete Tier-2 seller - SellerAdminPortal.tsx, useSellerData.ts"""
    current_user = get_jwt_identity()
    
    tier2_seller = Tier2Seller.query.get(seller_id)
    if not tier2_seller:
        return jsonify({'message': 'Tier-2 seller not found'}), 404
    
    # Verify access (only parent tier1 seller can delete)
    if current_user.get('role') != 'seller' or tier2_seller.tier1_seller_id != current_user.get('id'):
        return jsonify({'message': 'Access denied'}), 403
    
    try:
        # Soft delete by setting deleted_at timestamp
        from datetime import datetime
        tier2_seller.deleted_at = datetime.utcnow()
        
        # Deactivate associated plans
        plans = SubscriptionPlan.query.filter_by(tier2_seller_id=seller_id).all()
        for plan in plans:
            plan.active = False
        
        # Set associated clients to inactive
        clients = Client.query.filter_by(tier2_seller_id=seller_id).all()
        for client in clients:
            client.status = 'inactive'
        
        db.session.commit()
        
        return jsonify({'message': 'Tier-2 Seller deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting Tier-2 seller: {str(e)}'}), 500

@seller_bp.route('/dashboard', methods=['GET'])
@jwt_required_custom
def get_comprehensive_seller_dashboard():
    """Comprehensive seller dashboard - SellerAdminPortal.tsx, useSellerData.ts"""
    current_user = get_jwt_identity()
    seller_id = current_user.get('id')
    user_role = current_user.get('role')
    
    try:
        if user_role == 'seller':
            seller = Seller.query.get(seller_id)
            if not seller:
                return jsonify({'message': 'Seller not found'}), 404
            
            # Get seller data
            clients = Client.query.filter_by(seller_id=seller_id).all()
            plans = SubscriptionPlan.query.filter_by(seller_id=seller_id).all()
            tier2_sellers = Tier2Seller.query.filter_by(tier1_seller_id=seller_id).all()
            
        elif user_role == 'tier2_seller':
            tier2_seller = Tier2Seller.query.get(seller_id)
            if not tier2_seller:
                return jsonify({'message': 'Tier2 seller not found'}), 404
            
            # Get tier2 seller data
            clients = Client.query.filter_by(tier2_seller_id=seller_id).all()
            plans = SubscriptionPlan.query.filter_by(tier2_seller_id=seller_id).all()
            tier2_sellers = []  # Tier2 sellers don't have sub-sellers
            
        else:
            return jsonify({'message': 'Access denied'}), 403
        
        # Format clients data
        clients_data = []
        for client in clients:
            client_projects = Project.query.filter_by(client_id=client.id).all()
            clients_data.append({
                'id': client.id,
                'name': client.name,
                'email': client.email,
                'company': client.company,
                'status': client.status,
                'intake_form_completed': client.intake_form_completed,
                'plan_id': client.plan_id,
                'total_projects': len(client_projects),
                'active_projects': len([p for p in client_projects if p.status == 'active']),
                'created_at': client.created_at.isoformat() if client.created_at else None
            })
        
        # Format plans data
        plans_data = []
        for plan in plans:
            plan_clients = Client.query.filter_by(plan_id=plan.id).count()
            plans_data.append({
                'id': plan.id,
                'name': plan.name,
                'price': float(plan.price),
                'currency': plan.currency,
                'billing': plan.billing,
                'features': plan.features,
                'max_clients': plan.max_clients,
                'active': plan.active,
                'current_clients': plan_clients,
                'created_at': plan.created_at.isoformat() if plan.created_at else None
            })
        
        # Format tier2 sellers data
        tier2_data = []
        for t2 in tier2_sellers:
            if not t2.deleted_at:  # Only active tier2 sellers
                t2_clients = Client.query.filter_by(tier2_seller_id=t2.id).count()
                tier2_data.append({
                    'id': t2.id,
                    'name': t2.name,
                    'subdomain': t2.subdomain,
                    'admin_email': t2.admin_email,
                    'commission_type': t2.commission_type,
                    'commission_value': float(t2.commission_value) if t2.commission_value else 0,
                    'total_clients': t2_clients,
                    'created_at': t2.created_at.isoformat() if t2.created_at else None
                })
        
        # Calculate commissions (mock data for now)
        commissions_data = [
            {
                'id': str(i),
                'client_name': client.name,
                'amount': 1000.0 + (i * 100),
                'commission_amount': 150.0 + (i * 15),
                'status': 'paid' if i % 2 == 0 else 'pending',
                'type': 'recurring_fee',
                'transaction_date': client.created_at.date().isoformat() if client.created_at else None
            }
            for i, client in enumerate(clients[:5])
        ]
        
        # Calculate stats
        total_revenue = sum(float(p.project_value or 0) for p in Project.query.join(Client).filter(Client.seller_id == seller_id if user_role == 'seller' else Client.tier2_seller_id == seller_id).all())
        active_clients = len([c for c in clients if c.status == 'active'])
        
        return jsonify({
            'sellerData': {
                'id': seller_id,
                'name': seller.name if user_role == 'seller' else tier2_seller.name,
                'subdomain': seller.subdomain if user_role == 'seller' else tier2_seller.subdomain,
                'type': user_role,
                'total_clients': len(clients),
                'active_clients': active_clients,
                'total_revenue': total_revenue
            },
            'clients': clients_data,
            'plans': plans_data,
            'tier2_sellers': tier2_data,
            'commissions': commissions_data,
            'stats': {
                'total_clients': len(clients),
                'active_clients': active_clients,
                'total_plans': len(plans),
                'active_plans': len([p for p in plans if p.active]),
                'total_tier2_sellers': len(tier2_data),
                'total_revenue': total_revenue
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Error fetching dashboard data: {str(e)}'}), 500

@seller_bp.route('/projects', methods=['GET'])
@jwt_required_custom
def get_seller_projects():
    """Get all projects for a seller - ProjectManagement.tsx"""
    current_user = get_jwt_identity()
    seller_id = current_user.get('id')
    user_role = current_user.get('role')
    
    try:
        if user_role == 'seller':
            # Get all clients under this seller
            clients = Client.query.filter_by(seller_id=seller_id).all()
        elif user_role == 'tier2_seller':
            # Get all clients under this tier2 seller
            clients = Client.query.filter_by(tier2_seller_id=seller_id).all()
        else:
            return jsonify({'message': 'Access denied'}), 403
        
        client_ids = [client.id for client in clients]
        projects = Project.query.filter(Project.client_id.in_(client_ids)).all()
        
        projects_data = []
        for project in projects:
            client = Client.query.get(project.client_id)
            
            # Calculate billing summary
            total_billed = float(project.budget_spent or 0)
            project_value = float(project.project_value or 0)
            completion = (float(project.hours_used or 0) / float(project.hourly_budget or 1)) * 100 if project.hourly_budget else 0
            
            projects_data.append({
                'id': project.id,
                'name': project.name,
                'status': project.status,
                'project_type': project.project_type,
                'description': project.description,
                'client_name': client.name if client else 'Unknown',
                'client_company': client.company if client else 'Unknown',
                'project_value': project_value,
                'total_billed': total_billed,
                'remaining_value': project_value - total_billed,
                'completion_percentage': completion,
                'billing_frequency': project.billing_frequency,
                'hours_used': float(project.hours_used or 0),
                'hourly_budget': float(project.hourly_budget or 0),
                'start_date': project.start_date.isoformat() if project.start_date else None,
                'end_date': project.end_date.isoformat() if project.end_date else None,
                'created_at': project.created_at.isoformat() if project.created_at else None
            })
        
        return jsonify(projects_data), 200
        
    except Exception as e:
        return jsonify({'message': f'Error fetching projects: {str(e)}'}), 500