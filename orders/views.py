from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from products.models import Product
from .forms import CheckoutForm, QuantityForm
from .models import Cart, CartItem, CheckoutAttempt, Order
from .services import cancel_order, place_order


def cart_for(user):
    return Cart.objects.get_or_create(user=user)[0]


@login_required
@require_GET
def cart(request):
    items = list(cart_for(request.user).items.select_related("product").all())
    return render(
        request,
        "orders/cart.html",
        {
            "items": items,
            "total": sum((i.get_total_price() for i in items), Decimal("0")),
        },
    )


@login_required
@require_POST
def add(request, product_id):
    form = QuantityForm(request.POST)
    if form.is_valid():
        with transaction.atomic():
            cart = cart_for(request.user)
            # Serialize mutations with checkout, also on SQLite.
            Cart.objects.filter(pk=cart.pk).update(user=request.user)
            product = get_object_or_404(Product, pk=product_id, is_available=True)
            item = cart.items.filter(product=product).first()
            quantity = form.cleaned_data["quantity"] + (item.quantity if item else 0)
            if quantity <= min(product.stock, 99):
                if item:
                    item.quantity = quantity
                    item.save(update_fields=["quantity"])
                else:
                    CartItem.objects.create(
                        cart=cart, product=product, quantity=quantity
                    )
                messages.success(request, "أُضيف المنتج إلى السلة.")
            else:
                messages.error(request, "الكمية المطلوبة غير متوفرة.")
    else:
        messages.error(request, "أدخل كمية صحيحة من 1 إلى 99.")
    return redirect("orders:cart")


@login_required
@require_POST
def update(request, item_id):
    form = QuantityForm(request.POST)
    with transaction.atomic():
        cart = cart_for(request.user)
        Cart.objects.filter(pk=cart.pk).update(user=request.user)
        item = get_object_or_404(
            CartItem.objects.select_related("product"), pk=item_id, cart=cart
        )
        if (
            form.is_valid()
            and form.cleaned_data["quantity"] <= item.product.stock
            and item.product.is_available
        ):
            item.quantity = form.cleaned_data["quantity"]
            item.save(update_fields=["quantity"])
        else:
            messages.error(request, "تحقق من الكمية وتوفر المنتج.")
    return redirect("orders:cart")


@login_required
@require_POST
def remove(request, item_id):
    with transaction.atomic():
        cart = cart_for(request.user)
        Cart.objects.filter(pk=cart.pk).update(user=request.user)
        get_object_or_404(CartItem, pk=item_id, cart=cart).delete()
    return redirect("orders:cart")


@login_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    cart_for(request.user)
    initial = {"full_name": request.user.get_full_name()}
    initial.update(
        {k: v for k, v in request.session.get("checkout_initial", {}).items() if v}
    )
    profile = getattr(request.user, "profile", None)
    if profile:
        initial.update(
            {key: getattr(profile, key) for key in ["phone", "city", "address"]}
        )
    if request.method == "GET":
        token = CheckoutAttempt.objects.create(user=request.user)
        initial["token"] = token.pk
    form = CheckoutForm(
        request.POST if request.method == "POST" else None, initial=initial
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data.copy()
        token = data.pop("token")
        try:
            order = place_order(request.user, token, data)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            request.session["clear_browser_cart"] = True
            request.session.pop("checkout_initial", None)
            messages.success(request, "حُفظ طلبك. طريقة الدفع: عند الاستلام.")
            return redirect("orders:detail", order_id=order.pk)
    return render(request, "orders/checkout.html", {"form": form})


@login_required
@require_GET
def history(request):
    return render(
        request,
        "orders/history.html",
        {"orders": Order.objects.filter(user=request.user).order_by("-created_at")},
    )


@login_required
@require_GET
def detail(request, order_id):
    order = get_object_or_404(
        Order.objects.prefetch_related("items__product"), pk=order_id, user=request.user
    )
    return render(
        request,
        "orders/detail.html",
        {
            "order": order,
            "clear_browser_cart": request.session.pop("clear_browser_cart", False),
            "browser_cart_key": "autoPartsCart",
        },
    )


@login_required
@require_POST
def cancel(request, order_id):
    get_object_or_404(Order, pk=order_id, user=request.user)
    try:
        cancel_order(order_id, request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect("orders:detail", order_id=order_id)
