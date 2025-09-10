from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import Tier1Seller, Tier2Seller, Admin
from datetime import datetime

seller_bp = Blueprint('seller', __name__)

# ------------------ HELPER ------------------
def get_current_user(user_id):
    admin = Admin.query.get(user_id)
    if admin:
        return {"id": admin.id, "role": "admin"}

    tier1 = Tier1Seller.query.get(user_id)
    if tier1:
        return {"id": tier1.id, "role": "tier1_seller"}

    tier2 = Tier2Seller.query.get(user_id)
    if tier2:
        return {"id": tier2.id, "role": "tier2_seller"}

    return None

def is_admin(user):
    return user and user.get('role') == 'admin'

def is_tier1(user):
    return user and user.get('role') == 'tier1_seller'

def is_tier2(user):
    return user and user.get('role') == 'tier2_seller'


# ------------------ CREATE TIER1 SELLER ------------------
@seller_bp.route('/tier1', methods=['POST'])
@jwt_required()
def create_tier1():
    current_user = get_current_user(get_jwt_identity())
    if not is_admin(current_user):
        return jsonify({'message': 'Only admins can create Tier1 sellers'}), 403

    data = request.get_json()
    if not data or not data.get('name') or not data.get('admin_email'):
        return jsonify({'message': 'Name and admin_email are required'}), 400

    new_tier1 = Tier1Seller(
        name=data['name'],
        admin_email=data['admin_email'],
        password_hash=data.get('password_hash', ''),  # normally through register
        subdomain=data.get('subdomain')
    )
    db.session.add(new_tier1)
    db.session.commit()

    return jsonify({'message': 'Tier1 seller created successfully', 'id': new_tier1.id}), 201


# ------------------ GET ALL TIER1 SELLERS ------------------
@seller_bp.route('/tier1', methods=['GET'])
@jwt_required()
def get_tier1_sellers():
    sellers = Tier1Seller.query.all()
    result = [
        {'id': s.id, 'name': s.name, 'admin_email': s.admin_email, 'subdomain': s.subdomain}
        for s in sellers
    ]
    return jsonify(result), 200


# ------------------ GET SINGLE TIER1 SELLER ------------------
@seller_bp.route('/tier1/<seller_id>', methods=['GET'])
@jwt_required()
def get_tier1_seller(seller_id):
    seller = Tier1Seller.query.get(seller_id)
    if not seller:
        return jsonify({'message': 'Tier1 seller not found'}), 404

    return jsonify({'id': seller.id, 'name': seller.name, 'admin_email': seller.admin_email, 'subdomain': seller.subdomain}), 200


# ------------------ UPDATE TIER1 SELLER ------------------
@seller_bp.route('/tier1/<seller_id>', methods=['PUT'])
@jwt_required()
def update_tier1(seller_id):
    current_user = get_current_user(get_jwt_identity())
    if not is_admin(current_user):
        return jsonify({'message': 'Only admins can update Tier1 sellers'}), 403

    seller = Tier1Seller.query.get(seller_id)
    if not seller:
        return jsonify({'message': 'Tier1 seller not found'}), 404

    data = request.get_json()
    seller.name = data.get('name', seller.name)
    seller.subdomain = data.get('subdomain', seller.subdomain)

    db.session.commit()
    return jsonify({'message': 'Tier1 seller updated successfully'}), 200


# ------------------ DELETE TIER1 SELLER ------------------
@seller_bp.route('/tier1/<seller_id>', methods=['DELETE'])
@jwt_required()
def delete_tier1(seller_id):
    current_user = get_current_user(get_jwt_identity())
    if not is_admin(current_user):
        return jsonify({'message': 'Only admins can delete Tier1 sellers'}), 403

    seller = Tier1Seller.query.get(seller_id)
    if not seller:
        return jsonify({'message': 'Tier1 seller not found'}), 404

    db.session.delete(seller)
    db.session.commit()
    return jsonify({'message': 'Tier1 seller deleted successfully'}), 200


# ===============================================================
# ------------------ TIER2 SELLERS ------------------------------
# ===============================================================

# ------------------ CREATE TIER2 SELLER ------------------
@seller_bp.route('/tier2', methods=['POST'])
@jwt_required()
def create_tier2():
    current_user = get_current_user(get_jwt_identity())

    data = request.get_json()
    if not data or not data.get('name') or not data.get('admin_email'):
        return jsonify({'message': 'Name and admin_email are required'}), 400

    # If Admin is creating, they must provide tier1_seller_id
    tier1_seller_id = None
    if is_tier1(current_user):
        tier1_seller_id = current_user['id']
    elif is_admin(current_user):
        tier1_seller_id = data.get('tier1_seller_id')
        if not tier1_seller_id:
            return jsonify({'message': 'tier1_seller_id is required when admin creates Tier2 seller'}), 400
    else:
        return jsonify({'message': 'Unauthorized'}), 403

    new_tier2 = Tier2Seller(
        name=data['name'],
        admin_email=data['admin_email'],
        password_hash=data.get('password_hash', ''),  # normally through register
        tier1_seller_id=tier1_seller_id,
        subdomain=data.get('subdomain')
    )
    db.session.add(new_tier2)
    db.session.commit()

    return jsonify({'message': 'Tier2 seller created successfully', 'id': new_tier2.id}), 201


# ------------------ GET ALL TIER2 SELLERS ------------------
@seller_bp.route('/tier2', methods=['GET'])
@jwt_required()
def get_tier2_sellers():
    current_user = get_current_user(get_jwt_identity())

    if is_tier1(current_user):
        sellers = Tier2Seller.query.filter_by(tier1_seller_id=current_user['id']).all()
    elif is_admin(current_user):
        sellers = Tier2Seller.query.all()
    else:
        return jsonify({'message': 'Unauthorized'}), 403

    result = [
        {'id': s.id, 'name': s.name, 'admin_email': s.admin_email, 'subdomain': s.subdomain}
        for s in sellers
    ]
    return jsonify(result), 200


# ------------------ GET SINGLE TIER2 SELLER ------------------
@seller_bp.route('/tier2/<seller_id>', methods=['GET'])
@jwt_required()
def get_tier2_seller(seller_id):
    current_user = get_current_user(get_jwt_identity())
    seller = Tier2Seller.query.get(seller_id)
    if not seller:
        return jsonify({'message': 'Tier2 seller not found'}), 404

    # Restrict Tier2: can only view their own profile
    if is_tier2(current_user) and current_user['id'] != seller.id:
        return jsonify({'message': 'Unauthorized'}), 403

    return jsonify({
        'id': seller.id,
        'name': seller.name,
        'admin_email': seller.admin_email,
        'subdomain': seller.subdomain
    }), 200


# ------------------ UPDATE TIER2 SELLER ------------------
@seller_bp.route('/tier2/<seller_id>', methods=['PUT'])
@jwt_required()
def update_tier2(seller_id):
    current_user = get_current_user(get_jwt_identity())
    seller = Tier2Seller.query.get(seller_id)

    if not seller:
        return jsonify({'message': 'Tier2 seller not found'}), 404

    if not (is_admin(current_user) or (is_tier1(current_user) and seller.tier1_seller_id == current_user['id'])):
        return jsonify({'message': 'Unauthorized'}), 403

    data = request.get_json()
    seller.name = data.get('name', seller.name)
    seller.subdomain = data.get('subdomain', seller.subdomain)

    db.session.commit()
    return jsonify({'message': 'Tier2 seller updated successfully'}), 200


# ------------------ DELETE TIER2 SELLER ------------------
@seller_bp.route('/tier2/<seller_id>', methods=['DELETE'])
@jwt_required()
def delete_tier2(seller_id):
    current_user = get_current_user(get_jwt_identity())
    seller = Tier2Seller.query.get(seller_id)

    if not seller:
        return jsonify({'message': 'Tier2 seller not found'}), 404

    if not (is_admin(current_user) or (is_tier1(current_user) and seller.tier1_seller_id == current_user['id'])):
        return jsonify({'message': 'Unauthorized'}), 403

    db.session.delete(seller)
    db.session.commit()
    return jsonify({'message': 'Tier2 seller deleted successfully'}), 200
