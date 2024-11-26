from flask import Flask, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy import func

from app.models import *
from dotenv import load_dotenv
import os
from app.extensions import *
from app.utils.utils import *


load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)
migrate.init_app(app, db)
jwt.init_app(app)

# Create the database tables if they don't exist
with app.app_context():
    db.create_all()


# Placeholder route for testing
@app.route("/")
def index():
    return "Flask app is running!"


@app.route("/auth/register", methods=["POST"])
def register():
    try:
        data = request.get_json()
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        # Validate input data
        required_fields = ["name", "email", "password"]
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return (
                jsonify({"message": f"Missing fields: {', '.join(missing_fields)}"}),
                400,
            )

        # Email address validation
        if not validate_email(email):
            return jsonify({"message": f"Invalid email: {email}"}), 400

        # Check if email already exists
        if User.query.filter_by(email=email).first():
            return jsonify({"message": "Email already registered."}), 400

        # Create a new user
        new_user = User(name=name, email=email)

        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        return (
            jsonify(
                {
                    "name": new_user.name,
                    "email": new_user.email,
                    "hashedPassword": new_user.hashed_password,
                }
            ),
            201,
        )
    except Exception as e:
        print("Error:", e)  # Debug line for errors
        return jsonify({"message": "Internal Server Error"}), 500


@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    # Check if null fields
    if not email or not password:
        return jsonify({"message": "Bad credentials"}), 401

    # Check if the user exists
    user = User.query.filter_by(email=email).first()

    if user is None:
        return (
            jsonify({"message": "User not found for the given email: " + email}),
            400,
        )

    if not user.check_password(password):
        return jsonify({"message": "Bad credentials"}), 401

    # Create a JWT token
    access_token = create_access_token(identity=str(user.id))

    return jsonify({"token": access_token}), 200


@app.route("/api/users/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    revoked_token = RevokedToken(token=jti)
    db.session.add(revoked_token)
    db.session.commit()
    return (jsonify({"message": "Successfully logged out"})), 200


@app.route("/api/recurring-expenses", methods=["POST"])
@jwt_required()
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


@app.route("/api/recurring-expenses", methods=["GET"])
@jwt_required()
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


@app.route("/api/recurring-expenses/projection", methods=["GET"])
@jwt_required()
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


@app.route("/api/recurring-expenses/<int:expense_id>", methods=["PUT"])
@jwt_required()
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


@app.route("/api/recurring-expenses/<int:expense_id>", methods=["DELETE"])
@jwt_required()
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


@app.route("/api/transfers/fees/<source_currency>/<target_currency>", methods=["GET"])
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


@app.route("/api/transfers/rates/<source_currency>/<target_currency>", methods=["GET"])
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


@app.route("/api/transfers/simulate", methods=["POST"])
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


if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=3000, debug=True)
