from django import forms
from django.db.models import ImageField
from django.forms import TextInput, NumberInput, Textarea, Select, FileInput
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, PasswordResetForm
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget, RegionalPhoneNumberWidget

from core.models import Item, Article

PAYMENT = (
    ('S', 'Stripe'),
    ('P', 'PayPal'),
    ('F', 'Nigeria')
)


class CheckoutForm(forms.Form):
    street_address = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': '1234 Main St'
    }))

    apartment_address = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Apartment or suite'
    }))

    country = CountryField(blank_label='(select country)', default='NG').formfield(widget=CountrySelectWidget(attrs={
        'class': 'custom-select d-block w-100'
    }))

    phone = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Phone Number'
    }))

    zip = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control'
    }))

    same_billing_address = forms.BooleanField(required=False)
    save_info = forms.BooleanField(required=False)
    payment_option = forms.ChoiceField(
        widget=forms.RadioSelect, choices=PAYMENT, initial='F')


class RegistrationForm(UserCreationForm):
    """
      Form for Registering new users
    """
    email = forms.EmailField(max_length=60, help_text='Required. Add a valid email address')

    class Meta:
        model = get_user_model()
        fields = ('first_name', 'last_name', 'email', 'username', 'password1', 'password2')


class AccountAuthenticationForm(forms.ModelForm):
    """
      Form for Logging in  users
    """
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

    class Meta:
        model = get_user_model()
        fields = ('email', 'password')
        widgets = {
            'email': forms.TextInput(attrs={'class': 'form-control'}),
            'password': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        if self.is_valid():

            email = self.cleaned_data.get('email')
            password = self.cleaned_data.get('password')
            if not authenticate(email=email, password=password):
                raise forms.ValidationError('Invalid Login')


class AccountUpdateform(forms.ModelForm):
    """
      Updating User Info
    """

    class Meta:
        model = get_user_model()
        fields = ('email', 'username')

    def clean_email(self):
        if self.is_valid():
            email = self.cleaned_data['email']
            Account = get_user_model()
            try:
                account = Account.objects.exclude(pk=self.instance.pk).get(email=email)
            except Account.DoesNotExist:
                return email
            raise forms.ValidationError("Email '%s' already in use." % email)

    def clean_username(self):
        if self.is_valid():
            username = self.cleaned_data['username']
            Account = get_user_model()
            try:
                account = Account.objects.exclude(pk=self.instance.pk).get(username=username)
            except Account.DoesNotExist:
                return username
            raise forms.ValidationError("Username '%s' already in use." % username)

class ProductUpdateForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ('item_name', 'price','discount_price','category','label','description','image','initial_stock','topup_stock','total_stock','current_stock')
        widgets = {
            'item_name': TextInput(attrs={'class': 'form-control'}),
            'price': TextInput(attrs={'class': 'form-control'}),
            'discount_price': NumberInput(attrs={'class': 'form-control'}),
            'category': Select(attrs={'class': "form-control w-100"}),
            'label': Select(attrs={'class': "form-control w-100"}),
            'description': Textarea(attrs={'class': 'form-control'}),
            'image': FileInput(),
            'initial_stock': NumberInput(attrs={'class': 'form-control'}),
            'topup_stock': NumberInput(attrs={'class': 'form-control'}),
            'total_stock': NumberInput(attrs={'class': 'form-control'}),
            'current_stock': NumberInput(attrs={'class': 'form-control'}),
        }

class ChangePasswordForm(PasswordChangeForm):
    old_password = forms.CharField(label="Old password:",
                                   max_length=32, widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password1 = forms.CharField(label="New password:", help_text="<small><ul class='form-text text-muted'><li>Your password can\'t be too similar to your other personal information.</li><li>Your password must contain at least 8 characters.</li><li>Your password can\'t be a commonly used password.</li><li>Your password can\'t be entirely numeric.</li></ul></small>",
                                    max_length=32, widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password2 = forms.CharField(label="New password confirmation:",
                                    max_length=32, widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User

class ResetPasswordForm(forms.Form):
    email = forms.EmailField(label="",
                             max_length=50, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Registered email address'}))

class NewsArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ('title', 'slug', 'author', 'post', 'image', 'status')
        widgets = {
            'title': TextInput(attrs={'class': 'form-control', 'placeholder':'News Title'}),
            'slug': TextInput(attrs={'class': 'form-control', 'readonly':'readonly', 'placeholder':'Slug'}),
            'author': Select(attrs={'class': 'form-control', 'readonly':'readonly', 'placeholder':'Author'}),
            'post': Textarea(attrs={'class': "form-control w-100", 'placeholder':'News Post'}),
            'image': FileInput(),
            'status': Select(attrs={'class': 'form-control'})
        }
