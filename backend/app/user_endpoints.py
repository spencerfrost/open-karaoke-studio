from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from .models import SessionLocal, User

user_bp = Blueprint('users', __name__, url_prefix='/users')

@user_bp.route('/register', methods=['POST'])
def register_user():
    """Register a new user with an optional password."""
    data = request.json
    session = SessionLocal()
    try:
        if session.query(User).filter(User.username == data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400

        user = User(username=data['username'], display_name=data.get('display_name'))
        if 'password' in data and data['password']:
            user.set_password(data['password'])

        session.add(user)
        session.commit()
        return jsonify({'success': True, 'id': user.id}), 201
    finally:
        session.close()

@user_bp.route('/login', methods=['POST'])
def login_user():
    """Log in a user with a password if set."""
    data = request.json
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == data['username']).first()
        if not user or (user.password_hash and not user.check_password(data['password'])):
            return jsonify({'error': 'Invalid username or password'}), 401

        return jsonify({'success': True, 'id': user.id, 'display_name': user.display_name})
    finally:
        session.close()

@user_bp.route('/<int:user_id>', methods=['PATCH'])
def update_user(user_id):
    """Update user preferences like display name or password."""
    data = request.json
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if 'display_name' in data:
            user.display_name = data['display_name']
        if 'password' in data and data['password']:
            user.set_password(data['password'])

        session.commit()
        return jsonify({'success': True})
    finally:
        session.close()