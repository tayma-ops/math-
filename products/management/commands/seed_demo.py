from django.core.management.base import BaseCommand
from products.models import Category, Product

DATA = [
    ("1", "فلتر زيت المحرك", "فلاتر", "45", "قطعة عرض؛ تحقق من توافقها مع سيارتك."),
    ("2", "فحمات فرامل أمامية", "فرامل", "180", "قطعة عرض؛ تحقق من توافقها مع سيارتك."),
    ("3", "بطارية سيارة", "بطاريات", "350", "قطعة عرض؛ تحقق من توافقها مع سيارتك."),
    ("4", "زيت محرك صناعي", "زيوت", "120", "قطعة عرض؛ تحقق من توافقها مع سيارتك."),
    ("5", "شمعات احتراق بواجي", "محركات", "85", "قطعة عرض؛ تحقق من توافقها مع سيارتك."),
    ("6", "فلتر هواء المحرك", "فلاتر", "65", "قطعة عرض؛ تحقق من توافقها مع سيارتك."),
    ("7", "لمبات أمامية LED", "إضاءة", "95", "قطعة عرض؛ تحقق من توافقها مع سيارتك."),
    (
        "8",
        "حامل جوال للسيارة",
        "إكسسوارات",
        "55",
        "قطعة عرض؛ تحقق من توافقها مع سيارتك.",
    ),
]


class Command(BaseCommand):
    help = (
        "Create a fictional demo catalog; existing items and accounts remain unchanged."
    )

    def handle(self, *args, **options):
        for code, name, category, price, description in DATA:
            group, _ = Category.objects.get_or_create(name=category)
            Product.objects.get_or_create(
                sku=code,
                defaults={
                    "name": name,
                    "category": group,
                    "price": price,
                    "description": description,
                    "stock": 50,
                },
            )
        self.stdout.write(
            self.style.SUCCESS("Demo catalog is ready. No accounts created.")
        )
