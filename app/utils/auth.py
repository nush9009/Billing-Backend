from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity,get_jwt

def jwt_required_custom(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'message': str(e)}), 401
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            verify_jwt_in_request()
            current_user = get_jwt_identity()
            claims = get_jwt()
            if claims.get('role') != 'admin':
                return jsonify({'message': 'Admin access required'}), 403
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'message': 'Token is invalid'}), 401
    return decorated