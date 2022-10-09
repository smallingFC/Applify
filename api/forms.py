"""
:Created: 29 May 2016
:Author: Lucas Connors

"""

from django import forms


class CoordinatesFromAddressForm(forms.Form):

    address = forms.CharField()
