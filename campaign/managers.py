from django.db import models


class InvestmentManager(models.Manager):
    def filter_user_investments(self, user):
        return self.filter(
            charge__customer__user=user, charge__paid=True, charge__refunded=False
        )
