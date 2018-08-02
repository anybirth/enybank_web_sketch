from django.urls import path
from . import views

app_name = 'accounts'
urlpatterns = [
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('complete/', views.CompleteView.as_view(), name='complete'),
    path('activate/<uuid:uuid>/', views.ActivateView.as_view(), name='activate'),
    path('activate/expired/', views.ActivateExpiredView.as_view(), name='activate_expired'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
]
