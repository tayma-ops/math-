from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from .frontend import frontend
from . import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("orders/", include("orders.urls")),
    path("api/session/", api.session),
    path("api/catalog/", api.catalog),
    path("api/cart/import/", api.import_cart),
    path("", frontend),
    path("<path:path>", frontend),
]
if settings.DEBUG:
    urlpatterns = (
        static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + urlpatterns
    )
