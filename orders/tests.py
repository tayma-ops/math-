from decimal import Decimal
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from products.models import Category, Product
from .models import Cart, CartItem, CheckoutAttempt, Order


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("buyer", password="IndependentTest77!")
        self.other = User.objects.create_user("other", password="IndependentTest77!")
        cat = Category.objects.create(name="تجربة")
        self.product = Product.objects.create(
            category=cat, name="منتج", description="وصف", price="12.50", stock=3
        )
        self.client.force_login(self.user)
        self.cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)
        self.receipt = CheckoutAttempt.objects.create(user=self.user)
        self.data = {
            "token": str(self.receipt.pk),
            "full_name": "عميل تجربة",
            "phone": "0500000000",
            "city": "الرياض",
            "address": "عنوان تجريبي",
            "total_price": "0.01",
        }

    def checkout(self):
        return self.client.post(reverse("orders:checkout"), self.data)

    def test_checkout_is_server_priced_and_retry_is_idempotent(self):
        self.assertEqual(self.checkout().status_code, 302)
        self.assertEqual(self.checkout().status_code, 302)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.get().total_price, Decimal("25.00"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)
        self.assertFalse(self.cart.items.exists())
        self.product.price = Decimal("99")
        self.product.save()
        self.assertEqual(Order.objects.get().items.get().price, Decimal("12.50"))

    def test_insufficient_stock_rolls_back_everything(self):
        self.product.stock = 1
        self.product.save()
        self.assertEqual(self.checkout().status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.assertEqual(self.cart.items.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

    def test_cancellation_restocked_only_once_and_private_orders(self):
        self.checkout()
        order = Order.objects.get()
        url = reverse("orders:cancel", args=[order.pk])
        self.client.post(url)
        self.client.post(url)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("orders:detail", args=[order.pk])).status_code, 404
        )
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_foreign_cart_and_token_are_not_usable(self):
        self.client.force_login(self.other)
        item = self.cart.items.get()
        self.assertEqual(
            self.client.post(
                reverse("orders:update", args=[item.pk]), {"quantity": 1}
            ).status_code,
            404,
        )
        self.assertEqual(self.checkout().status_code, 200)
        self.assertFalse(Order.objects.exists())

    def test_login_csrf_and_invalid_quantity(self):
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.user)
        self.assertEqual(
            c.post(
                reverse("orders:add", args=[self.product.pk]), {"quantity": 1}
            ).status_code,
            403,
        )
        self.client.post(
            reverse("orders:add", args=[self.product.pk]), {"quantity": -2}
        )
        self.assertEqual(self.cart.items.get().quantity, 2)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("orders:cart")).status_code, 302)

    def test_closed_or_paid_order_cannot_cancel(self):
        self.checkout()
        order = Order.objects.get()
        order.status = "shipped"
        order.save()
        self.client.post(reverse("orders:cancel", args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

    def test_empty_cart_invalid_phone_and_foreign_receipt(self):
        self.cart.items.all().delete()
        self.checkout()
        self.assertFalse(Order.objects.exists())
        self.data["phone"] = "invalid"
        self.checkout()
        self.assertFalse(Order.objects.exists())

    def test_partial_stock_changes_are_rolled_back_on_second_product_failure(self):
        second = Product.objects.create(
            category=self.product.category, name="غير متوفر", price="10", stock=0
        )
        CartItem.objects.create(cart=self.cart, product=second, quantity=1)
        self.assertEqual(self.checkout().status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    def test_order_keeps_original_name_after_catalog_edit(self):
        self.checkout()
        item = Order.objects.get().items.get()
        self.product.name = "اسم جديد"
        self.product.save()
        self.assertEqual(item.product_name, "منتج")
        response = self.client.get(reverse("orders:detail", args=[item.order_id]))
        self.assertNotContains(response, "اسم جديد")
