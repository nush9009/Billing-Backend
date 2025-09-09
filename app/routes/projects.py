from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
# UPDATED: Import the new, renamed models
from app.models import Admin, Project, User, Tier1Seller, Tier2Seller
from app.utils.auth import jwt_required_custom
from datetime import datetime

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/client/<admin_name>/projects', methods=['GET'])
def get_client_projects(admin_name):
    """Get projects for a specific Admin (formerly Client)."""
    # UPDATED: Query the Admin model
    admin = Admin.query.filter_by(name=admin_name).first()
    
    if not admin:
        return jsonify({'message': 'Admin account not found'}), 404
    
    projects = Project.query.filter_by(client_id=admin.id).all()
    
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

@projects_bp.route('/client/<admin_name>/billing', methods=['GET'])
def get_client_billing(admin_name):
    """Get billing information for an Admin (formerly Client)."""
    # UPDATED: Query the Admin model
    admin = Admin.query.filter_by(name=admin_name).first()
    
    if not admin:
        return jsonify({'message': 'Admin account not found'}), 404
    
    projects = Project.query.filter_by(client_id=admin.id).all()
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
    """Get all projects based on the authenticated user's role."""
    current_user = get_jwt_identity()
    user_role = current_user.get('role')
    user_id = current_user.get('id')
    
    projects = []
    
    # UPDATED: Logic for new roles and models
    if user_role == 'admin':
        # Admin can see all projects
        projects = Project.query.all()
    elif user_role == 'tier1_seller':
        # Tier1 Seller sees projects for all their directly managed Admins
        admins = Admin.query.filter_by(tier1_seller_id=user_id).all()
        admin_ids = [admin.id for admin in admins]
        projects = Project.query.filter(Project.client_id.in_(admin_ids)).all()
    
    elif user_role == 'tier2_seller':
        # Tier2 Seller sees projects for their directly managed Admins
        admins = Admin.query.filter_by(tier2_seller_id=user_id).all()
        admin_ids = [admin.id for admin in admins]
        projects = Project.query.filter(Project.client_id.in_(admin_ids)).all()
    
    elif user_role == 'client':
        # A Client Portal User sees projects only for their specific Admin company
        client_user = User.query.get(user_id)
        if client_user:
            projects = Project.query.filter_by(client_id=client_user.client_id).all()
    
    else:
        return jsonify({'message': 'Invalid user role'}), 403
    
    project_list = []
    for project in projects:
        # UPDATED: Get the Admin record associated with the project
        admin = Admin.query.get(project.client_id)
        project_list.append({
            'id': project.id,
            'name': project.name,
            'status': project.status,
            'project_type': project.project_type,
            'description': project.description,
            'client_name': admin.name if admin else 'Unknown',
            'client_company': admin.company if admin else 'Unknown',
            'project_value': float(project.project_value) if project.project_value else 0,
            'hours_used': float(project.hours_used) if project.hours_used else 0,
            'hourly_budget': float(project.hourly_budget) if project.hourly_budget else 0,
            'completion_percentage': (float(project.hours_used or 0) / float(project.hourly_budget or 1)) * 100 if project.hourly_budget else 0
        })
    
    return jsonify(project_list), 200

@projects_bp.route('/', methods=['POST'])
@jwt_required_custom
def create_project():
    """Create a new project for an Admin."""
    current_user = get_jwt_identity()
    data = request.get_json()
    
    # UPDATED: Allow all admin/seller roles to create projects
    if current_user.get('role') not in ['admin', 'tier1_seller', 'tier2_seller']:
        return jsonify({'message': 'You do not have permission to create projects'}), 403
    
    try:
        new_project = Project(
            # client_id now refers to the ID of an Admin record
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
    """Delete a project."""
    current_user = get_jwt_identity()
    user_role = current_user.get('role')
    user_id = current_user.get('id')
    
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404
    
    # UPDATED: Verify access permissions with new models
    admin = Admin.query.get(project.client_id)
    if not admin:
        return jsonify({'message': 'Associated admin account not found'}), 404

    # Check permissions
    if user_role == 'admin':
        # Admin can delete any project
        pass
    elif user_role == 'tier1_seller':
        if admin.tier1_seller_id != user_id:
            return jsonify({'message': 'Access denied'}), 403
    elif user_role == 'tier2_seller':
        if admin.tier2_seller_id != user_id:
            return jsonify({'message': 'Access denied'}), 403
    else:
        return jsonify({'message': 'You do not have permission to delete projects'}), 403
    
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
