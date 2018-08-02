import datetime
from django.conf import settings
from django.urls import reverse_lazy
from django.views import generic
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib.auth import views as auth_views
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from . import models, forms
# Create your views here.

class SignupView(generic.CreateView):
    model = models.User
    form_class = forms.UserForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:complete')

    def get_object(self, queryset=None):
        return queryset.get(traveller=self.traveller)

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        return super().get(request)

    def form_valid(self, form):
        form.instance.password = make_password(self.request.POST.get('password'))
        user = form.save(commit=False)
        user.save()

        protocol = 'https://' if self.request.is_secure() else 'http://'
        host_name = settings.HOST_NAME
        send_mail(
            u'会員登録完了',
            u'会員登録が完了しました。\n' +
            '以下のURLより、メールアドレスの認証を行ってください。\n\n' +
            protocol + host_name + str(reverse_lazy('accounts:activate', args=[user.uuid,])),
            'info@anybirth.co.jp',
            [user.email],
            fail_silently=False,
        )
        return super().form_valid(form)

class SignupSocialView(generic.View):

    def get(self, request):
        user = request.user
        if user.date_joined < timezone.now() - datetime.timedelta(seconds=10):
            return redirect('accounts:profile')

        protocol = 'https://' if self.request.is_secure() else 'http://'
        host_name = settings.HOST_NAME
        send_mail(
            u'会員登録完了',
            u'会員登録が完了しました。\n' +
            '以下のURLより、メールアドレスの認証を行ってください。\n\n' +
            protocol + host_name + str(reverse_lazy('accounts:activate', args=[user.uuid,])),
            'info@anybirth.co.jp',
            [user.email],
            fail_silently=False,
        )
        return redirect('accounts:complete', permanent=True)


class CompleteView(generic.TemplateView):
    template_name = 'accounts/complete.html'


class ActivateView(generic.TemplateView):
    template_name = 'accounts/activate.html'

    def get(self, request, uuid):
        try:
            user = models.User.objects.get(uuid=uuid)
        except models.User.DoesNotExist:
            return redirect('accounts:activate_expired')
        if user.is_verified:
            return redirect('accounts:activate_expired')
        user.is_verified = True
        user.save()

        send_mail(
            u'メールアドレス認証完了',
            u'メールアドレス認証完了が完了しました。',
            'info@anybirth.co.jp',
            [user.email],
            fail_silently=False,
        )
        return super().get(request, uuid)


class ActivateExpiredView(generic.TemplateView):
    template_name = 'accounts/activate_expired.html'


class LoginView(auth_views.LoginView):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        return super().get(request)


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('accounts:login')


@method_decorator(login_required, name='dispatch')
class ProfileView(generic.TemplateView):
    template_name = 'accounts/profile.html'
