import json
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from products.models import Product
from orders.models import Cart, CartItem


@ensure_csrf_cookie
@require_GET
def session(request):
    return JsonResponse(
        {
            "authenticated": request.user.is_authenticated,
            "username": (
                request.user.get_username() if request.user.is_authenticated else ""
            ),
        }
    )


@require_GET
def catalog(request):
    products = (
        Product.objects.filter(is_available=True)
        .select_related("category")
        .order_by("pk")
    )
    return JsonResponse(
        {
            "products": [
                {
                    "id": p.pk,
                    "code": p.sku or str(p.pk),
                    "name": p.name,
                    "description": p.description,
                    "category": p.category.name,
                    "price": str(p.price),
                    "stock": p.stock,
                    "image": p.image.url if p.image else "",
                }
                for p in products
            ]
        }
    )


@require_POST
def import_cart(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "سجل الدخول أولًا لحفظ طلبك."}, status=401)
    if request.content_type != "application/json" or len(request.body) > 30000:
        return JsonResponse({"error": "صيغة الطلب غير صالحة."}, status=400)
    try:
        body = json.loads(request.body)
        items = body["items"]
        if not isinstance(items, list) or not 1 <= len(items) <= 100:
            raise ValueError
        clean = []
        seen = set()
        for item in items:
            code = str(item["code"])
            quantity = item["quantity"]
            if (
                isinstance(quantity, bool)
                or not isinstance(quantity, int)
                or not 1 <= quantity <= 99
                or code in seen
            ):
                raise ValueError
            seen.add(code)
            product = Product.objects.get(sku=code, is_available=True)
            if quantity > product.stock:
                raise ValueError
            clean.append((product, quantity))
        with transaction.atomic():
            cart, _ = Cart.objects.get_or_create(user=request.user)
            Cart.objects.filter(pk=cart.pk).update(user=request.user)
            cart.items.all().delete()
            CartItem.objects.bulk_create(
                [CartItem(cart=cart, product=p, quantity=q) for p, q in clean]
            )
        request.session["checkout_initial"] = {
            k: str(body.get(k, ""))[:200]
            for k in [
                "full_name",
                "phone",
                "city",
                "address",
                "vehicle",
                "fulfilment",
                "notes",
            ]
        }
        return JsonResponse({"checkout_url": "/orders/checkout/"})
    except (ValueError, TypeError, KeyError, Product.DoesNotExist):
        return JsonResponse(
            {"error": "تحقق من المنتجات والكميات المتوفرة ثم حاول مجددًا."}, status=400
        )
