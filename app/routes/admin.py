from flask import Blueprint, request, jsonify
from app import db
from app.models import Seller, Tier2Seller, Client, Commission
from app.utils.auth import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_admin_dashboard():
    sellers = Seller.query.all()
    tier2_sellers = Tier2Seller.query.all()
    clients = Client.query.all()
    commissions = Commission.query.all()
    
    dashboard_data = {
        'stats': {
            'total_sellers': len(sellers),
            'total_tier2_sellers': len(tier2_sellers),
            'total_clients': len(clients),
            'total_revenue': sum(c.amount for c in commissions if c.status == 'paid')
        },
        'sellers': [{
            'id': s.id,
            'name': s.name,
            'subdomain': s.subdomain,
            'status': s.status
        } for s in sellers]
    }
    
    return jsonify(dashboard_data), 200