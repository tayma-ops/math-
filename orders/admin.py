from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import Cart, Order, OrderItem
from .services import cancel_order


class ItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "price")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "full_name",
        "total_price",
        "status",
        "is_paid",
        "created_at",
    )
    list_filter = ("status", "is_paid", "created_at")
    search_fields = ("full_name", "phone", "user__username")
    readonly_fields = tuple(f.name for f in Order._meta.fields)
    inlines = [ItemInline]
    actions = ("process", "ship", "deliver", "cancel_pending", "record_cash")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="بدء تجهيز الطلبات المنتظرة")
    def process(self, request, queryset):
        queryset.filter(status="pending").update(status="processing")

    @admin.action(description="تسجيل شحن الطلبات المجهزة")
    def ship(self, request, queryset):
        queryset.filter(status="processing").update(status="shipped")

    @admin.action(description="تسجيل تسليم الطلبات المشحونة")
    def deliver(self, request, queryset):
        queryset.filter(status="shipped").update(status="delivered")

    @admin.action(description="إلغاء الطلبات المنتظرة وإعادة المخزون")
    def cancel_pending(self, request, queryset):
        for order in queryset:
            try:
                cancel_order(order.pk, request.user, staff=True)
            except ValidationError as exc:
                self.message_user(request, " ".join(exc.messages), messages.ERROR)

    @admin.action(description="تسجيل استلام الدفع النقدي للطلبات المسلمة")
    def record_cash(self, request, queryset):
        queryset.filter(status="delivered").update(is_paid=True)
