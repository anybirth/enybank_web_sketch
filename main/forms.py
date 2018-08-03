from django import forms
from django.utils.translation import gettext_lazy as _
from . import models

class RentalForm(forms.ModelForm):
    class Meta:
        model = models.Reservation
        fields = ['address_name', 'zip_code', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for fieldname in ['address_name', 'zip_code', 'address']:
            self.fields[fieldname].required = True
