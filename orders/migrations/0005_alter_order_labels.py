from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("orders", "0004_orderitem_product_name")]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="vehicle",
            field=models.CharField(
                blank=True, max_length=120, verbose_name="السيارة والموديل"
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="notes",
            field=models.TextField(blank=True, max_length=500, verbose_name="ملاحظات"),
        ),
    ]
