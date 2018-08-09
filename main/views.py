import uuid
import stripe
from datetime import date, datetime, timedelta
from django.urls import reverse_lazy
from django.conf import settings
from django.core.mail import send_mail
from django.views import generic
from django.db.models import Q, Count
from django.shortcuts import render, redirect
from django.contrib.auth.hashers import make_password
from accounts.models import User
from accounts.forms import UserForm
from . import models, forms

# Create your views here.

class IndexView(generic.TemplateView):
    template_name = 'main/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['color_categories'] = models.ColorCategory.objects.all()
        context['types'] = models.Type.objects.all()
        context['items_popular'] = models.Item.objects.all().annotate(Count('reservation')).order_by('-reservation__count')
        context['items_reasonable'] = models.Item.objects.all().order_by('fee_intercept')
        return context


# class SearchView(generic.ListView):
class SearchView(generic.TemplateView):
    # model = models.Item
    # context_object_name = 'items'
    template_name = 'main/search.html'

    def fee_calculator(self):
        item = models.Item.objects.get(
            color_category=self.request.GET.get('color_category'),
            type=self.request.GET.get('type')
        )

        intercept = item.fee_intercept
        coefs = item.item_fee_coef_set.order_by('starting_point')
        fee = intercept
        start_date = datetime.strptime(self.request.GET.get('start_date'), '%Y-%m-%d')
        return_date = datetime.strptime(self.request.GET.get('return_date'), '%Y-%m-%d')
        delta = return_date - start_date
        days = delta.days + 1

        for coef in coefs:
            fee_coef = coef.fee_coef
            starting_point = coef.starting_point
            end_point = coef.end_point

            if end_point:
                if days <= end_point:
                    fee += fee_coef * (days - starting_point)
                    return round(fee, -1)
                elif end_point < days:
                    fee += fee_coef * (end_point - starting_point)
            else:
                fee += fee_coef * (days - starting_point)
                return round(fee, -1)

        return round(fee, -1)

    # def get_queryset(self):
    #     return models.Item.objects.filter(
    #         color_category=self.request.GET.get('color_category'),
    #         type=self.request.GET.get('type')
    #     )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if all(x in self.request.GET for x in ('start_date', 'return_date', 'color_category', 'type', 'num')):
            try:
                context['item'] = models.Item.objects.filter(
                    color_category=self.request.GET.get('color_category'),
                    type=self.request.GET.get('type')
                ).annotate(Count('reservation')).order_by('-reservation__count')[int(self.request.GET.get('num'))]
            except IndexError:
                context['item'] = None
            try:
                context['next_item'] = models.Item.objects.filter(
                    color_category=self.request.GET.get('color_category'),
                    type=self.request.GET.get('type')
                ).annotate(Count('reservation')).order_by('-reservation__count')[int(self.request.GET.get('num')) + 1]
            except IndexError:
                context['next_item'] = None
        context['fee'] = self.fee_calculator()
        return context

    def post(self, request):
        if request.user.is_authenticated:
            cart, _ = models.Cart.objects.get_or_create(user=request.user)
        elif 'cart' in request.session and not request.user.is_authenticated:
            cart, _ = models.Cart.objects.get_or_create(uuid=request.session.get('cart'))
        else:
            _uuid = str(uuid.uuid4())
            new_cart = models.Cart(uuid=_uuid)
            new_cart.save()
            cart = models.Cart.objects.get(uuid=_uuid)
        request.session['cart'] = str(cart.uuid)
        reservation = models.Reservation(
            cart=cart,
            item=models.Item.objects.get(uuid=request.POST.get('item')),
            start_date=request.GET.get('start_date'),
            return_date=request.GET.get('return_date'),
            total_fee=self.fee_calculator(),
        )
        if request.user.is_authenticated:
            reservation.user = request.user
            reservation.zip_code = request.user.zip_code
            reservation.prefecture = request.user.prefecture
            reservation.city = request.user.city
            reservation.address = request.user.address
            reservation.address_name = request.user.address_name
            reservation.address_name_kana = request.user.address_name_kana
            reservation.email = request.user.email
            reservation.gender = request.user.gender
            reservation.age_range = request.user.age_range
        reservation.save()
        return redirect('main:cart', permanent=True)


class CartView(generic.ListView):
    model = models.Reservation
    context_object_name = 'reservations'
    template_name = 'main/cart.html'

    def get_queryset(self):
        if self.request.user.is_authenticated:
            cart, _ = models.Cart.objects.get_or_create(user=self.request.user)
        elif 'cart' in self.request.session and not self.request.user.is_authenticated:
            cart, _ = models.Cart.objects.get_or_create(uuid=self.request.session.get('cart'))
        else:
            _uuid = str(uuid.uuid4())
            new_cart = models.Cart(uuid=_uuid)
            new_cart.save()
            cart = models.Cart.objects.get(uuid=_uuid)
        self.request.session['cart'] = str(cart.uuid)
        return models.Reservation.objects.filter(cart=cart, status=1).order_by('-created_at')

    def post(self, request):
        request.session['reservation'] = request.POST.get('reservation')
        return redirect('main:rental')


class RentalView(generic.UpdateView):
    model = models.Reservation
    form_class = forms.RentalForm
    template_name = 'main/rental.html'
    success_url = reverse_lazy('main:rental_confirm')

    def get_object(self, queryset=None):
        obj = models.Reservation.objects.get(uuid=self.request.session.get('reservation'))
        return obj


class RentalConfirmView(generic.DetailView):
    model = models.Reservation
    context_object_name = 'reservation'
    template_name = 'main/rental_confirm.html'

    def get_object(self, queryset=None):
        obj = models.Reservation.objects.get(uuid=self.request.session.get('reservation'))
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reservation = models.Reservation.objects.get(uuid=self.request.session.get('reservation'))
        delta = reservation.return_date - reservation.start_date
        context['days'] = delta.days + 1
        return context


class RentalCheckoutView(generic.View):

    def post(self, request):
        reservation = models.Reservation.objects.get(uuid=request.session.get('reservation'))

        stripe.api_key = settings.STRIPE_API_KEY
        token = request.POST.get('stripeToken')
        charge = stripe.Charge.create(
            amount=reservation.total_fee,
            currency='jpy',
            description='支払い',
            source=token,
        )

        reservation.status = 0
        reservation.save()
        if request.user.is_authenticated:
            request.user.zip_code = reservation.zip_code
            request.user.prefecture = reservation.prefecture
            request.user.city = reservation.city
            request.user.address = reservation.address
            request.user.address_name = reservation.address_name
            request.user.address_name_kana = reservation.address_name_kana
            request.user.gender = reservation.gender
            request.user.age_range = reservation.age_range
            request.user.save()
            del request.session['reservation']
        return redirect(reverse_lazy('main:rental_complete'), permanent=True)


class RentalCompleteView(generic.CreateView):
    model = User
    form_class = UserForm
    template_name = 'main/rental_complete.html'
    success_url = reverse_lazy('accounts:complete')

    def form_valid(self, form):
        form.instance.password = make_password(self.request.POST.get('password'))
        _uuid = str(uuid.uuid4())
        new_user = form.save(commit=False)
        new_user.uuid = _uuid
        new_user.save()
        user = User.objects.get(uuid=_uuid)
        if 'reservation' in self.request.session:
            try:
                reservation = models.Reservation.objects.get(uuid=self.request.session.get('reservation'))
                reservation.user = user
                reservation.save()
                request.user.zip_code = reservation.zip_code
                request.user.prefecture = reservation.prefecture
                request.user.city = reservation.city
                request.user.address = reservation.address
                request.user.address_name = reservation.address_name
                request.user.address_name_kana = reservation.address_name_kana
                request.user.gender = reservation.gender
                request.user.age_range = reservation.age_range
                request.user.save()
            except models.Reservation.DoesNotExist:
                pass
            del self.request.session['reservation']
        if 'cart' in self.request.session:
            try:
                cart = models.Cart.objects.get(uuid=self.request.session.get('cart'))
                cart.user = user
                cart.save()
            except models.Cart.DoesNotExist:
                pass

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

class RentalCompleteSocialView(generic.View):

    def get(self, request):
        user = request.user
        if 'reservation' in self.request.session:
            try:
                reservation = models.Reservation.objects.get(uuid=request.session.get('reservation'))
                reservation.user = user
                try:
                    cart = models.Cart.objects.get(user=request.user)
                    reservation.cart = cart
                    request.session['cart'] = str(cart.uuid)
                except models.Cart.DoesNotExist:
                    pass
                reservation.save()
                request.user.zip_code = reservation.zip_code
                request.user.prefecture = reservation.prefecture
                request.user.city = reservation.city
                request.user.address = reservation.address
                request.user.address_name = reservation.address_name
                request.user.address_name_kana = reservation.address_name_kana
                request.user.gender = reservation.gender
                request.user.age_range = reservation.age_range
                request.user.save()
            except models.Reservation.DoesNotExist:
                pass
            del request.session['reservation']
        if 'cart' in request.session:
            try:
                _ = models.Cart.objects.get(user=request.user)
            except models.Cart.DoesNotExist:
                try:
                    cart = models.Cart.objects.get(uuid=request.session.get('cart'))
                    cart.user = request.user
                    cart.save()
                except models.Cart.DoesNotExist:
                    pass
        return redirect('accounts:signup_social', permanent=True)
