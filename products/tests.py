import json
from django.test import TestCase
from django.contrib.auth.models import User
from products.models import Category, Product
from orders.models import Cart


class StoreApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("api", password="IndependentTest77!")
        c = Category.objects.create(name="تجربة")
        self.p = Product.objects.create(
            category=c, name="منتج", price="15", stock=2, sku="demo"
        )

    def post(self, items):
        return self.client.post(
            "/api/cart/import/", {"items": items}, content_type="application/json"
        )

    def test_auth_stock_duplicates_and_catalog(self):
        self.assertEqual(self.post([{"code": "demo", "quantity": 1}]).status_code, 401)
        self.client.force_login(self.user)
        self.assertEqual(self.post([{"code": "demo", "quantity": 3}]).status_code, 400)
        self.assertEqual(
            self.post([{"code": "demo", "quantity": 1}] * 2).status_code, 400
        )
        self.assertEqual(
            self.post([{"code": "demo", "quantity": 1, "price": 0}]).status_code, 200
        )
        self.assertEqual(Cart.objects.get(user=self.user).items.get().product.price, 15)
        self.assertEqual(
            self.client.get("/api/catalog/").json()["products"][0]["code"], "demo"
        )

    def test_source_and_database_are_not_public(self):
        for path in [
            "/db.sqlite3",
            "/.env",
            "/.git/config",
            "/config/settings.py",
            "/manage.py",
        ]:
            self.assertEqual(self.client.get(path).status_code, 404)
