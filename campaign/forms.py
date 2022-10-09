"""
:Created: 14 April 2016
:Author: Lucas Connors

"""

from django import forms


class PaymentChargeForm(forms.Form):

    card = forms.CharField()
    num_shares = forms.IntegerField(min_value=1)

    def __init__(self, *args, **kwargs):
        self.campaign = kwargs.pop("campaign")
        super().__init__(*args, **kwargs)

    def clean_num_shares(self):
        num_shares = self.cleaned_data["num_shares"]
        if num_shares > self.campaign.num_shares_remaining():
            raise forms.ValidationError(
                "The number of shares requested exceeds the number of shares available."
            )
        return num_shares
