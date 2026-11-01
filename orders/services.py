"""Transactional checkout: prices and stock are always owned by the server."""

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from products.models import Product
from .models import Cart, CheckoutAttempt, Order, OrderItem


@transaction.atomic
def place_order(user, token, data):
    # The write acquires SQLite's write lock before the cart is read. On other
    # databases select_for_update protects the same receipt and cart rows.
    if not CheckoutAttempt.objects.filter(pk=token, user=user).update(claimed=True):
        raise ValidationError("انتهت صلاحية نموذج الطلب. أعد فتح صفحة إتمام الطلب.")
    receipt = CheckoutAttempt.objects.select_for_update().get(pk=token, user=user)
    if receipt.order_id:
        return receipt.order
    cart = Cart.objects.select_for_update().get(user=user)
    items = list(cart.items.select_related("product").order_by("product_id"))
    if not items:
        raise ValidationError("السلة فارغة.")
    total = Decimal("0")
    for item in items:
        product = item.product
        if not 1 <= item.quantity <= 99 or product.price <= 0:
            raise ValidationError("تحقق من كميات المنتجات وأسعارها.")
        if not Product.objects.filter(
            pk=product.pk, is_available=True, stock__gte=item.quantity
        ).update(stock=F("stock") - item.quantity):
            raise ValidationError(
                "الكمية المطلوبة من «" + product.name + "» غير متوفرة."
            )
        total += product.price * item.quantity
    if total > Decimal("99999999.99"):
        raise ValidationError("قيمة الطلب تتجاوز الحد المسموح.")
    order = Order.objects.create(user=user, total_price=total, **data)
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                product=item.product,
                product_name=item.product.name,
                quantity=item.quantity,
                price=item.product.price,
            )
            for item in items
        ]
    )
    cart.items.all().delete()
    receipt.order = order
    receipt.save(update_fields=["order"])
    return order


@transaction.atomic
def cancel_order(order_id, user, staff=False):
    orders = Order.objects.filter(pk=order_id)
    if not staff:
        orders = orders.filter(user=user)
    if not orders.filter(status="pending", is_paid=False).update(status="cancelled"):
        raise ValidationError("يمكن إلغاء طلب غير مدفوع وقيد الانتظار فقط.")
    order = orders.get()
    for item in order.items.all():
        Product.objects.filter(pk=item.product_id).update(
            stock=F("stock") + item.quantity
        )
    return order
