from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Project, Client, User
from app.utils.auth import jwt_required_custom
from datetime import datetime

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/client/<client_name>/projects', methods=['GET'])
def get_client_projects(client_name):
    """Get projects for a specific client"""
    client = Client.query.filter_by(name=client_name).first()
    
    if not client:
        return jsonify({'message': 'Client not found'}), 404
    
    projects = Project.query.filter_by(client_id=client.id).all()
    
    project_list = []
    for project in projects:
        project_list.append({
            'id': project.id,
            'name': project.name,
            'status': project.status,
            'project_type': project.project_type,
            'description': project.description,
            'project_value': float(project.project_value) if project.project_value else 0,
            'completion_percentage': (float(project.hours_used or 0) / float(project.hourly_budget or 1)) * 100 if project.hourly_budget else 0,
            'created_at': project.created_at.isoformat() if project.created_at else None
        })
    
    return jsonify(project_list), 200

@projects_bp.route('/client/<client_name>/billing', methods=['GET'])
def get_client_billing(client_name):
    """Get billing information for a client"""
    client = Client.query.filter_by(name=client_name).first()
    
    if not client:
        return jsonify({'message': 'Client not found'}), 404
    
    # Get billing records for all client projects
    projects = Project.query.filter_by(client_id=client.id).all()
    billing_records = []
    
    for project in projects:
        if hasattr(project, 'billing_records'):
            for record in project.billing_records:
                billing_records.append({
                    'id': record.id,
                    'project_name': project.name,
                    'billing_type': record.billing_type,
                    'amount': float(record.amount),
                    'status': record.status,
                    'due_date': record.due_date.isoformat() if record.due_date else None,
                    'paid_date': record.paid_date.isoformat() if record.paid_date else None
                })
    
    return jsonify(billing_records), 200

@projects_bp.route('/', methods=['GET'])
@jwt_required_custom
def get_all_projects():
    """Get all projects for the authenticated user"""
    current_user = get_jwt_identity()
    user_type = current_user.get('user_type')
    user_id = current_user.get('id')
    
    if user_type == 'seller':
        # Get all projects for this seller's clients
        clients = Client.query.filter_by(seller_id=user_id).all()
        client_ids = [client.id for client in clients]
        projects = Project.query.filter(Project.client_id.in_(client_ids)).all()
    
    elif user_type == 'tier2_seller':
        # Get all projects for this tier2 seller's clients
        clients = Client.query.filter_by(tier2_seller_id=user_id).all()
        client_ids = [client.id for client in clients]
        projects = Project.query.filter(Project.client_id.in_(client_ids)).all()
    
    elif user_type == 'client':
        # Get projects for this client only
        user = User.query.get(user_id)
        if user:
            projects = Project.query.filter_by(client_id=user.client_id).all()
        else:
            projects = []
    
    else:
        return jsonify({'message': 'Invalid user type'}), 403
    
    project_list = []
    for project in projects:
        client = Client.query.get(project.client_id)
        project_list.append({
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
        })
    
    return jsonify(project_list), 200

@projects_bp.route('/', methods=['POST'])
@jwt_required_custom
def create_project():
    """Create a new project"""
    current_user = get_jwt_identity()
    data = request.get_json()
    
    # Validate access
    if current_user.get('user_type') not in ['seller', 'tier2_seller']:
        return jsonify({'message': 'Only sellers can create projects'}), 403
    
    try:
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
        
        return jsonify({
            'message': 'Project created successfully',
            'project_id': new_project.id,
            'name': new_project.name
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating project: {str(e)}'}), 400

@projects_bp.route('/<project_id>', methods=['DELETE'])
@jwt_required_custom
def delete_project(project_id):
    """Delete a project"""
    current_user = get_jwt_identity()
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404
    
    # Verify access permissions
    client = Client.query.get(project.client_id)
    if current_user.get('user_type') == 'seller':
        if client.seller_id != current_user.get('id'):
            return jsonify({'message': 'Access denied'}), 403
    elif current_user.get('user_type') == 'tier2_seller':
        if client.tier2_seller_id != current_user.get('id'):
            return jsonify({'message': 'Access denied'}), 403
    else:
        return jsonify({'message': 'Only sellers can delete projects'}), 403
    
    try:
        db.session.delete(project)
        db.session.commit()
        
        return jsonify({
            'message': 'Project deleted successfully',
            'project_id': project_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting project: {str(e)}'}), 400