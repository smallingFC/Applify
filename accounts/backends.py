"""
:Created: 28 May 2016
:Author: Lucas Connors

"""

from social_core.backends.facebook import FacebookOAuth2
from social_core.backends.google import GoogleOAuth2


class GoogleOAuth2Login(GoogleOAuth2):

    name = "google-oauth2-login"
    auth_operation = "login"

    def setting(self, name, default=None):
        return self.strategy.setting(name, default=default, backend=super())


class GoogleOAuth2Register(GoogleOAuth2):

    name = "google-oauth2-register"
    auth_operation = "register"

    def setting(self, name, default=None):
        return self.strategy.setting(name, default=default, backend=super())


class FacebookOAuth2Login(FacebookOAuth2):

    name = "facebook-login"
    auth_operation = "login"

    def setting(self, name, default=None):
        return self.strategy.setting(name, default=default, backend=super())


class FacebookOAuth2Register(FacebookOAuth2):

    name = "facebook-register"
    auth_operation = "register"

    def setting(self, name, default=None):
        return self.strategy.setting(name, default=default, backend=super())
