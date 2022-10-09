"""
:Created: 9 July 2016
:Author: Lucas Connors

"""

from django.conf import settings


def keys(request):
    return {
        "FB_APP_ID": settings.SOCIAL_AUTH_FACEBOOK_KEY,
        "GA_TRACKING_CODE": settings.GA_TRACKING_CODE,
        "JACO_API_KEY": settings.JACO_API_KEY,
    }


def profile(request):
    user = request.user
    if user.is_authenticated:
        return user.userprofile.profile_context()
    return {}
