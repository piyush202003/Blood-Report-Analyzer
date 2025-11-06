from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import BloodReport, AllergyInfo, HabitProgress

class BloodReportUploadForm(forms.ModelForm):
    class Meta:
        model = BloodReport
        fields = ['report_file']
        widgets = {
            'report_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            })
        }


class AllergyForm(forms.ModelForm):
    # Common allergies checklist
    dairy = forms.BooleanField(required=False, label="Dairy Products")
    nuts = forms.BooleanField(required=False, label="Nuts (Peanuts, Almonds, etc.)")
    shellfish = forms.BooleanField(required=False, label="Shellfish")
    eggs = forms.BooleanField(required=False, label="Eggs")
    soy = forms.BooleanField(required=False, label="Soy")
    wheat = forms.BooleanField(required=False, label="Wheat/Gluten")
    fish = forms.BooleanField(required=False, label="Fish")
    
    class Meta:
        model = AllergyInfo
        fields = ['user_mentioned_allergies']
        widgets = {
            'user_mentioned_allergies': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter any specific allergies not listed above...'
            })
        }


# New Authentication Forms
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'Email'
    }))
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Password'
    }))

class HabitProgressForm(forms.ModelForm):
    class Meta:
        model = HabitProgress
        fields = ['completed', 'notes']
        widgets = {
            'completed': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Add notes about your progress (optional)...'
            })
        }