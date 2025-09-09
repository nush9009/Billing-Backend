from flask import Blueprint, request, jsonify
from app import db
from app.utils.auth import jwt_required_custom
# UPDATED: Import the necessary models directly
from app.models import Project, Admin
from app.models.billing import ProjectBilling, Invoice
from sqlalchemy.orm import joinedload
from datetime import date
import uuid

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/create', methods=['POST'])
@jwt_required_custom
def create_billing_record():
    """Creates a new billing record for a project."""
    data = request.get_json()
    try:
        # This logic is likely okay as it's based on project_id
        new_record = ProjectBilling(
            project_id=data.get('project_id'),
            billing_type=data.get('billing_type'),
            amount=data.get('amount'),
            hours_worked=data.get('hours_worked'),
            milestone_description=data.get('milestone_description'),
            status='pending', # Default status
            due_date=date.today() # Example due date
        )
        db.session.add(new_record)
        
        # Update the project's budget_spent
        project = Project.query.get(data.get('project_id'))
        if project:
            project.budget_spent = (project.budget_spent or 0) + float(data.get('amount', 0))
        
        db.session.commit()
        
        return jsonify({
            'message': 'Billing record created successfully',
            'record_id': new_record.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating billing record: {str(e)}'}), 400

@billing_bp.route('/project/<project_id>', methods=['GET'])
@jwt_required_custom
def get_project_billing(project_id):
    """Gets a summary of all billing for a specific project."""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404

    # Use the relationship to get all billing records
    records = project.billing_records
    
    total_billed = sum(float(r.amount) for r in records)
    total_paid = sum(float(r.amount) for r in records if r.status == 'paid')
    
    summary = {
        'project_id': project.id,
        'project_name': project.name,
        'project_value': float(project.project_value or 0),
        'total_billed': total_billed,
        'total_paid': total_paid,
        'amount_due': total_billed - total_paid,
        'records': [
            {
                'id': r.id,
                'type': r.billing_type,
                'amount': float(r.amount),
                'status': r.status,
                'description': r.milestone_description,
                'due_date': r.due_date.isoformat() if r.due_date else None,
                'paid_date': r.paid_date.isoformat() if r.paid_date else None
            } for r in records
        ]
    }
    return jsonify(summary), 200

@billing_bp.route('/invoice/generate', methods=['POST'])
@jwt_required_custom
def generate_invoice():
    """Generates an invoice for a specific client (Admin) from a list of billing records."""
    data = request.get_json()
    # UPDATED: The client_id now refers to an Admin's ID
    admin_id = data.get('client_id')
    billing_record_ids = data.get('billing_records_ids')

    if not admin_id or not billing_record_ids:
        return jsonify({'message': 'Admin ID and billing record IDs are required'}), 400

    # UPDATED: Verify the Admin exists
    admin = Admin.query.get(admin_id)
    if not admin:
        return jsonify(message="Admin account not found"), 404

    try:
        # Find all pending billing records that match the provided IDs and belong to the client's projects
        records_to_invoice = db.session.query(ProjectBilling).join(Project).filter(
            Project.client_id == admin_id,
            ProjectBilling.id.in_(billing_record_ids),
            ProjectBilling.status == 'pending'
        ).all()

        if not records_to_invoice:
            return jsonify({'message': 'No valid pending billing records found for invoicing'}), 404
            
        subtotal = sum(float(r.amount) for r in records_to_invoice)
        # In a real app, tax would be calculated based on rules
        tax = subtotal * 0.10 
        total = subtotal + tax

        # Create the new invoice
        new_invoice = Invoice(
            client_id=admin_id,
            invoice_number=f"INV-{uuid.uuid4().hex[:6].upper()}",
            subtotal=subtotal,
            tax_amount=tax,
            total_amount=total,
            issue_date=date.today(),
            due_date=date.today() + db.timedelta(days=30),
            status='sent'
        )
        db.session.add(new_invoice)
        
        # Update the status of the billing records to 'invoiced'
        for record in records_to_invoice:
            record.status = 'invoiced'
            record.invoice_date = date.today()

        db.session.commit()

        return jsonify({
            'message': 'Invoice generated successfully',
            'invoice_number': new_invoice.invoice_number,
            'total_amount': float(new_invoice.total_amount)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error generating invoice: {str(e)}'}),
