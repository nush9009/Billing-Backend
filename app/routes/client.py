from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Client, Project, User, Report
from app.utils.auth import jwt_required_custom

client_bp = Blueprint('client', __name__)


@client_bp.route('/<client_id>/intake-form', methods=['POST'])
def submit_client_intake_form(client_id):
    """Submit client intake form - ClientIntakeForm.tsx"""
    client = Client.query.get(client_id)
    if not client:
        return jsonify({'message': 'Client not found'}), 404
    
    data = request.get_json()
    
    try:
        # Update client with intake form data
        # You can store the form data in a separate table or as JSON in the client record
        client.intake_form_completed = True
        
        # If you have a separate intake form table, create a record there
        # For now, we'll just mark the form as completed
        
        db.session.commit()
        
        return jsonify({'message': 'Intake form submitted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error submitting intake form: {str(e)}'}), 500

@client_bp.route('/<client_id>/billing', methods=['GET'])
def get_client_billing_details(client_id):
    """Get client billing details - ClientBilling.tsx"""
    client = Client.query.get(client_id)
    if not client:
        return jsonify({'message': 'Client not found'}), 404
    
    try:
        # Get all projects for this client
        projects = Project.query.filter_by(client_id=client_id).all()
        
        # Get billing records for all projects
        billing_records = []
        total_billed = 0
        total_paid = 0
        total_pending = 0
        
        for project in projects:
            # If billing system is implemented
            try:
                from app.models.billing import ProjectBilling
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
                        'billing_type': billing.billing_type,
                        'amount': amount,
                        'status': billing.status,
                        'milestone_description': billing.milestone_description,
                        'due_date': billing.due_date.isoformat() if billing.due_date else None,
                        'paid_date': billing.paid_date.isoformat() if billing.paid_date else None,
                        'created_at': billing.created_at.isoformat() if billing.created_at else None
                    })
            except ImportError:
                # Fallback if billing system not available
                project_value = float(project.project_value or 0)
                budget_spent = float(project.budget_spent or 0)
                
                billing_records.append({
                    'id': project.id,
                    'project_name': project.name,
                    'billing_type': 'project_value',
                    'amount': project_value,
                    'status': 'active',
                    'milestone_description': f'Total project value for {project.name}',
                    'due_date': None,
                    'paid_date': None,
                    'created_at': project.created_at.isoformat() if project.created_at else None
                })
                
                total_billed += project_value
                total_paid += budget_spent
                total_pending += (project_value - budget_spent)
        
        billing_summary = {
            'client_id': client_id,
            'client_name': client.name,
            'client_company': client.company,
            'total_billed': total_billed,
            'total_paid': total_paid,
            'total_pending': total_pending,
            'payment_status': 'current' if total_pending == 0 else 'pending',
            'billing_records': billing_records,
            'total_projects': len(projects),
            'active_projects': len([p for p in projects if p.status == 'active'])
        }
        
        return jsonify(billing_summary), 200
        
    except Exception as e:
        return jsonify({'message': f'Error fetching billing details: {str(e)}'}), 500


