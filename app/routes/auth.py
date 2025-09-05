from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app import db, bcrypt
from app.models import Seller, Tier2Seller, User, Client

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Updated login to match frontend expectations"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user_type = data.get('user_type', 'client')  # seller, tier2_seller, client
    
    if not email or not password:
        return jsonify({'message': 'Email and password required'}), 400
    
    user = None
    user_data = {}
    
    if user_type == 'seller':
        user = Seller.query.filter_by(admin_email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            user_data = {
                'id': user.id,
                'email': email,
                'name': user.name,
                'user_type': 'seller',
                'company': user.name
            }
    elif user_type == 'tier2_seller':
        user = Tier2Seller.query.filter_by(admin_email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            user_data = {
                'id': user.id,
                'email': email,
                'name': user.name,
                'user_type': 'tier2_seller',
                'company': user.name
            }
    else:  # client
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            client = Client.query.get(user.client_id)
            user_data = {
                'id': user.id,
                'email': email,
                'name': user.name,
                'user_type': 'client',
                'company': client.company if client else None
            }
    
    if user and user_data:
        access_token = create_access_token(identity=user_data)
        return jsonify({
            'token': access_token,  # Frontend expects 'token', not 'access_token'
            'user': user_data
        }), 200
    
    return jsonify({'message': 'Invalid credentials'}), 401