from django.apps import AppConfig


class CampaignConfig(AppConfig):

    name = "campaign"

    def ready(self):
        import campaign.signals
