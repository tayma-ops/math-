import re
from django import forms


class QuantityForm(forms.Form):
    quantity = forms.IntegerField(label="الكمية", min_value=1, max_value=99, initial=1)


class CheckoutForm(forms.Form):
    token = forms.UUIDField(widget=forms.HiddenInput)
    full_name = forms.CharField(label="الاسم الكامل", max_length=200)
    phone = forms.CharField(label="رقم الجوال", max_length=20)
    city = forms.CharField(label="المدينة", max_length=100)
    address = forms.CharField(label="العنوان", widget=forms.Textarea, max_length=2000)

    vehicle = forms.CharField(label="السيارة والموديل", max_length=120, required=False)
    notes = forms.CharField(
        label="ملاحظات", max_length=500, required=False, widget=forms.Textarea
    )

    def clean_phone(self):
        phone = self.cleaned_data["phone"].translate(
            str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        )
        phone = re.sub(r"[ ()-]", "", phone)
        if not re.fullmatch(r"(?:05[0-9]{8}|(?:\+?966)5[0-9]{8})", phone):
            raise forms.ValidationError("أدخل رقم جوال سعودي صحيحًا.")
        return phone
