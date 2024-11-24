from flask import Flask, request, jsonify
from flask_jwt_extended import create_access_token

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


if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=3000, debug=True)
