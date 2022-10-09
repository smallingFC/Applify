"""
:Created: 17 April 2016
:Author: Lucas Connors

"""

from django.db import models


class VerifiedEmailManager(models.Manager):
    def get_current_email(self, user):
        verified_email, _ = self.get_or_create(user=user, email=user.email)
        return verified_email

    def is_current_email_verified(self, user):
        verified_email = self.get_current_email(user)
        return verified_email.verified


class EmailSubscriptionManager(models.Manager):
    def is_subscribed(self, user, subscription_type=None):
        if not subscription_type:
            subscription_type = self.model.SUBSCRIPTION_ALL

        try:
            subscription = self.get(user=user, subscription=subscription_type)
        except self.model.DoesNotExist:
            return True
        else:
            return subscription.subscribed

    def unsubscribe_user(self, user, subscription_type=None):
        if not subscription_type:
            subscription_type = self.model.SUBSCRIPTION_ALL
        self.update_or_create(
            user=user, subscription=subscription_type, defaults={"subscribed": False}
        )
