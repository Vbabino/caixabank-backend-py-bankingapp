from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from app.utils.utils import is_token_revoked
from app.models import User, Alert
from app.extensions import *

# Create a blueprint
alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/api/alerts/amount_reached", methods=["POST"])
@jwt_required()
def saving_goal():
    try:
        data = request.get_json()
        target_amount = data.get("target_amount")
        alert_threshold = data.get("alert_threshold")

        # Check if token has been revoked
        jti = get_jwt()["jti"]

        if is_token_revoked(jti):
            return jsonify({"message": "Session has expired"}), 401

        user_id = get_jwt_identity()

        user = User.query.get(user_id)

        if not user:
            return jsonify({"message": "Access Denied"}), 401

        if not data:
            return (
                jsonify({"msg": "No data provided."}),
                400,
            )
        # Validate input data
        required_fields = ["target_amount", "alert_threshold"]
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return (
                jsonify({"msg": f"Missing fields: {', '.join(missing_fields)}"}),
                400,
            )

        # Create a new alert
        new_alert = Alert(
            user_id=user_id,
            target_amount=target_amount,
            alert_threshold=alert_threshold,
        )

        # Add new alert to database
        db.session.add(new_alert)
        db.session.commit()

        return jsonify(
            {
                "msg": "Correctly added savings alert!",
                "data": {
                    "id": new_alert.id,
                    "user_id": new_alert.user_id,
                    "target_amount": new_alert.target_amount,
                    "alert_threshold": new_alert.alert_threshold,
                },
            }
        )

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"msg": "Internal Server Error"}), 500


@alerts_bp.route("/api/alerts/balance_drop", methods=["POST"])
@jwt_required()
def balance_drop():
    try:
        data = request.get_json()

        # Check if token has been revoked
        jti = get_jwt()["jti"]

        if is_token_revoked(jti):
            return jsonify({"message": "Session has expired"}), 401

        user_id = get_jwt_identity()

        user = User.query.get(user_id)

        if not user:
            return jsonify({"message": "Access Denied"}), 401

        if not data:
            return (
                jsonify({"msg": "No empty fields allowed."}),
                400,
            )

        balance_drop_threshold = Alert(
            user_id=user_id, balance_drop_threshold=data["balance_drop_threshold"]
        )

        # Add new alert to database
        db.session.add(balance_drop_threshold)
        db.session.commit()

        return (
            jsonify(
                {
                    "msg": "Balance drop alert created successfully.",
                    "data": {
                        "id": balance_drop_threshold.id,
                        "user_id": balance_drop_threshold.user_id,
                        "balance_drop_threshold": balance_drop_threshold.balance_drop_threshold,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"msg": "Internal Server Error"}), 500


@alerts_bp.route("/api/alerts/delete", methods=["DELETE"])
@jwt_required()
def delete_alert():
    try:
        # Check if token has been revoked
        jti = get_jwt()["jti"]
        if is_token_revoked(jti):
            return jsonify({"message": "Session has expired"}), 401

        data = request.get_json()
        if not data:
            return jsonify({"msg": "No data provided."}), 400

        alert_id = data.get("alert_id")
        if alert_id is None:
            return jsonify({"msg": "Missing alert ID."}), 400

        # Fetch the alert from the database
        user_id = get_jwt_identity()
        alert = Alert.query.filter_by(id=alert_id, user_id=user_id).first()

        if not alert:
            return jsonify({"msg": "Alert not found."}), 404

        # Delete the alert
        db.session.delete(alert)
        db.session.commit()

        return jsonify({"msg": f"Alert with ID {alert_id} deleted successfully."}), 200

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"message": "Internal Server Error"}), 500


@alerts_bp.route("/api/alerts/list", methods=["GET"])
@jwt_required()
def get_alert_list():
    try:
        # Check if token has been revoked
        jti = get_jwt()["jti"]

        if is_token_revoked(jti):
            return jsonify({"message": "Session has expired"}), 401

        user_id = get_jwt_identity()

        # Fetch alerts for the user
        alerts = Alert.query.filter_by(user_id=user_id).all()

        # Transform alerts into the expected response format
        alerts_list = [
            {
                "id": alert.id,
                "user_id": alert.user_id,
                "target_amount": alert.target_amount,
                "alert_threshold": alert.alert_threshold,
                "balance_drop_threshold": alert.balance_drop_threshold,
            }
            for alert in alerts
        ]

        return jsonify({"data": alerts_list}), 200

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"msg": "Internal Server Error"}), 500
