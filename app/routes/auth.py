from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity,
    create_refresh_token, get_jwt
)
from app import db, bcrypt
from app.models import Tier1Seller, Tier2Seller, Admin
from datetime import timedelta

auth_bp = Blueprint('auth', __name__)

# ------------------ REGISTER ------------------
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Request body must be JSON'}), 400

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    user_type = data.get('user_type')

    if not name or not email or not password or not user_type:
        return jsonify({'message': 'All fields are required'}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

    try:
        if user_type == 'admin':
            if Admin.query.filter_by(email=email).first():
                return jsonify({'message': 'Admin already exists'}), 400
            new_user = Admin(
                name=name,
                email=email,
                password_hash=hashed_pw
            )
            db.session.add(new_user)

        elif user_type == 'tier1_seller':
            if Tier1Seller.query.filter_by(admin_email=email).first():
                return jsonify({'message': 'Tier1 seller already exists'}), 400
            subdomain = data.get('subdomain')  # optional
            new_user = Tier1Seller(
                name=name,
                admin_email=email,
                password_hash=hashed_pw,
                subdomain=subdomain
            )
            db.session.add(new_user)

        elif user_type == 'tier2_seller':
            if Tier2Seller.query.filter_by(admin_email=email).first():
                return jsonify({'message': 'Tier2 seller already exists'}), 400

            # Required: tier1_seller_id
            tier1_seller_id = data.get('tier1_seller_id')
            if not tier1_seller_id:
                return jsonify({'message': 'tier1_seller_id is required for Tier2 Seller'}), 400

            subdomain = data.get('subdomain')  # optional

            new_user = Tier2Seller(
                name=name,
                admin_email=email,
                password_hash=hashed_pw,
                tier1_seller_id=tier1_seller_id,
                subdomain=subdomain
            )
            db.session.add(new_user)

        else:
            return jsonify({'message': 'Invalid user_type'}), 400

        db.session.commit()
        return jsonify({'message': f'{user_type} registered successfully'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error: {str(e)}'}), 500


# ------------------ LOGIN ------------------
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Request body must be JSON'}), 400

    email = data.get('email')
    password = data.get('password')
    user_type = data.get('user_type')

    if not email or not password or not user_type:
        return jsonify({'message': 'Email, password, and user_type are required'}), 400

    user = None
    user_identity = {}

    try:
        if user_type == 'admin':
            user = Admin.query.filter_by(email=email).first()
            if user and bcrypt.check_password_hash(user.password_hash, password):
                user_identity = {
                    'id': str(user.id),
                    'role': 'admin',
                    'email': user.email,
                    'name': user.name
                }

        elif user_type == 'tier1_seller':
            user = Tier1Seller.query.filter_by(admin_email=email).first()
            if user and bcrypt.check_password_hash(user.password_hash, password):
                user_identity = {
                    'id': str(user.id),
                    'role': 'tier1_seller',
                    'email': user.admin_email,
                    'name': user.name
                }

        elif user_type == 'tier2_seller':
            user = Tier2Seller.query.filter_by(admin_email=email).first()
            if user and bcrypt.check_password_hash(user.password_hash, password):
                user_identity = {
                    'id': str(user.id),
                    'role': 'tier2_seller',
                    'email': user.admin_email,
                    'name': user.name
                }

        if user and user_identity:
            # ✅ identity must be string
            access_token = create_access_token(
                identity=user_identity["id"],
                additional_claims={
                    "role": user_identity["role"],
                    "email": user_identity["email"],
                    "name": user_identity["name"]
                },
                expires_delta=timedelta(hours=1)
            )
            refresh_token = create_refresh_token(
                identity=user_identity["id"],
                additional_claims={
                    "role": user_identity["role"],
                    "email": user_identity["email"],
                    "name": user_identity["name"]
                }
            )
            return jsonify({
                'message': 'Login successful',
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': user_identity
            }), 200

        return jsonify({'message': 'Invalid credentials or user type'}), 401

    except Exception as e:
        return jsonify({'message': f'An internal error occurred: {str(e)}'}), 500


# ------------------ PROFILE ------------------
@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = get_jwt_identity()
    claims = get_jwt()
    return jsonify({
        'id': user_id,
        'role': claims.get("role"),
        'email': claims.get("email"),
        'name': claims.get("name")
    }), 200


# ------------------ REFRESH TOKEN ------------------
@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    user_id = get_jwt_identity()
    claims = get_jwt()
    new_access = create_access_token(
        identity=user_id,
        additional_claims={
            "role": claims.get("role"),
            "email": claims.get("email"),
            "name": claims.get("name")
        },
        expires_delta=timedelta(hours=1)
    )
    return jsonify({'access_token': new_access}), 200


# ------------------ LOGOUT ------------------
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({'message': 'Logout successful'}), 200


# ------------------ GET ALL USERS ------------------
@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    claims = get_jwt()

    # ✅ Only allow admin to view all users
    if claims.get("role") != "admin":
        return jsonify({'message': 'Only admins can view all users'}), 403

    try:
        admins = Admin.query.all()
        tier1_sellers = Tier1Seller.query.all()
        tier2_sellers = Tier2Seller.query.all()

        users = {
            "admins": [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "email": a.email
                } for a in admins
            ],
            "tier1_sellers": [
                {
                    "id": str(t1.id),
                    "name": t1.name,
                    "admin_email": t1.admin_email,
                    "subdomain": t1.subdomain
                } for t1 in tier1_sellers
            ],
            "tier2_sellers": [
                {
                    "id": str(t2.id),
                    "name": t2.name,
                    "admin_email": t2.admin_email,
                    "tier1_seller_id": str(t2.tier1_seller_id),
                    "subdomain": t2.subdomain
                } for t2 in tier2_sellers
            ]
        }

        return jsonify(users), 200

    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500
