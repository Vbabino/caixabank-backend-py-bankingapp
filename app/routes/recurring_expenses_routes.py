from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from app.utils.utils import is_token_revoked
from sqlalchemy import func
from flasgger.utils import swag_from
from app.extensions import *

from app.models import *

# Create a blueprint
recurring_bp = Blueprint("recurring_expenses", __name__)


@recurring_bp.route("/api/recurring-expenses", methods=["POST"])
@jwt_required()
@swag_from("docs/recurring_expenses.yml")
def recurring_expenses():
    try:

        data = request.get_json()
        expense_name = data.get("expense_name")
        amount = data.get("amount")
        frequency = data.get("frequency")
        start_date = data.get("start_date")

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
        required_fields = ["expense_name", "amount", "frequency", "start_date"]
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return (
                jsonify({"msg": f"Missing fields: {', '.join(missing_fields)}"}),
                400,
            )

        # Create a new recurring expense
        new_recurring_expense = RecurringExpense(
            user_id=user_id,
            expense_name=expense_name,
            amount=amount,
            frequency=frequency,
            start_date=start_date,
        )

        # Add new recurring expense to databae
        db.session.add(new_recurring_expense)
        db.session.commit()

        return (
            jsonify(
                {
                    "msg": "Recurring expense added successfully.",
                    "data": {
                        "id": new_recurring_expense.id,
                        "expense_name": new_recurring_expense.expense_name,
                        "amount": new_recurring_expense.amount,
                        "frequency": new_recurring_expense.frequency,
                        "start_date": new_recurring_expense.start_date.strftime(
                            "%Y-%m-%d"
                        ),
                    },
                }
            ),
            201,
        )

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"msg": "Internal Server Error"}), 500


@recurring_bp.route("/api/recurring-expenses", methods=["GET"])
@jwt_required()
@swag_from("docs/get_recurring_expenses.yml")
def get_recurring_expenses():
    try:
        # Check if token has been revoked
        jti = get_jwt()["jti"]

        if is_token_revoked(jti):
            return jsonify({"message": "Session has expired"}), 401

        user_id = get_jwt_identity()

        user = User.query.get(user_id)

        if not user:
            return jsonify({"message": "User not found"}), 404

        expenses_list = [
            {
                "id": expense.id,
                "expense_name": expense.expense_name,
                "amount": expense.amount,
                "frequency": expense.frequency,
                "start_date": expense.start_date.strftime("%Y-%m-%d"),
            }
            for expense in user.recurring_expense
        ]

        return (
            jsonify({"recurring_expenses": expenses_list}),
            200,
        )

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"msg": "Internal Server Error"}), 500


@recurring_bp.route("/api/recurring-expenses/projection", methods=["GET"])
@jwt_required()
@swag_from("docs/monthly_expenses.yml")
def monthly_expenses():
    try:
        # Check if token has been revoked
        jti = get_jwt()["jti"]

        if is_token_revoked(jti):
            return jsonify({"message": "Session has expired"}), 401

        user_id = get_jwt_identity()

        user = User.query.get(user_id)

        if not user:
            return jsonify({"message": "User not found"}), 404

        # Group expenses by year and month, summing the amounts
        monthly_expenses = (
            db.session.query(
                func.date_format(RecurringExpense.start_date, "%Y-%m").label("month"),
                func.sum(RecurringExpense.amount).label("total_amount"),
            )
            .filter(RecurringExpense.user_id == user_id)
            .group_by(func.date_format(RecurringExpense.start_date, "%Y-%m"))
            .order_by("month")
            .all()
        )

        # Convert query result to a list of dictionaries
        expenses_list = [
            {
                "month": expense.month,
                "recurring_expenses": round(expense.total_amount, 2),
            }
            for expense in monthly_expenses
        ]

        return (
            jsonify({"list_of_monthly_expenses": expenses_list}),
            200,
        )

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"msg": "Internal Server Error"}), 500


@recurring_bp.route("/api/recurring-expenses/<int:expense_id>", methods=["PUT"])
@jwt_required()
@swag_from("docs/update_recurring_expense.yml")
def update_recurring_expense(expense_id):
    try:
        # Check if token has been revoked
        jti = get_jwt()["jti"]
        if is_token_revoked(jti):
            return jsonify({"message": "Session has expired"}), 401

        # Get the user ID from the JWT
        user_id = get_jwt_identity()

        # Fetch the recurring expense by ID
        expense = RecurringExpense.query.filter_by(
            id=expense_id, user_id=user_id
        ).first()

        # Check if the expense exists
        if not expense:
            return jsonify({"message": "Recurring expense not found"}), 404

        # Parse the request body
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided"}), 400

        # Validate input data
        required_fields = ["expense_name", "amount", "frequency", "start_date"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return (
                jsonify({"message": f"Missing fields: {', '.join(missing_fields)}"}),
                400,
            )

        # Update the expense fields
        expense.expense_name = data["expense_name"]
        expense.amount = data["amount"]
        expense.frequency = data["frequency"]
        expense.start_date = datetime.strptime(data["start_date"], "%Y-%m-%d")

        # Commit changes to the database
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Recurring expense updated successfully",
                    "data": {
                        "id": expense.id,
                        "expense_name": expense.expense_name,
                        "amount": expense.amount,
                        "frequency": expense.frequency,
                        "start_date": expense.start_date.strftime("%Y-%m-%d"),
                    },
                }
            ),
            200,
        )

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"message": "Internal Server Error"}), 500


@recurring_bp.route("/api/recurring-expenses/<int:expense_id>", methods=["DELETE"])
@jwt_required()
@swag_from("docs/delete_recurring_expense.yml")
def delete_recurring_expense(expense_id):
    try:
        # Check if token has been revoked
        jti = get_jwt()["jti"]
        if is_token_revoked(jti):
            return jsonify({"message": "Session has expired"}), 401

        # Get the user ID from the JWT
        user_id = get_jwt_identity()

        # Fetch the recurring expense by ID
        expense = RecurringExpense.query.filter_by(
            id=expense_id, user_id=user_id
        ).first()

        # Check if the expense exists
        if not expense:
            return jsonify({"message": "Recurring expense not found"}), 404

        # Delete expense from database
        db.session.delete(expense)

        # Commit changes to the database
        db.session.commit()

        return (
            jsonify(
                {"msg": f"Recurring expense with ID {expense_id} deleted successfully"}
            ),
            200,
        )

    except Exception as e:
        print("Error:", repr(e))
        return jsonify({"message": "Internal Server Error"}), 500
