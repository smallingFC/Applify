"""
:Created: 17 April 2016
:Author: Lucas Connors

"""

from unittest import mock

from django.test import TestCase, override_settings

from emails.factories import EmailSubscriptionFactory
from emails.models import EmailSubscription
from emails.utils import create_unsubscribe_link
from perdiem.tests import PerDiemTestCase


class UnsubscribeTestCase(TestCase):
    def testUnsubscribeFromAllRemovesAllSubscriptions(self):
        # Create an artist update subscription
        email_subscription = EmailSubscriptionFactory(
            subscription=EmailSubscription.SUBSCRIPTION_ARTUP, subscribed=True
        )

        # Create an explicit unsubscribe from all emails
        # We cannot use a factory to generate the EmailSubscription here
        # because we actually need the pre_save signal to be made
        EmailSubscription.objects.create(
            user=email_subscription.user,
            subscription=EmailSubscription.SUBSCRIPTION_ALL,
            subscribed=False,
        )

        # Verify that when the user unsubscribes from everything, this artist update subscription is turned off
        email_subscription.refresh_from_db()
        self.assertFalse(email_subscription.subscribed)


class SubscribeTestCase(PerDiemTestCase):
    def testSubscribeToNewsletterSuccess(self):
        self.assertResponseRenders(
            "/accounts/settings/",
            method="POST",
            data={
                "action": "email_preferences",
                "email": self.user.email,
                "subscription_all": True,
                "subscription_news": True,
                "subscription_artist_update": False,
            },
        )


class UnsubscribeWebTestCase(PerDiemTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        EmailSubscriptionFactory(user=cls.user)

    def testUnsubscribe(self):
        unsubscribe_url = create_unsubscribe_link(self.user)
        self.assertResponseRenders(unsubscribe_url)

    def testUnsubscribeUnauthenticated(self):
        self.client.logout()
        unsubscribe_url = create_unsubscribe_link(self.user)
        self.assertResponseRenders(unsubscribe_url)

    def testUnsubscribeInvalidLink(self):
        self.client.logout()
        unsubscribe_url = "/unsubscribe/{user_id}/ALL/{invalid_token}/".format(
            user_id=self.user.id, invalid_token="abc123"
        )
        response = self.assertResponseRenders(unsubscribe_url)
        self.assertIn(b"This link is invalid", response.content)

    @mock.patch("emails.mailchimp.requests.put")
    @override_settings(
        MAILCHIMP_API_KEY="FAKE_API_KEY", MAILCHIMP_LIST_ID="FAKE_LIST_ID"
    )
    def testUnsubscribeFromMailChimp(self, mock_mailchimp_request):
        mock_mailchimp_request.return_value = mock.Mock(status_code=200)

        self.client.logout()

        # Simulate POST request received from MailChimp
        self.assertResponseRenders(
            "/unsubscribe/from-mailchimp/",
            method="POST",
            data={"data[list_id]": "FAKE_LIST_ID", "data[email]": self.user.email},
        )
