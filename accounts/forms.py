from django import forms
from .models import PatientProfile

class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        exclude = ("user", "created_at")
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
        }
