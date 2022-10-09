"""
:Created: 11 July 2016
:Author: Lucas Connors

"""

from django.contrib.sites.models import Site


def request(request):
    return {"host": Site.objects.get_current().domain}
