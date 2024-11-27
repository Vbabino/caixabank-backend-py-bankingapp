from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt, jwt_required
from app.utils.utils import get_exchange_data, is_token_revoked
from app.models import *


# Create a blueprint
transfers_bp = Blueprint("transfers", __name__)

@transfers_bp.route("/api/transfers/fees/<source_currency>/<target_currency>", methods=["GET"])
@jwt_required()
def get_fees(source_currency, target_currency):
    try:
        # Check if token has been revoked
        jti = get_jwt()["jti"]
        if is_token_revoked(jti):
            return jsonify({"message": "Session has expired"}), 401

        # Fetch the fee from the database
        fee = get_exchange_data(ExchangeFee, source_currency, target_currency)

        if not fee:
            return (
                jsonify({"msg": "No fee information available for these currencies."}),
                400,
            )

        return jsonify({"fee": round(fee.fee, 2)}), 200

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"msg": "Internal Server Error"}), 500


@transfers_bp.route("/api/transfers/rates/<source_currency>/<target_currency>", methods=["GET"])
@jwt_required()
def get_rates(source_currency, target_currency):
    try:
        # Check if token has been revoked
        jti = get_jwt()["jti"]
        if is_token_revoked(jti):
            return jsonify({"message": "Session has expired"}), 401

        # Fetch the rate from the database
        rate = get_exchange_data(ExchangeRate, source_currency, target_currency)

        if not rate:
            return (
                jsonify({"msg": "No rate information available for these currencies."}),
                400,
            )

        return jsonify({"rate": round(rate.rate, 2)}), 200

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"msg": "Internal Server Error"}), 500


@transfers_bp.route("/api/transfers/simulate", methods=["POST"])
@jwt_required()
def international_transfer():
    data = request.get_json()
    amount = data.get("amount")
    source_currency = data.get("source_currency")
    target_currency = data.get("target_currency")

    # Check if token has been revoked
    jti = get_jwt()["jti"]

    if is_token_revoked(jti):
        return jsonify({"message": "Session has expired"}), 401

    # Fetch the rate from the database
    rate = get_exchange_data(ExchangeRate, source_currency, target_currency)

    # Fetch the fee from the database
    fee = get_exchange_data(ExchangeFee, source_currency, target_currency)

    if fee is None or rate is None:
        return (
            jsonify({"msg": "Invalid currencies or no exchange data available."}),
            404,
        )

    converted_amount = amount * rate.rate
    total_amount = converted_amount + fee.fee

    return jsonify(
        {
            "msg": "Transfer simulation successful.",
            "converted_amount": converted_amount,
            "total_amount": total_amount,
            "fee": round(fee.fee, 2),
        }
    )
