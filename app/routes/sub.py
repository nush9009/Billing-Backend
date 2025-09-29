# from flask import Blueprint, request, jsonify
# from flask_jwt_extended import jwt_required, get_jwt_identity
# from app import db
# from app.models import  Admin
# from app.models.project import SubscriptionPlan
# from app.utils.auth import get_current_user, is_admin

# subscription_bp = Blueprint('subscription', __name__, url_prefix='/subscription-plans')

# # ---------------- CREATE ----------------
# @subscription_bp.route('/', methods=['POST'])
# @jwt_required()
# def create_subscription_plan():
#     current_user = get_current_user(get_jwt_identity())
#     if not is_admin(current_user):
#         return jsonify({'message': 'Access denied'}), 403

#     data = request.get_json()
#     new_plan = SubscriptionPlan(
#         name=data.get('name'),
#         description=data.get('description'),
#         price=data.get('price'),
#         billing_cycle=data.get('billing_cycle', 'monthly'),
#         admin_id=current_user['id']
#     )
#     db.session.add(new_plan)
#     db.session.commit()
#     return jsonify({'message': 'Subscription plan created', 'id': new_plan.id}), 201


# # ---------------- READ ALL ----------------
# @subscription_bp.route('/', methods=['GET'])
# @jwt_required()
# def get_subscription_plans():
#     plans = SubscriptionPlan.query.all()
#     result = []
#     for plan in plans:
#         result.append({
#             'id': plan.id,
#             'name': plan.name,
#             'description': plan.description,
#             'price': str(plan.price),
#             'billing_cycle': plan.billing_cycle,
#             'status': plan.status,
#             'admin_id': plan.admin_id,
#             'created_at': plan.created_at,
#             'updated_at': plan.updated_at
#         })
#     return jsonify(result), 200


# # ---------------- READ SINGLE ----------------
# @subscription_bp.route('/<plan_id>', methods=['GET'])
# @jwt_required()
# def get_subscription_plan(plan_id):
#     plan = SubscriptionPlan.query.get(plan_id)
#     if not plan:
#         return jsonify({'message': 'Subscription plan not found'}), 404
    
#     return jsonify({
#         'id': plan.id,
#         'name': plan.name,
#         'description': plan.description,
#         'price': str(plan.price),
#         'billing_cycle': plan.billing_cycle,
#         'status': plan.status,
#         'admin_id': plan.admin_id,
#         'created_at': plan.created_at,
#         'updated_at': plan.updated_at
#     }), 200


# # ---------------- UPDATE ----------------
# @subscription_bp.route('/<plan_id>', methods=['PUT'])
# @jwt_required()
# def update_subscription_plan(plan_id):
#     current_user = get_current_user(get_jwt_identity())
#     if not is_admin(current_user):
#         return jsonify({'message': 'Access denied'}), 403

#     plan = SubscriptionPlan.query.get(plan_id)
#     if not plan:
#         return jsonify({'message': 'Subscription plan not found'}), 404

#     data = request.get_json()
#     plan.name = data.get('name', plan.name)
#     plan.description = data.get('description', plan.description)
#     plan.price = data.get('price', plan.price)
#     plan.billing_cycle = data.get('billing_cycle', plan.billing_cycle)
#     plan.status = data.get('status', plan.status)

#     db.session.commit()
#     return jsonify({'message': 'Subscription plan updated'}), 200


# # ---------------- DELETE ----------------
# @subscription_bp.route('/<plan_id>', methods=['DELETE'])
# @jwt_required()
# def delete_subscription_plan(plan_id):
#     current_user = get_current_user(get_jwt_identity())
#     if not is_admin(current_user):
#         return jsonify({'message': 'Access denied'}), 403

#     plan = SubscriptionPlan.query.get(plan_id)
#     if not plan:
#         return jsonify({'message': 'Subscription plan not found'}), 404

#     db.session.delete(plan)
#     db.session.commit()
#     return jsonify({'message': 'Subscription plan deleted'}), 200
