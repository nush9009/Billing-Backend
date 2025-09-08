from flask import Blueprint, request, jsonify
from app import db
from app.models import Seller, Tier2Seller, Client, Commission, Project # Added Project
from app.utils.auth import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_admin_dashboard():
    sellers = Seller.query.all()
    tier2_sellers = Tier2Seller.query.all()
    clients = Client.query.all()
    commissions = Commission.query.all()
    
    # Calculate dashboard metrics
    total_revenue = sum(c.amount for c in commissions if c.status == 'paid')
    active_projects = Project.query.filter_by(status='active').count()
    growth_rate = 12.5 # Mock growth rate

    dashboard_data = {
        'metrics': {
            'total_clients': len(clients),
            'active_projects': active_projects,
            'monthly_revenue': total_revenue,
            'growth_rate': growth_rate
        },
        'recent_activity': [
            {'action': 'New Tier-1 Seller registered', 'company': 'TechCorp Solutions', 'time': '2 hours ago', 'status': 'pending'},
            {'action': 'Client payment received', 'company': 'DataFlow Inc', 'time': '4 hours ago', 'status': 'completed'},
            {'action': 'Tier-2 Seller approved', 'company': 'Analytics Pro', 'time': '6 hours ago', 'status': 'approved'},
        ],
        
        'sellers': [{
            'id': s.id,
            'name': s.name,
            'subdomain': s.subdomain,
            'status': s.status
        } for s in sellers]
    }

    return jsonify(dashboard_data), 200
