from django.urls import path
from .views import (
    remove_from_cart,
    reduce_quantity_item,
    add_to_cart,
    index,
    complete_payment,
    ProductView,
    HomeView,
    OrderSummaryView,
    CheckoutView,
    PaymentView, SignUpView, account_view, OrdersView, latest_orders, update_status
)

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('index/', index, name='index'),
    path('product/<pk>/', ProductView.as_view(), name='product'),
    path('order-summary/', OrderSummaryView.as_view(), name='order-summary'),
    path('orders/', OrdersView.as_view(), name='orders'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('payment/<payment_option>/', PaymentView.as_view(), name='payment'),
    path('add-to-cart/<pk>/', add_to_cart, name='add-to-cart'),
    path('remove-from-cart/<pk>/', remove_from_cart, name='remove-from-cart'),
    path('reduce-quantity-item/<pk>/', reduce_quantity_item, name='reduce-quantity-item'),
    path('complete_payment/', complete_payment, name='complete_payment'),
    path("signup/", SignUpView.as_view(), name="signup"),
    path('profile/', account_view, name="account"),
    path('latest_orders/', latest_orders, name='latest_orders'),
    path('update_status/', update_status, name='update_status'),

]


