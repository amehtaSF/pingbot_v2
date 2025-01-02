# flask_app/blueprints/support.py

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Support, User
from extensions import db
from datetime import datetime
from crud import create_support_query

support_bp = Blueprint('support', __name__)


@support_bp.route('/support', methods=['POST'])
@jwt_required(optional=True)
def submit_feedback():
    data = request.get_json()
    email = data.get('email')
    query_type = data.get('type')  # Adjusted to accept 'type'
    message = data.get('message')
    is_urgent = data.get('urgent', False)

    if not message or not query_type:
        return jsonify({'error': 'Query type and message are required.'}), 400

    user_id = None
    user_identity = get_jwt_identity()
    if user_identity:
        user_id = user_identity  # Get the user ID from the JWT
        if not email:
            user = User.query.get(user_id)
            email = user.email if user else None

    if not email:
        return jsonify({'error': 'Email is required.'}), 400

    messages_list = [{
        'sender': email,
        'message': message,
    }]

    try:
        support_query = create_support_query(
            session=db.session,
            user_id=user_id,
            email=email,
            messages=messages_list,
            query_type=query_type,
            is_urgent=is_urgent
        )
        db.session.commit()
        return jsonify({'message': 'Feedback submitted successfully.'}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error saving feedback for user {user_id} - {email}.')
        current_app.logger.exception(e)
        return jsonify({'error': 'An error occurred while saving feedback.'}), 500