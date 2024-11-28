from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt, jwt_required
from app.extensions import db
from app.models import Transaction, User
from app.utils.utils import is_token_revoked, balance_drop_alert

transactions_bp = Blueprint("transactions", __name__, url_prefix="/api/transactions")


@transactions_bp.route("", methods=["POST"])
@jwt_required()
def add_transaction():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        amount = data.get("amount")
        category = data.get("category")
        timestamp = data.get("timestamp", datetime.utcnow().isoformat())

        # Check if token has been revoked
        jti = get_jwt()["jti"]

        if is_token_revoked(jti):
            return jsonify({"message": "Session has expired"}), 401

        # Validation
        if not user_id or not amount or not category:
            return jsonify({"msg": "No empty fields allowed."}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({"msg": "User not found."}), 404

        # Check is user has sufficient funds
        if user.balance < amount:
            return jsonify({"msg": "Transaction not allowed. Insufficient funds"}), 403

        # Convert timestamp to datetime
        timestamp = datetime.fromisoformat(timestamp)

        # Fraud Detection Rules
        is_fraud = False

        # 1. High Deviation from Average Spending
        past_90_days = timestamp - timedelta(days=90)

        transactions_90_days = (
            db.session.query(Transaction.amount)
            .filter(
                Transaction.user_id == user_id, Transaction.timestamp >= past_90_days
            )
            .all()
        )

        amounts_90_days = [txn.amount for txn in transactions_90_days]

        if amounts_90_days:
            avg_spending = sum(amounts_90_days) / len(amounts_90_days)
            std_dev = (
                sum((x - avg_spending) ** 2 for x in amounts_90_days)
                / len(amounts_90_days)
            ) ** 0.5
            if amount > avg_spending + 3 * std_dev:
                is_fraud = True

        # 2. Unusual Spending Category
        past_6_months = timestamp - timedelta(days=180)
        used_categories = (
            db.session.query(Transaction.category)
            .filter(
                Transaction.user_id == user_id, Transaction.timestamp >= past_6_months
            )
            .distinct()
            .all()
        )
        used_categories = [
            cat[0] for cat in used_categories
        ]  # Extract categories from query result

        if category not in used_categories:
            is_fraud = True

        # 3. Rapid Transactions
        past_5_minutes = timestamp - timedelta(minutes=5)
        recent_transactions = (
            db.session.query(Transaction.amount)
            .filter(
                Transaction.user_id == user_id, Transaction.timestamp >= past_5_minutes
            )
            .all()
        )
        recent_amounts = [txn.amount for txn in recent_transactions]

        if len(recent_amounts) > 3 and sum(recent_amounts) > avg_spending:
            is_fraud = True

        # Add the transaction
        transaction = Transaction(
            user_id=user_id,
            amount=amount,
            category=category,
            timestamp=timestamp,
            fraud=is_fraud,
        )
        db.session.add(transaction)

        # Update user balance
        user.balance -= amount
        db.session.commit()

        # Trigger balance drop alert if applicable
        if user.alert:
            for alert in user.alert:
                if (
                    alert.balance_drop_threshold is not None
                    and user.balance <= alert.balance_drop_threshold
                ):
                    balance_drop_alert(user, alert)

        # Response
        return (
            jsonify(
                {
                    "msg": "Transaction added and evaluated for fraud.",
                    "data": {
                        "id": transaction.id,
                        "user_id": user_id,
                        "amount": amount,
                        "category": category,
                        "timestamp": timestamp.isoformat(),
                        "fraud": is_fraud,
                    },
                }
            ),
            201,
        )

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"msg": "Internal Server Error"}), 500
