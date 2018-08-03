from datetime import date, datetime, timedelta
from django.views import generic
from django.shortcuts import render
from . import models, forms

# Create your views here.

class IndexView(generic.TemplateView):
    template_name = 'main/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['color_categories'] = models.ColorCategory.objects.all()
        context['types'] = models.Type.objects.all()
        return context


class SearchView(generic.TemplateView):
    template_name = 'main/search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['item'] = models.Item.objects.get(
            color_category=self.request.GET.get('color_category'),
            type=self.request.GET.get('type')
        )

        item = context['item']
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
                    context['fee'] = round(fee, -1)
                    return context
                elif end_point < days:
                    fee += fee_coef * (end_point - starting_point)
            else:
                fee += fee_coef * (days - starting_point)
                context['fee'] = round(fee, -1)
                return context

        context['fee'] = round(fee, -1)
        return context
