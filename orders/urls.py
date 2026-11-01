from django.urls import path
from . import views

app_name = "orders"
urlpatterns = [
    path("", views.history, name="history"),
    path("cart/", views.cart, name="cart"),
    path("cart/add/<int:product_id>/", views.add, name="add"),
    path("cart/update/<int:item_id>/", views.update, name="update"),
    path("cart/remove/<int:item_id>/", views.remove, name="remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("<int:order_id>/", views.detail, name="detail"),
    path("<int:order_id>/cancel/", views.cancel, name="cancel"),
]
