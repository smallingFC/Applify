"""
:Created: 8 April 2016
:Author: Lucas Connors

"""

from django.contrib.auth import login
from django.utils.deprecation import MiddlewareMixin

from accounts.forms import LoginAccountForm


class LoginFormMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.method == "POST" and "login-username" in request.POST:
            # Process the request as a login request
            # if login-username is in the POST data
            form = LoginAccountForm(data=request.POST, prefix="login")
            if form.is_valid():
                login(request, form.get_user())

            # We have to change the request method here because
            # the page the user is currently on might not support POST
            request.method = "GET"
        else:
            form = LoginAccountForm(request, prefix="login")

        # Add the login form to the request (accessible in context)
        request.login_form = form
