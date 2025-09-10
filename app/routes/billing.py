from flask import Blueprint, request, jsonify
from app import db
from app.utils.auth import jwt_required_custom
from app.models import Project, Admin
from app.models.billing import ProjectBilling, Invoice
from datetime import date, timedelta
import uuid

billing_bp = Blueprint('billing', __name__)

# ---------------- CREATE BILLING RECORD ----------------
@billing_bp.route('/create', methods=['POST'])
@jwt_required_custom
def create_billing_record():
    """Create a new billing record for a project."""
    data = request.get_json()
    try:
        project = Project.query.get(data.get('project_id'))
        if not project:
            return jsonify({'message': 'Project not found'}), 404

        new_record = ProjectBilling(
            project_id=project.id,
            billing_type=data.get('billing_type'),
            amount=data.get('amount', 0),
            hours_worked=data.get('hours_worked', 0),
            milestone_description=data.get('milestone_description'),
            status='pending',
            due_date=data.get('due_date', date.today())
        )
        db.session.add(new_record)

        # Update project's budget spent
        from decimal import Decimal

        project.budget_spent = (project.budget_spent or Decimal('0')) + Decimal(new_record.amount)
        if new_record.hours_worked:
            project.hours_used = (project.hours_used or Decimal('0')) + Decimal(new_record.hours_worked)


        db.session.commit()

        return jsonify({
            'message': 'Billing record created successfully',
            'record_id': new_record.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 400


# ---------------- GET PROJECT BILLING ----------------
@billing_bp.route('/project/<project_id>', methods=['GET'])
@jwt_required_custom
def get_project_billing(project_id):
    """Get all billing records and summary for a project."""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404

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
                'invoice_date': r.invoice_date.isoformat() if r.invoice_date else None,
                'paid_date': r.paid_date.isoformat() if r.paid_date else None
            } for r in records
        ]
    }
    return jsonify(summary), 200


@billing_bp.route('/invoice/generate', methods=['POST'])
@jwt_required_custom
def generate_invoice():
    """Generate an invoice from pending billing records for a project."""
    data = request.get_json()
    billing_record_ids = data.get('billing_record_ids')
    if not billing_record_ids:
        return jsonify({'message': 'Billing record IDs are required'}), 400

    try:
        # Get pending billing records
        records_to_invoice = ProjectBilling.query.filter(
            ProjectBilling.id.in_(billing_record_ids),
            ProjectBilling.status == 'pending'
        ).all()

        if not records_to_invoice:
            return jsonify({'message': 'No pending billing records found'}), 404

        subtotal = sum(float(r.amount) for r in records_to_invoice)
        tax = subtotal * 0.10  # 10% tax
        total = subtotal + tax

        new_invoice = Invoice(
            invoice_number=f"INV-{uuid.uuid4().hex[:6].upper()}",
            subtotal=subtotal,
            tax_amount=tax,
            total_amount=total,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status='sent',
            invoice_data=[{
                'billing_id': r.id,
                'project_id': r.project_id,
                'amount': float(r.amount),
                'type': r.billing_type,
                'description': r.milestone_description
            } for r in records_to_invoice]
        )
        db.session.add(new_invoice)

        # Update billing records to 'invoiced'
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
        return jsonify({'message': f'Error: {str(e)}'}), 400



# ---------------- GET INVOICE BY ID ----------------
@billing_bp.route('/invoice/<invoice_id>', methods=['GET'])
@jwt_required_custom
def get_invoice(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({'message': 'Invoice not found'}), 404

    data = {
        'id': invoice.id,
        'invoice_number': invoice.invoice_number,
        'client_id': invoice.client_id,
        'subtotal': float(invoice.subtotal),
        'tax_amount': float(invoice.tax_amount),
        'total_amount': float(invoice.total_amount),
        'status': invoice.status,
        'issue_date': invoice.issue_date.isoformat(),
        'due_date': invoice.due_date.isoformat(),
        'paid_date': invoice.paid_date.isoformat() if invoice.paid_date else None,
        'line_items': invoice.invoice_data
    }
    return jsonify(data), 200


# ---------------- LIST ALL INVOICES FOR A CLIENT ----------------
@billing_bp.route('/invoices/client/<client_id>', methods=['GET'])
@jwt_required_custom
def list_invoices(client_id):
    invoices = Invoice.query.filter_by(client_id=client_id).all()
    return jsonify([
        {
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'status': inv.status,
            'total_amount': float(inv.total_amount),
            'issue_date': inv.issue_date.isoformat(),
            'due_date': inv.due_date.isoformat()
        } for inv in invoices
    ]), 200


# ---------------- MARK INVOICE AS PAID ----------------
@billing_bp.route('/invoice/<invoice_id>/pay', methods=['POST'])
@jwt_required_custom
def mark_invoice_paid(invoice_id):
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({'message': 'Invoice not found'}), 404
    if invoice.status == 'paid':
        return jsonify({'message': 'Invoice already paid'}), 400

    invoice.status = 'paid'
    invoice.paid_date = date.today()

    # Update related billing records
    for billing_item in invoice.invoice_data:
        record = ProjectBilling.query.get(billing_item['billing_id'])
        if record:
            record.status = 'paid'
            record.paid_date = date.today()

    db.session.commit()
    return jsonify({'message': 'Invoice marked as paid'}), 200
