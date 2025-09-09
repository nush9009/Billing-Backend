from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app import db
from app.models import Admin, Project, User, Tier1Seller, Tier2Seller
from app.utils.auth import jwt_required_custom

projects_bp = Blueprint('projects', __name__)

# -------------------- PROJECT ROUTES -------------------- #

@projects_bp.route('/', methods=['GET'])
@jwt_required_custom
def get_all_projects():
    """Get all projects based on the authenticated user's role."""
    current_user = get_jwt_identity()
    role = current_user.get('role')
    user_id = current_user.get('id')

    if role == 'admin':
        projects = Project.query.all()
    elif role == 'tier1_seller':
        clients = Admin.query.filter_by(tier1_seller_id=user_id).all()
        client_ids = [c.id for c in clients]
        projects = Project.query.filter(Project.client_id.in_(client_ids)).all()
    elif role == 'tier2_seller':
        clients = Admin.query.filter_by(tier2_seller_id=user_id).all()
        client_ids = [c.id for c in clients]
        projects = Project.query.filter(Project.client_id.in_(client_ids)).all()
    elif role == 'client':
        client_user = User.query.get(user_id)
        projects = Project.query.filter_by(client_id=client_user.client_id).all() if client_user else []
    else:
        return jsonify({'message': 'Invalid role'}), 403

    project_list = []
    for p in projects:
        client = Admin.query.get(p.client_id)
        project_list.append({
            'id': p.id,
            'name': p.name,
            'status': p.status,
            'project_type': p.project_type,
            'description': p.description,
            'client_name': client.name if client else 'Unknown',
            'client_company': client.company if client else 'Unknown',
            'project_value': float(p.project_value) if p.project_value else 0,
            'hours_used': float(p.hours_used) if p.hours_used else 0,
            'hourly_budget': float(p.hourly_budget) if p.hourly_budget else 0,
            'completion_percentage': (float(p.hours_used or 0) / float(p.hourly_budget or 1)) * 100 if p.hourly_budget else 0
        })
    return jsonify(project_list), 200


@projects_bp.route('/<project_id>', methods=['GET'])
@jwt_required_custom
def get_project(project_id):
    """Get a single project by ID"""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404

    client = Admin.query.get(project.client_id)
    return jsonify({
        'id': project.id,
        'name': project.name,
        'status': project.status,
        'project_type': project.project_type,
        'description': project.description,
        'client_name': client.name if client else 'Unknown',
        'client_company': client.company if client else 'Unknown',
        'project_value': float(project.project_value) if project.project_value else 0,
        'hours_used': float(project.hours_used) if project.hours_used else 0,
        'hourly_budget': float(project.hourly_budget) if project.hourly_budget else 0,
        'completion_percentage': (float(project.hours_used or 0) / float(project.hourly_budget or 1)) * 100 if project.hourly_budget else 0
    }), 200


@projects_bp.route('/', methods=['POST'])
@jwt_required_custom
def create_project():
    """Create a new project"""
    current_user = get_jwt_identity()
    if current_user.get('role') not in ['admin', 'tier1_seller', 'tier2_seller']:
        return jsonify({'message': 'Access denied'}), 403

    data = request.get_json()
    new_project = Project(
        client_id=data.get('client_id'),
        name=data.get('name'),
        status=data.get('status', 'active'),
        project_type=data.get('project_type'),
        description=data.get('description'),
        project_value=data.get('project_value'),
        billing_frequency=data.get('billing_frequency', 'milestone'),
        hourly_budget=data.get('hourly_budget')
    )
    db.session.add(new_project)
    db.session.commit()
    return jsonify({'message': 'Project created successfully', 'id': new_project.id}), 201


@projects_bp.route('/<project_id>', methods=['PUT', 'PATCH'])
@jwt_required_custom
def update_project(project_id):
    """Update a project"""
    current_user = get_jwt_identity()
    role = current_user.get('role')
    user_id = current_user.get('id')

    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404

    client = Admin.query.get(project.client_id)
    if not client:
        return jsonify({'message': 'Associated client not found'}), 404

    if role == 'admin':
        pass
    elif role == 'tier1_seller' and client.tier1_seller_id != user_id:
        return jsonify({'message': 'Access denied'}), 403
    elif role == 'tier2_seller' and client.tier2_seller_id != user_id:
        return jsonify({'message': 'Access denied'}), 403
    elif role == 'client':
        return jsonify({'message': 'Clients cannot update projects'}), 403

    data = request.get_json()
    for f in ['name', 'status', 'project_type', 'description', 'project_value', 'hourly_budget', 'hours_used']:
        if f in data:
            setattr(project, f, data[f])

    db.session.commit()
    return jsonify({'message': 'Project updated successfully'}), 200


@projects_bp.route('/<project_id>', methods=['DELETE'])
@jwt_required_custom
def delete_project(project_id):
    """Delete a project"""
    current_user = get_jwt_identity()
    role = current_user.get('role')
    user_id = current_user.get('id')

    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404

    client = Admin.query.get(project.client_id)
    if not client:
        return jsonify({'message': 'Associated client not found'}), 404

    if role == 'admin':
        pass
    elif role == 'tier1_seller' and client.tier1_seller_id != user_id:
        return jsonify({'message': 'Access denied'}), 403
    elif role == 'tier2_seller' and client.tier2_seller_id != user_id:
        return jsonify({'message': 'Access denied'}), 403
    else:
        return jsonify({'message': 'Access denied'}), 403

    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted successfully'}), 200


# -------------------- CLIENT ROUTES -------------------- #

@projects_bp.route('/clients', methods=['POST'])
@jwt_required_custom
def create_client():
    """Create a new client"""
    current_user = get_jwt_identity()
    if current_user.get('role') not in ['admin', 'tier1_seller', 'tier2_seller']:
        return jsonify({'message': 'Access denied'}), 403

    data = request.get_json()
    new_client = Admin(
        name=data.get('name'),
        company=data.get('company'),
        tier1_seller_id=data.get('tier1_seller_id'),
        tier2_seller_id=data.get('tier2_seller_id')
    )
    db.session.add(new_client)
    db.session.commit()
    return jsonify({'message': 'Client created successfully', 'id': new_client.id}), 201


@projects_bp.route('/clients', methods=['GET'])
@jwt_required_custom
def list_clients():
    """List clients based on role"""
    current_user = get_jwt_identity()
    role = current_user.get('role')
    user_id = current_user.get('id')

    if role == 'admin':
        clients = Admin.query.all()
    elif role == 'tier1_seller':
        clients = Admin.query.filter_by(tier1_seller_id=user_id).all()
    elif role == 'tier2_seller':
        clients = Admin.query.filter_by(tier2_seller_id=user_id).all()
    else:
        return jsonify({'message': 'Access denied'}), 403

    return jsonify([{'id': c.id, 'name': c.name, 'company': c.company} for c in clients]), 200


@projects_bp.route('/clients/<client_id>', methods=['GET'])
@jwt_required_custom
def get_client(client_id):
    """Get a client by ID"""
    client = Admin.query.get(client_id)
    if not client:
        return jsonify({'message': 'Client not found'}), 404
    return jsonify({'id': client.id, 'name': client.name, 'company': client.company}), 200


@projects_bp.route('/clients/<client_id>/assign', methods=['PUT'])
@jwt_required_custom
def assign_client(client_id):
    """Assign or transfer a client"""
    current_user = get_jwt_identity()
    if current_user.get('role') not in ['admin', 'tier1_seller', 'tier2_seller']:
        return jsonify({'message': 'Access denied'}), 403

    client = Admin.query.get(client_id)
    if not client:
        return jsonify({'message': 'Client not found'}), 404

    data = request.get_json()
    if 'tier1_seller_id' in data:
        client.tier1_seller_id = data['tier1_seller_id']
        client.tier2_seller_id = None
    elif 'tier2_seller_id' in data:
        client.tier2_seller_id = data['tier2_seller_id']
        client.tier1_seller_id = None
    else:
        return jsonify({'message': 'Must provide tier1_seller_id or tier2_seller_id'}), 400

    db.session.commit()
    return jsonify({'message': 'Client reassigned successfully'}), 200


@projects_bp.route('/clients/<client_id>', methods=['PUT', 'PATCH'])
@jwt_required_custom
def update_client(client_id):
    """Update client details"""
    current_user = get_jwt_identity()
    if current_user.get('role') not in ['admin', 'tier1_seller', 'tier2_seller']:
        return jsonify({'message': 'Access denied'}), 403

    client = Admin.query.get(client_id)
    if not client:
        return jsonify({'message': 'Client not found'}), 404

    data = request.get_json()
    for f in ['name', 'company']:
        if f in data:
            setattr(client, f, data[f])

    db.session.commit()
    return jsonify({'message': 'Client updated successfully'}), 200


@projects_bp.route('/clients/<client_id>', methods=['DELETE'])
@jwt_required_custom
def delete_client(client_id):
    """Delete a client (Admin only)"""
    current_user = get_jwt_identity()
    if current_user.get('role') != 'admin':
        return jsonify({'message': 'Only admin can delete clients'}), 403

    client = Admin.query.get(client_id)
    if not client:
        return jsonify({'message': 'Client not found'}), 404

    db.session.delete(client)
    db.session.commit()
    return jsonify({'message': 'Client deleted successfully'}), 200
