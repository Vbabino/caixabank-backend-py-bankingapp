from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from app.extensions import db
from app.models import Transaction, User
from app.utils.utils import is_token_revoked, savings_alert
from flasgger.utils import swag_from


deposits_bp = Blueprint("deposits", __name__, url_prefix="/api/deposits")


@deposits_bp.route("", methods=["POST"])
@jwt_required()
@swag_from("docs/add_deposit.yml")
def add_deposit():
    try:
        # Check if token has been revoked
        jti = get_jwt()["jti"]
        if is_token_revoked(jti):
            return jsonify({"message": "Session has expired"}), 401

        # Get the user ID and fetch user
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({"message": "Access Denied"}), 401

        # Parse and validate request data
        data = request.get_json()
        if not data:
            return jsonify({"msg": "No data provided."}), 400

        required_fields = ["deposit_amount", "password"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({"msg": f"Missing fields: {', '.join(missing_fields)}"}), 400

        deposit_amount = data.get("deposit_amount")
        password = data.get("password")

        # Validate deposit amount
        if deposit_amount <= 0:
            return jsonify({"msg": "Deposit amount must be greater than 0"}), 400

        # Validate password
        if not user.check_password(password):
            return jsonify({"message": "Bad credentials"}), 401

        # Update user's balance
        user.balance += deposit_amount

        # Trigger savings alert if applicable
        if user.alert:
            for alert in user.alert:
                if (
                    alert.alert_threshold is not None
                    and alert.target_amount is not None
                    and user.balance >= alert.alert_threshold
                    and user.balance <= alert.target_amount
                ):
                    savings_alert(user, alert)

        # Saving the transaction to database
        transaction = Transaction(
            user_id=user_id,
            amount=deposit_amount,
            category="deposit",
            timestamp=datetime.utcnow(),
        )
        db.session.add(transaction)

        # Commit changes to the database
        db.session.commit()

        return (
            jsonify(
                {
                    "msg": f"{deposit_amount} has been added to your account balance",
                    "new_balance": user.balance,
                }
            ),
            200,
        )

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"msg": "Internal Server Error"}), 500
