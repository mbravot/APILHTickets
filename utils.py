from flask import jsonify
from flask_jwt_extended import get_jwt_identity
from functools import wraps
from models import Usuario

def role_required(required_role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_user_id = get_jwt_identity()
            user = Usuario.query.get(current_user_id)
            
            if not user or user.rol_obj.rol != required_role:
                return jsonify({'message': 'No tienes permisos para acceder a esta ruta'}), 403
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


#hola