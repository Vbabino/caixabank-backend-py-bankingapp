from datetime import datetime, timezone
from app.extensions import db, bcrypt

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), unique=True, nullable=False, index=True)
    hashed_password = db.Column(db.String(128), nullable=False)
    balance = db.Column(db.Float, nullable=False, default=0.0)

    alert = db.relationship("Alert", back_populates="user")
    recurring_expense = db.relationship("RecurringExpense", back_populates="user")
    transactions = db.relationship("Transaction", back_populates="user")

    # Hash the password
    def set_password(self, password):
        self.hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    # Verify the password
    def check_password(self, password):
        return bcrypt.check_password_hash(self.hashed_password, password)


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    target_amount = db.Column(db.Float)
    alert_threshold = db.Column(db.Float)
    balance_drop_threshold = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="alert")


class RecurringExpense(db.Model):
    __tablename__ = "recurring_expenses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    expense_name = db.Column(db.String(255))
    amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(50))
    start_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="recurring_expense")


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    fraud = db.Column(db.Boolean)

    user = db.relationship("User", back_populates="transactions")


class RevokedToken(db.Model):
    __tablename__ = "revoked_tokens"
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(500), unique=True, nullable=True)
    revoked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
