from django.shortcuts import render
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import backends

class EmailModelBackend(backends.ModelBackend):

    def authenticate(self, request, username=None, password=None):
        UserModel = get_user_model()
        if '@' in username:
            kwargs = {'email': username}
        else:
            kwargs = {'email': username + '@anybirth.co.jp'}
        try:
            user = UserModel.objects.get(**kwargs)
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            UserModel.set_password(self, raw_password=password)
