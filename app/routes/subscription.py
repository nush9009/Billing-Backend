from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.project import SubscriptionPlan, Tier1Subscription, Tier2Subscription
from app.models.seller import Tier1Seller, Tier2Seller
from app.routes.seller import get_current_user, is_admin, is_tier1, is_tier2

subscription_bp = Blueprint('subscription', __name__, url_prefix='/subscription')

# ------------------ ADMIN: CREATE MASTER PLANS ------------------
@subscription_bp.route('/admin/plans', methods=['POST'])
@jwt_required()
def create_master_plan():
    current_user = get_current_user(get_jwt_identity())
    if not is_admin(current_user):
        return jsonify({'message': 'Only admins can create master plans'}), 403

    data = request.get_json()
    new_plan = SubscriptionPlan(
        name=data['name'],
        description=data.get('description'),
        price=data['price'],
        billing_cycle=data.get('billing_cycle', 'monthly'),
        admin_commission_pct=data.get('admin_commission_pct'),
        creator_id=current_user['id'],
        creator_type='admin'
    )
    db.session.add(new_plan)
    db.session.commit()
    return jsonify({'message': 'Master plan created successfully', 'plan_id': new_plan.id}), 201

# ------------------ TIER1: CREATE WHITE-LABELED PLANS ------------------
@subscription_bp.route('/tier1/plans', methods=['POST'])
@jwt_required()
def create_tier1_plan():
    current_user = get_current_user(get_jwt_identity())
    if not is_tier1(current_user):
        return jsonify({'message': 'Only Tier1 sellers can create plans'}), 403

    data = request.get_json()
    master_plan = SubscriptionPlan.query.get(data['master_plan_id'])
    if not master_plan or master_plan.creator_type != 'admin':
        return jsonify({'message': 'Master plan not found'}), 404

    new_plan = SubscriptionPlan(
        name=master_plan.name,
        description=master_plan.description,
        price=master_plan.price,
        billing_cycle=master_plan.billing_cycle,
        admin_commission_pct=master_plan.admin_commission_pct,
        tier1_commission_pct=data['tier1_commission_pct'],
        creator_id=current_user['id'],
        creator_type='tier1_seller',
        parent_plan_id=master_plan.id
    )
    db.session.add(new_plan)
    db.session.commit()
    return jsonify({'message': 'Tier1 plan created successfully', 'plan_id': new_plan.id}), 201

# ------------------ TIER1 & TIER2: SUBSCRIBE TO PLANS ------------------
@subscription_bp.route('/subscribe', methods=['POST'])
@jwt_required()
def subscribe_to_plan():
    current_user = get_current_user(get_jwt_identity())
    data = request.get_json()
    plan = SubscriptionPlan.query.get(data['plan_id'])

    if not plan:
        return jsonify({'message': 'Plan not found'}), 404

    if is_tier1(current_user) and plan.creator_type == 'admin':
        new_subscription = Tier1Subscription(
            tier1_seller_id=current_user['id'],
            subscription_plan_id=plan.id
        )
    elif is_tier2(current_user) and plan.creator_type == 'tier1_seller':
        new_subscription = Tier2Subscription(
            tier2_seller_id=current_user['id'],
            subscription_plan_id=plan.id
        )
    else:
        return jsonify({'message': 'You cannot subscribe to this plan'}), 403

    db.session.add(new_subscription)
    db.session.commit()
    return jsonify({'message': 'Subscribed successfully', 'subscription_id': new_subscription.id}), 201

# # ------------------ GET PLANS ------------------
# @subscription_bp.route('/plans', methods=['GET'])
# @jwt_required()
# def get_plans():
#     current_user = get_current_user(get_jwt_identity())
    
#     if is_tier1(current_user):
#         # Tier1 can see Admin plans to subscribe to
#         plans = SubscriptionPlan.query.filter_by(creator_type='admin').all()
#     elif is_tier2(current_user):
#         # Tier2 can see plans created by their Tier1 parent
#         tier2_seller = Tier2Seller.query.get(current_user['id'])
#         plans = SubscriptionPlan.query.filter_by(creator_id=tier2_seller.tier1_seller_id, creator_type='tier1_seller').all()
#     else:
#         # Admin can see all plans
#         plans = SubscriptionPlan.query.all()

#     return jsonify([{
#         'id': plan.id,
#         'name': plan.name,
#         'price': str(plan.price),
#         'creator_type': plan.creator_type
#     } for plan in plans]), 200

@subscription_bp.route('/plans', methods=['GET'])
@jwt_required()
def get_plans():
    current_user = get_current_user(get_jwt_identity())

    # ---------------- Admin ----------------
    if is_admin(current_user):
        plans = SubscriptionPlan.query.all()

    # ---------------- Tier1 Seller ----------------
    elif is_tier1(current_user):
        # Tier1 must see Admin plans + their own plans
        admin_plans = SubscriptionPlan.query.filter_by(creator_type='admin').all()
        tier1_own_plans = SubscriptionPlan.query.filter_by(
            creator_id=current_user['id'],
            creator_type='tier1_seller'
        ).all()
        plans = admin_plans + tier1_own_plans

    # ---------------- Tier2 Seller ----------------
    elif is_tier2(current_user):
        tier2_seller = Tier2Seller.query.get(current_user['id'])
        if not tier2_seller:
            return jsonify({'message': 'Tier2 seller not found'}), 404

        # Tier2 should ONLY see Tier1-created plans from their parent Tier1 seller
        plans = SubscriptionPlan.query.filter(
            SubscriptionPlan.creator_id == tier2_seller.tier1_seller_id,
            SubscriptionPlan.creator_type == 'tier1_seller'
        ).all()

    # ---------------- Others ----------------
    else:
        return jsonify({'message': 'Unauthorized role'}), 403

    # ---------------- Response ----------------
    return jsonify([
        {
            'id': plan.id,
            'name': plan.name,
            'price': str(plan.price),
            'creator_type': plan.creator_type,
            'creator_id': plan.creator_id,
            'billing_cycle': plan.billing_cycle,
            'description': plan.description,
            'admin_commission_pct': str(plan.admin_commission_pct) if plan.admin_commission_pct else None,
            'tier1_commission_pct': str(plan.tier1_commission_pct) if plan.tier1_commission_pct else None,
            'parent_plan_id': plan.parent_plan_id
        }
        for plan in plans
    ]), 200



# ------------------ GET, UPDATE, DELETE SINGLE PLAN ------------------
@subscription_bp.route('/plans/<plan_id>', methods=['GET'])
@jwt_required()
def get_subscription_plan(plan_id):
    plan = SubscriptionPlan.query.get(plan_id)
    if not plan:
        return jsonify({'message': 'Plan not found'}), 404
    return jsonify({
        'id': plan.id,
        'name': plan.name,
        'price': str(plan.price),
        'description': plan.description,
        'creator_type': plan.creator_type,
        'admin_commission_pct': str(plan.admin_commission_pct) if plan.admin_commission_pct else None,
        'tier1_commission_pct': str(plan.tier1_commission_pct) if plan.tier1_commission_pct else None,
    }), 200

@subscription_bp.route('/plans/<plan_id>', methods=['PUT'])
@jwt_required()
def update_subscription_plan(plan_id):
    plan = SubscriptionPlan.query.get(plan_id)
    if not plan:
        return jsonify({'message': 'Plan not found'}), 404

    current_user = get_current_user(get_jwt_identity())
    # Security check: only the creator can update the plan
    if plan.creator_id != current_user['id']:
        return jsonify({'message': 'Unauthorized to update this plan'}), 403

    data = request.get_json()
    plan.name = data.get('name', plan.name)
    plan.price = data.get('price', plan.price)
    plan.description = data.get('description', plan.description)
    
    # Only allow updating relevant commission
    if plan.creator_type == 'admin':
        plan.admin_commission_pct = data.get('admin_commission_pct', plan.admin_commission_pct)
    elif plan.creator_type == 'tier1_seller':
        plan.tier1_commission_pct = data.get('tier1_commission_pct', plan.tier1_commission_pct)

    db.session.commit()
    return jsonify({'message': 'Plan updated successfully'}), 200

@subscription_bp.route('/plans/<plan_id>', methods=['DELETE'])
@jwt_required()
def delete_subscription_plan(plan_id):
    plan = SubscriptionPlan.query.get(plan_id)
    if not plan:
        return jsonify({'message': 'Plan not found'}), 404

    current_user = get_current_user(get_jwt_identity())
    # Security check: only the creator can delete the plan
    if plan.creator_id != current_user['id']:
        return jsonify({'message': 'Unauthorized to delete this plan'}), 403
        
    # Optional: Add check here to prevent deletion if plan has active subscriptions

    db.session.delete(plan)
    db.session.commit()
    return jsonify({'message': 'Plan deleted successfully'}), 200







