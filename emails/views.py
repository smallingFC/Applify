"""
:Created: 17 April 2016
:Author: Lucas Connors

"""

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from emails.models import EmailSubscription
from emails.utils import check_token


class UnsubscribeView(TemplateView):

    template_name = "registration/unsubscribe.html"

    def dispatch(self, request, *args, **kwargs):
        self.user = get_object_or_404(User, id=kwargs["user_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_is_logged_in = (
            self.request.user.is_authenticated and self.request.user == self.user
        )
        user_is_authenticated = user_is_logged_in or check_token(
            self.user, kwargs["token"]
        )
        subscription_type = kwargs["subscription_type"]
        subscription_choices = dict(EmailSubscription.SUBSCRIPTION_CHOICES)

        if user_is_authenticated and subscription_type in subscription_choices:
            EmailSubscription.objects.unsubscribe_user(
                self.user, subscription_type=subscription_type
            )
            context.update(
                {
                    "success": True,
                    "email": self.user.email,
                    "subscription_type_display": subscription_choices[
                        subscription_type
                    ],
                }
            )
        else:
            context["success"] = False

        return context


@csrf_exempt
def unsubscribe_from_mailchimp(request):
    if (
        request.method == "POST"
        and request.POST["data[list_id]"] == settings.MAILCHIMP_LIST_ID
    ):
        email = request.POST["data[email]"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            pass
        else:
            EmailSubscription.objects.unsubscribe_user(
                user, subscription_type=EmailSubscription.SUBSCRIPTION_NEWS
            )
    return HttpResponse("")
