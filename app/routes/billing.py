from flask import Blueprint, request, jsonify
from app import db
from app.utils.auth import jwt_required_custom
from app.utils.billing_calculator import BillingCalculator

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/create', methods=['POST'])
@jwt_required_custom
def create_billing_record():
    data = request.get_json()
    try:
        new_record = BillingCalculator.create_project_billing(
            project_id=data.get('project_id'),
            billing_type=data.get('billing_type'),
            amount=data.get('amount'),
            hours_worked=data.get('hours_worked'),
            milestone_description=data.get('milestone_description')
        )
        return jsonify({
            'message': 'Billing record created successfully',
            'record_id': new_record.id
        }), 201
    except Exception as e:
        return jsonify({'message': f'Error creating billing record: {str(e)}'}), 400

@billing_bp.route('/project/<project_id>', methods=['GET'])
@jwt_required_custom
def get_project_billing(project_id):
    summary = BillingCalculator.calculate_project_billing(project_id)
    if not summary:
        return jsonify({'message': 'Project not found'}), 404
    return jsonify(summary), 200

@billing_bp.route('/invoice/generate', methods=['POST'])
@jwt_required_custom
def generate_invoice():
    data = request.get_json()
    client_id = data.get('client_id')
    billing_records_ids = data.get('billing_records_ids')

    if not client_id or not billing_records_ids:
        return jsonify({'message': 'Client ID and billing record IDs are required'}), 400

    try:
        invoice = BillingCalculator.generate_invoice_for_client(client_id, billing_records_ids)
        if not invoice:
            return jsonify({'message': 'No pending billing records found for invoicing'}), 404

        return jsonify({
            'message': 'Invoice generated successfully',
            'invoice_number': invoice.invoice_number,
            'total_amount': float(invoice.total_amount)
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error generating invoice: {str(e)}'}), 400