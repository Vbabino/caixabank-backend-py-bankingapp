import os
from flask import Flask
from dotenv import load_dotenv
from app.routes.transfers_routes import transfers_bp
from app.routes.savings_goal_alert_routes import alerts_bp
from app.routes.recurring_expenses_routes import recurring_bp
from app.routes.auth_routes import auth_bp
from app.extensions import *


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

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(recurring_bp)
app.register_blueprint(transfers_bp)
app.register_blueprint(alerts_bp)


# Placeholder route for testing
@app.route("/")
def index():
    return "Flask app is running!"


if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=3000, debug=True)
