from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
# UPDATED: Import the new Admin model and other necessary models
from app.models import Admin, Project, User, Report

# The blueprint name is kept as 'client' to match the registration in __init__.py
client_bp = Blueprint('client', __name__)

# NOTE: A decorator like this would typically live in a separate app/utils/auth.py file
def client_user_required(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user = get_jwt_identity()
        # This role should match what you set in your auth.py login route for client users
        if current_user.get('role') != 'client': 
            return jsonify(message="Client User access required"), 403
        return fn(*args, **kwargs)
    return wrapper

@client_bp.route('/dashboard', methods=['GET'])
@client_user_required
def client_user_dashboard():
    """Provides a dashboard for the logged-in Client User."""
    current_user = get_jwt_identity()
    # The token for a client user should contain the ID of the Admin company they belong to.
    # We will get this from the 'client_id' field in the token, which links to the Admin record.
    admin_id = current_user.get('client_id')

    if not admin_id:
        return jsonify(message="Admin ID (client_id) not found in token"), 400

    try:
        # UPDATED: Query the Admin model
        admin_record = Admin.query.get(admin_id)
        if not admin_record:
            return jsonify(message="Associated Admin account not found"), 404

        projects = Project.query.filter_by(client_id=admin_id).all()
        active_projects = [p for p in projects if p.status == 'active']
        
        return jsonify({
            'company_name': admin_record.company,
            'stats': {
                'total_projects': len(projects),
                'active_projects': len(active_projects),
            },
            'projects': [{'id': p.id, 'name': p.name, 'status': p.status} for p in projects]
        }), 200
    except Exception as e:
        return jsonify(message=f"An error occurred: {str(e)}"), 500

@client_bp.route('/<admin_id>/intake-form', methods=['POST'])
def submit_client_intake_form(admin_id):
    """Submit client intake form - ClientIntakeForm.tsx"""
    # UPDATED: Query the Admin model
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({'message': 'Admin account not found'}), 404
    
    data = request.get_json()
    
    try:
        admin.intake_form_completed = True
        # Here you would add logic to save other form data from `data`
        db.session.commit()
        return jsonify({'message': 'Intake form submitted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error submitting intake form: {str(e)}'}), 500

@client_bp.route('/<admin_id>/billing', methods=['GET'])
def get_client_billing_details(admin_id):
    """Get client billing details - ClientBilling.tsx"""
    # UPDATED: Query the Admin model
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify({'message': 'Admin account not found'}), 404
    
    try:
        projects = Project.query.filter_by(client_id=admin_id).all()
        billing_records = []
        total_billed = 0
        total_paid = 0
        total_pending = 0
        
        from app.models.billing import ProjectBilling
        for project in projects:
            project_billings = ProjectBilling.query.filter_by(project_id=project.id).all()
            for billing in project_billings:
                amount = float(billing.amount)
                total_billed += amount
                if billing.status == 'paid':
                    total_paid += amount
                elif billing.status in ['pending', 'invoiced']:
                    total_pending += amount
                
                billing_records.append({
                    'id': billing.id,
                    'project_name': project.name,
                    'amount': amount,
                    'status': billing.status,
                    'due_date': billing.due_date.isoformat() if billing.due_date else None,
                })

        return jsonify({
            'client_id': admin_id,
            'client_name': admin.name,
            'client_company': admin.company,
            'total_billed': total_billed,
            'total_paid': total_paid,
            'total_pending': total_pending,
            'billing_records': billing_records
        }), 200
    except Exception as e:
        return jsonify({'message': f'Error fetching billing details: {str(e)}'}), 500

