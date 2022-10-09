"""
:Created: 17 April 2016
:Author: Lucas Connors

"""

from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.urls import reverse

from emails.models import EmailSubscription


def make_token(user):
    return TimestampSigner().sign(user.id)


def create_unsubscribe_link(user, subscription_type=EmailSubscription.SUBSCRIPTION_ALL):
    user_id, token = make_token(user).split(":", 1)
    return reverse(
        "unsubscribe",
        kwargs={
            "user_id": user_id,
            "subscription_type": subscription_type,
            "token": token,
        },
    )


def check_token(user_id, token):
    try:
        key = f"{user_id}:{token}"
        TimestampSigner().unsign(key, max_age=60 * 60 * 48)  # Valid for 2 days
    except (BadSignature, SignatureExpired):
        return False
    return True
