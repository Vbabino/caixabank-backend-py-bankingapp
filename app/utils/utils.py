import re
from sqlalchemy import exists
from app.models import *


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
