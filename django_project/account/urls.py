from django.urls import path

from . import views

urlpatterns = [
    path('', views.settings, name='settings'),
    path('add_editor/', views.add_editor, name='add_editor'),
    path('remove_editor/', views.remove_editor, name='remove_editor'),
    path('status/', views.status, name='status'),
    path('payment/', views.payment, name='payment'),
    path('checkout/', views.checkout, name='checkout'),
]