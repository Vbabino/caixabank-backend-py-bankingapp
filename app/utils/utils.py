import re
from sqlalchemy import exists
from app.models import *


def validate_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email))


def is_token_revoked(jti):
    token_revoked = db.session.query(exists().where(RevokedToken.token == jti)).scalar()
    return token_revoked
