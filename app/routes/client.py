from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Client, Project, User, Report
from app.utils.auth import jwt_required_custom

client_bp = Blueprint('client', __name__)

@client_bp.route('/dashboard', methods=['GET'])
@jwt_required_custom
def get_client_dashboard():
    current_user = get_jwt_identity()
    user_id = current_user.get('id')
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    client = Client.query.get(user.client_id)
    projects = Project.query.filter_by(client_id=client.id).all()
    reports = Report.query.filter_by(client_id=client.id).all()
    
    dashboard_data = {
        'client': {
            'id': client.id,
            'name': client.name,
            'company': client.company
        },
        'projects': [{
            'id': p.id,
            'name': p.name,
            'status': p.status,
            'project_type': p.project_type
        } for p in projects],
        'reports': [{
            'id': r.id,
            'title': r.title,
            'status': r.status,
            'created_at': r.created_at.isoformat()
        } for r in reports]
    }
    
    return jsonify(dashboard_data), 200