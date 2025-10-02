from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Admin, Client , Project, Tier1Seller, Tier2Seller
from datetime import datetime

from app.models.project import SubscriptionPlan
from app.models.seller import Tier2Seller

projects_bp = Blueprint('projects', __name__)

# ------------------ HELPER FUNCTIONS ------------------
def get_current_user(user_id):
    if admin := Admin.query.get(user_id):
        return {"id": admin.id, "role": "admin"}
    if tier1 := Tier1Seller.query.get(user_id):
        return {"id": tier1.id, "role": "tier1_seller"}
    if tier2 := Tier2Seller.query.get(user_id):
        return {"id": tier2.id, "role": "tier2_seller"}
    return None

def is_admin(user): return user and user.get('role') == 'admin'
def is_tier1(user): return user and user.get('role') == 'tier1_seller'
def is_tier2(user): return user and user.get('role') == 'tier2_seller'

# -------------------- PROJECT ROUTES -------------------- #

@projects_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_projects():
    current_user = get_current_user(get_jwt_identity())
    user_id = current_user.get('id')

    if is_admin(current_user):
        projects = Project.query.all()
    elif is_tier1(current_user):
        # MODIFIED: Tier 1 sees their projects that are NOT assigned to a Tier 2 seller.
        projects = Project.query.filter_by(
            tier1_seller_id=user_id, 
            tier2_seller_id=None
        ).all()
    elif is_tier2(current_user):
        projects = Project.query.filter_by(tier2_seller_id=user_id).all()
    else:
        return jsonify({'message': 'Access denied'}), 403

    result = []
    for p in projects:
        result.append({
            'id': p.id,
            'name': p.name,
            'status': p.status,
            'project_type': p.project_type,
            'description': p.description,
            'tier1_seller_id': p.tier1_seller_id,
            'tier2_seller_id': p.tier2_seller_id,
            # 'project_value': float(p.project_value) if p.project_value else 0,
            'hours_used': float(p.hours_used) if p.hours_used else 0,
            'hourly_budget': float(p.hourly_budget) if p.hourly_budget else 0,
            'completion_percentage': (float(p.hours_used or 0) / float(p.hourly_budget or 1)) * 100 if p.hourly_budget else 0,
            'clients': [{'id': c.id, 'name': c.name, 'company': c.company} for c in p.clients],
            'subscription_plan_id': p.subscription_plan_id 
        })
    return jsonify(result), 200



@projects_bp.route('/services/<project_id>/toggle', methods=['POST'])
@jwt_required()
def toggle_project_status(project_id):
    current_user = get_current_user(get_jwt_identity())
    user_id = current_user.get('id')

    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404

    # Access control
    if (is_tier1(current_user) and project.tier1_seller_id != user_id) or \
       (is_tier2(current_user) and project.tier2_seller_id != user_id):
        return jsonify({'message': 'Access denied'}), 403

    # Toggle status
    if project.status == "active":
        project.status = "inactive"
    else:
        project.status = "active"

    db.session.commit()
    return jsonify({
        'message': f"Project status toggled to {project.status}",
        'id': project.id,
        'status': project.status
    }), 200

@projects_bp.route('/<project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    current_user = get_current_user(get_jwt_identity())
    user_id = current_user.get('id')

    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404

    if (is_tier1(current_user) and project.tier1_seller_id != user_id) or \
       (is_tier2(current_user) and project.tier2_seller_id != user_id):
        return jsonify({'message': 'Access denied'}), 403

    return jsonify({
        'id': project.id,
        'name': project.name,
        'status': project.status,
        'project_type': project.project_type,
        'description': project.description,
        'tier1_seller_id': project.tier1_seller_id,
        'tier2_seller_id': project.tier2_seller_id,
        'project_value': float(project.project_value) if project.project_value else 0,
        'hours_used': float(project.hours_used) if project.hours_used else 0,
        'hourly_budget': float(project.hourly_budget) if project.hourly_budget else 0,
        'completion_percentage': (float(project.hours_used or 0) / float(project.hourly_budget or 1)) * 100 if project.hourly_budget else 0,
        'clients': [{'id': c.id, 'name': c.name, 'company': c.company} for c in project.clients],
        'subscription_plan_id': project.subscription_plan_id
    }), 200

@projects_bp.route('/', methods=['POST'])
@jwt_required()
def create_project():
    current_user = get_current_user(get_jwt_identity())
    user_id = current_user.get('id')

    if not (is_admin(current_user) or is_tier1(current_user) or is_tier2(current_user)):
        return jsonify({'message': 'Access denied'}), 403

    data = request.get_json()
    subscription_plan_id = data.get('subscription_plan_id')
    subscription_plan_name = data.get('subscription_plan_name')
    plan = None

    # --- 1. FIND the plan by ID or Name ---
    if subscription_plan_id:
        plan = SubscriptionPlan.query.get(subscription_plan_id)
    elif subscription_plan_name:
        plan = SubscriptionPlan.query.filter_by(name=subscription_plan_name).first()
    else:
        return jsonify({'message': 'Either subscription_plan_id or subscription_plan_name is required'}), 400

    if not plan:
        return jsonify({'message': 'Subscription plan not found'}), 404

    # --- 2. VALIDATE the plan based on user role (same logic as before) ---
    if is_tier1(current_user):
        # Tier 1 sellers must use an admin-created plan
        if plan.creator_type != 'admin':
            return jsonify({'message': 'Tier 1 sellers must select a plan created by an Admin.'}), 403

    elif is_tier2(current_user):
        # Tier 2 sellers must use a plan created by their parent Tier 1
        tier2_seller = Tier2Seller.query.get(user_id)
        if plan.creator_id != tier2_seller.tier1_seller_id:
            return jsonify({'message': 'This plan is not available to you.'}), 403

    # --- 3. CREATE the project ---
    tier1_seller_id = data.get('tier1_seller_id') if is_admin(current_user) else (user_id if is_tier1(current_user) else Tier2Seller.query.get(user_id).tier1_seller_id)
    tier2_seller_id = data.get('tier2_seller_id') if is_admin(current_user) or is_tier1(current_user) else (user_id if is_tier2(current_user) else None)

    new_project = Project(
        name=data.get('name'),
        status=data.get('status', 'active'),
        project_type=data.get('project_type'),
        description=data.get('description'),
        billing_frequency=data.get('billing_frequency', 'milestone'),
        hourly_budget=data.get('hourly_budget'),
        tier1_seller_id=tier1_seller_id,
        tier2_seller_id=tier2_seller_id,
        subscription_plan_id=plan.id  # Use the ID from the plan object we found
    )
    db.session.add(new_project)
    db.session.commit()
    return jsonify({'message': 'Project created successfully', 'id': new_project.id}), 201

@projects_bp.route('/<project_id>', methods=['PUT', 'PATCH'])
@jwt_required()
def update_project(project_id):
    current_user = get_current_user(get_jwt_identity())
    user_id = current_user.get('id')

    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404

    if (is_tier1(current_user) and project.tier1_seller_id != user_id) or \
       (is_tier2(current_user) and project.tier2_seller_id != user_id):
        return jsonify({'message': 'Access denied'}), 403

    data = request.get_json()
    for f in ['name', 'status', 'project_type', 'description', 'project_value', 'hourly_budget', 'hours_used']:
        if f in data:
            setattr(project, f, data[f])

    db.session.commit()
    return jsonify({'message': 'Project updated successfully'}), 200

@projects_bp.route('/<project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    current_user = get_current_user(get_jwt_identity())
    user_id = current_user.get('id')

    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404

    if (is_tier1(current_user) and project.tier1_seller_id != user_id) or \
       (is_tier2(current_user) and project.tier2_seller_id != user_id):
        return jsonify({'message': 'Access denied'}), 403

    # Delete associated clients
    for client in project.clients:
        db.session.delete(client)
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project and its clients deleted successfully'}), 200

# -------------------- CLIENT ROUTES -------------------- #

@projects_bp.route('/clients', methods=['POST'])
@jwt_required()
def create_client():
    current_user = get_current_user(get_jwt_identity())
    user_id = current_user.get('id')

    if not (is_admin(current_user) or is_tier1(current_user) or is_tier2(current_user)):
        return jsonify({'message': 'Access denied'}), 403

    data = request.get_json()
    project = Project.query.get(data.get('project_id'))
    if not project:
        return jsonify({'message': 'Associated project not found'}), 404

    if (is_tier1(current_user) and project.tier1_seller_id != user_id) or \
       (is_tier2(current_user) and project.tier2_seller_id != user_id):
        return jsonify({'message': 'Access denied'}), 403

    new_client = Client(name=data.get('name'), company=data.get('company'), project_id=project.id)
    db.session.add(new_client)
    db.session.commit()
    return jsonify({'message': 'Client created successfully', 'id': new_client.id}), 201

@projects_bp.route('/clients', methods=['GET'])
@jwt_required()
def list_clients():
    current_user = get_current_user(get_jwt_identity())
    user_id = current_user.get('id')

    if is_admin(current_user):
        clients = Client.query.all()
    elif is_tier1(current_user):
        clients = Client.query.join(Project).filter(Project.tier1_seller_id == user_id).all()
    elif is_tier2(current_user):
        clients = Client.query.join(Project).filter(Project.tier2_seller_id == user_id).all()
    else:
        return jsonify({'message': 'Access denied'}), 403

    return jsonify([{'id': c.id, 'name': c.name, 'company': c.company, 'project_id': c.project_id} for c in clients]), 200

@projects_bp.route('/clients/<client_id>', methods=['GET'])
@jwt_required()
def get_client(client_id):
    current_user = get_current_user(get_jwt_identity())
    user_id = current_user.get('id')

    client = Client.query.get(client_id)
    if not client:
        return jsonify({'message': 'Client not found'}), 404

    project = Project.query.get(client.project_id)
    if (is_tier1(current_user) and project.tier1_seller_id != user_id) or \
       (is_tier2(current_user) and project.tier2_seller_id != user_id):
        return jsonify({'message': 'Access denied'}), 403

    return jsonify({'id': client.id, 'name': client.name, 'company': client.company, 'project_id': client.project_id}), 200
