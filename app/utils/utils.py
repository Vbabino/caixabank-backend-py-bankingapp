import re
import smtplib
from sqlalchemy import exists
from app.models import *
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def validate_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email))


def is_token_revoked(jti):
    token_revoked = db.session.query(exists().where(RevokedToken.token == jti)).scalar()
    return token_revoked

def get_exchange_data(model, source_currency, target_currency):
    """
    Fetch exchange data (rate or fee) for the given source and target currency.

    Args:
        model (db.Model): The model to query (ExchangeRate or ExchangeFee).
        source_currency (str): The source currency.
        target_currency (str): The target currency.

    Returns:
        db.Model instance or None: The matching database record.
    """
    return model.query.filter_by(
        currency_from=source_currency, currency_to=target_currency
    ).first()

def savings_alert(user, alert):
    from_email = "CaixaBank@caixabank.com"
    to_email = user.email
    subject = "Savings alert"

    body = f"""
    Dear {user.name},

    Great news! Your savings are nearing the target amount of {alert.target_amount}.
    Keep up the great work and stay consistent!

    Best Regards,
    The Management Team
    """
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    smtp_server = "smtp"
    smtp_port = 1025

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.send_message(msg)

def balance_drop_alert(user, alert):
    from_email = "CaixaBank@caixabank.com"
    to_email = user.email
    subject = "Savings alert"

    body = f"""
    Dear {user.name},

    We noticed a significant balance drop in your account more than {alert.balance_drop_threshold}.
    If this wasn't you, please review your recent transactions to ensure everything is correct.

    Best Regards,
    The Management Team
    """
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    smtp_server = "smtp"
    smtp_port = 1025

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.send_message(msg)
