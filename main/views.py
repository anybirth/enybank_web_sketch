import uuid
from datetime import date, datetime, timedelta
from django.urls import reverse_lazy
from django.views import generic
from django.shortcuts import render, redirect
from . import models, forms

# Create your views here.

class IndexView(generic.TemplateView):
    template_name = 'main/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['color_categories'] = models.ColorCategory.objects.all()
        context['types'] = models.Type.objects.all()
        return context


class SearchView(generic.ListView):
    model = models.Item
    context_object_name = 'items'
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

    def get_queryset(self):
        return models.Item.objects.filter(
            color_category=self.request.GET.get('color_category'),
            type=self.request.GET.get('type')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
