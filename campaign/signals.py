"""
:Created: 29 May 2016
:Author: Lucas Connors

"""

from django.core.cache import cache
from django.db import models
from django.dispatch import receiver

from accounts.models import UserProfile
from campaign.models import Investment, RevenueReport


@receiver(
    models.signals.post_save,
    sender=Investment,
    dispatch_uid="clear_leaderboard_from_investment_handler",
)
@receiver(
    models.signals.post_save,
    sender=RevenueReport,
    dispatch_uid="clear_leaderboard_from_revenue_report_handler",
)
def clear_leaderboard_cache_handler(sender, instance, **kwargs):
    cache.delete("leaderboard")


@receiver(
    models.signals.post_save,
    sender=Investment,
    dispatch_uid="clear_profile_contexts_from_investment_handler",
)
def clear_profile_context(sender, instance, **kwargs):
    pk = instance.investor().userprofile.pk
    cache.delete(f"profile_context-{pk}")


@receiver(
    models.signals.post_save,
    sender=RevenueReport,
    dispatch_uid="clear_profile_contexts_from_revenue_report_handler",
)
def clear_all_profile_contexts(sender, instance, **kwargs):
    # TODO(lucas): Review to improve performance
    # Instead of clearing out all of the profile contexts, we could just clear out
    # the profile contexts associated with the investors related to this revenue report
    cache_keys = [f"profile_context-{up.pk}" for up in UserProfile.objects.all()]
    cache.delete_many(cache_keys)
