from django.db import models
from django.contrib.auth.models import User

from products.models import Product


class Cart(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="cart", verbose_name="المستخدم"
    )

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="تاريخ إنشاء السلة"
    )

    class Meta:
        verbose_name = "سلة التسوق"
        verbose_name_plural = "سلال التسوق"

    def __str__(self):
        return f"سلة - {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items", verbose_name="سلة التسوق"
    )

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, verbose_name="المنتج"
    )

    quantity = models.PositiveIntegerField(default=1, verbose_name="الكمية")

    class Meta:
        verbose_name = "عنصر في السلة"
        verbose_name_plural = "عناصر السلة"

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    def get_total_price(self):
        return self.product.price * self.quantity


class Order(models.Model):
    vehicle = models.CharField(
        max_length=120, blank=True, verbose_name="السيارة والموديل"
    )
    notes = models.TextField(max_length=500, blank=True, verbose_name="ملاحظات")
    STATUS_CHOICES = [
        ("pending", "قيد الانتظار"),
        ("processing", "قيد التجهيز"),
        ("shipped", "تم الشحن"),
        ("delivered", "تم التوصيل"),
        ("cancelled", "ملغي"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="orders", verbose_name="المستخدم"
    )

    full_name = models.CharField(max_length=200, verbose_name="الاسم الكامل")

    phone = models.CharField(max_length=20, verbose_name="رقم الهاتف")

    city = models.CharField(max_length=100, verbose_name="المدينة")

    address = models.TextField(verbose_name="العنوان")

    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="إجمالي السعر"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="حالة الطلب",
    )

    is_paid = models.BooleanField(default=False, verbose_name="تم الدفع")

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="تاريخ إنشاء الطلب"
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")

    class Meta:
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"

    def __str__(self):
        return f"طلب رقم {self.id} - {self.user.username}"


class OrderItem(models.Model):
    product_name = models.CharField(
        max_length=200, blank=True, verbose_name="اسم المنتج عند الطلب"
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name="الطلب"
    )

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, verbose_name="المنتج"
    )

    quantity = models.PositiveIntegerField(default=1, verbose_name="الكمية")

    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر")

    class Meta:
        verbose_name = "عنصر طلب"
        verbose_name_plural = "عناصر الطلب"

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    def get_total_price(self):
        return self.price * self.quantity


class CheckoutAttempt(models.Model):
    """One receipt per submitted checkout, making retries safe."""

    import uuid

    token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.OneToOneField(Order, null=True, blank=True, on_delete=models.PROTECT)
    claimed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
