"""
:Created: 5 May 2016
:Author: Lucas Connors

"""

from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from sorl.thumbnail import get_thumbnail

from accounts.cache import cache_using_pk
from artist.models import Artist
from campaign.models import Campaign, Investment


class UserAvatar(models.Model):

    PROVIDER_PERDIEM = "perdiem"
    PROVIDER_GOOGLE = "google-oauth2"
    PROVIDER_FACEBOOK = "facebook"
    PROVIDER_CHOICES = (
        (PROVIDER_PERDIEM, "Custom"),
        (PROVIDER_GOOGLE, "Google"),
        (PROVIDER_FACEBOOK, "Facebook"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.CharField(choices=PROVIDER_CHOICES, max_length=15)

    class Meta:
        unique_together = (("user", "provider"),)

    @staticmethod
    def anonymous_avatar_url():
        return "{static_url}img/perdiem-anonymous-avatar.png".format(
            static_url=settings.STATIC_URL
        )

    def __str__(self):
        return "{user}: {provider}".format(
            user=str(self.user), provider=self.get_provider_display()
        )

    def avatar_url(self):
        if self.provider == self.PROVIDER_GOOGLE:
            return self.useravatarurl.url
        elif self.provider in [self.PROVIDER_FACEBOOK, self.PROVIDER_PERDIEM]:
            original = self.useravatarimage.img
            return get_thumbnail(original, "150x150", crop="center").url


class UserAvatarURL(models.Model):

    avatar = models.OneToOneField(UserAvatar, on_delete=models.CASCADE)
    url = models.URLField(max_length=2000)

    def __str__(self):
        return str(self.avatar)


def user_avatar_filename(instance, filename):
    extension = filename.split(".")[-1]
    new_filename = "{user_id}.{extension}".format(
        user_id=instance.avatar.user.id, extension=extension
    )
    return "/".join(["avatars", new_filename])


class UserAvatarImage(models.Model):

    avatar = models.OneToOneField(UserAvatar, on_delete=models.CASCADE)
    img = models.ImageField(upload_to=user_avatar_filename)

    def __str__(self):
        return str(self.avatar)


class UserProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ForeignKey(
        UserAvatar, on_delete=models.SET_NULL, null=True, blank=True
    )
    invest_anonymously = models.BooleanField(default=False)

    @staticmethod
    def prepare_artist_for_profile_context(artist):
        artist.total_invested = 0
        artist.total_earned = 0
        return artist.id, artist

    def __str__(self):
        return str(self.user)

    def get_display_name(self):
        if self.invest_anonymously:
            return "Anonymous"
        else:
            return self.user.get_full_name() or self.user.username

    def default_avatar_url(self):
        name = self.get_display_name()
        return f"https://ui-avatars.com/api/?name={quote(name)}&size=150"

    def avatar_url(self):
        if self.avatar:
            return self.avatar.avatar_url()
        else:
            return self.default_avatar_url()

    def display_avatar_url(self):
        if self.invest_anonymously:
            return UserAvatar.anonymous_avatar_url()
        else:
            return self.avatar_url()

    def public_profile_url(self):
        if not self.invest_anonymously:
            return reverse("public_profile", args=(self.user.username,))

    def get_total_earned(self):
        investments = Investment.objects.filter_user_investments(user=self.user)
        total_earned = sum(investment.generated_revenue() for investment in investments)
        return total_earned

    @cache_using_pk
    def profile_context(self):
        context = {}

        # Get artists the user has invested in
        investments = Investment.objects.filter(
            charge__customer__user=self.user, charge__paid=True, charge__refunded=False
        )
        campaign_ids = investments.values_list("campaign", flat=True).distinct()
        campaigns = Campaign.objects.filter(id__in=campaign_ids).select_related(
            "project"
        )
        context["campaigns"] = campaigns
        artist_ids = campaigns.values_list("project__artist", flat=True).distinct()
        artists = Artist.objects.filter(id__in=artist_ids)
        context["artists"] = dict(map(self.prepare_artist_for_profile_context, artists))

        # Update context with total investments
        aggregate_context = investments.aggregate(
            total_investments=models.Sum(
                models.F("campaign__value_per_share") * models.F("num_shares"),
                output_field=models.FloatField(),
            )
        )
        context.update(aggregate_context)

        # Update context with total invested and total earned
        total_earned = 0
        for campaign in campaigns:
            artist = campaign.project.artist

            # Total invested
            investments_this_campaign = investments.filter(campaign=campaign)
            num_shares_this_campaign = investments_this_campaign.aggregate(
                ns=models.Sum("num_shares")
            )["ns"]
            context["artists"][artist.id].total_invested += (
                num_shares_this_campaign * campaign.value_per_share
            )

            # Total earned
            generated_revenue_user = 0
            for investment in investments_this_campaign:
                generated_revenue_user += investment.generated_revenue()
            context["artists"][artist.id].total_earned += generated_revenue_user
            total_earned += generated_revenue_user

        # TODO(lucas): Could refactor to use get_total_earned() instead
        context["total_earned"] = total_earned

        # Add percentage of return to context
        total_investments = aggregate_context["total_investments"] or 0
        try:
            percentage = total_earned / total_investments * 100
        except ZeroDivisionError:
            percentage = 0
        context["percentage"] = percentage

        return context
