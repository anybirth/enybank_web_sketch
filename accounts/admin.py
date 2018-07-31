from django.contrib import admin
from django import forms
from main.admin import ReservationInline
from . import models

# Register your models here.

class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'line_id', 'zip_code', 'address')
    list_filter = ['created_at', 'updated_at']
    search_fields = ['email', 'line_id', 'facebook_id', 'first_name', 'last_name', 'zip_code', 'address', 'address_name']
    inlines = [ReservationInline]
