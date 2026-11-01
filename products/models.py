from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from decimal import Decimal


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم التصنيف")

    description = models.TextField(blank=True, null=True, verbose_name="وصف التصنيف")

    class Meta:
        verbose_name = "تصنيف"
        verbose_name_plural = "التصنيفات"

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField(
        max_length=12,
        unique=True,
        null=True,
        blank=False,
        validators=[
            RegexValidator(
                r"^[1-9][0-9]{0,11}$", "Use a positive numeric product code."
            )
        ],
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name="التصنيف",
    )

    name = models.CharField(max_length=200, verbose_name="اسم المنتج")

    description = models.TextField(verbose_name="وصف المنتج")

    price = models.DecimalField(
        validators=[MinValueValidator(Decimal("0.01"))],
        max_digits=10,
        decimal_places=2,
        verbose_name="السعر",
    )

    stock = models.PositiveIntegerField(default=0, verbose_name="الكمية المتوفرة")

    image = models.ImageField(
        upload_to="products/", blank=True, null=True, verbose_name="صورة المنتج"
    )

    is_available = models.BooleanField(default=True, verbose_name="متوفر للبيع")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإضافة")

    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")

    class Meta:
        verbose_name = "منتج"
        verbose_name_plural = "المنتجات"

    def __str__(self):
        return self.name
