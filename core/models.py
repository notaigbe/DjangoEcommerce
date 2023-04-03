import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import models
from django.db.models import Q, F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import reverse
from django.utils import timezone
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

CATEGORY = (
    ('S', 'Fish'),
    ('SP', 'Palm Oil'),
    ('OW', 'Honey')
)

LABEL = (
    ('N', 'New'),
    ('BS', 'Discount')
)


class Item(models.Model):
    item_name = models.CharField(max_length=100)
    price = models.FloatField()
    discount_price = models.FloatField(blank=True, null=True)
    category = models.CharField(choices=CATEGORY, max_length=2)
    label = models.CharField(choices=LABEL, max_length=2)
    description = models.TextField()
    image = models.ImageField(upload_to='troika/accounts/products/', default='troika/accounts/products/default.jpg')
    initial_stock = models.IntegerField(default=0)
    topup_stock = models.IntegerField(default=0)
    total_stock = models.IntegerField(default=100)
    current_stock = models.IntegerField(default=0)
    def __str__(self):
        return self.item_name

    def get_absolute_url(self):
        return reverse("core:product", kwargs={
            "pk": self.pk

        })

    def get_add_to_cart_url(self):
        return reverse("core:add-to-cart", kwargs={
            "pk": self.pk
        })

    def get_remove_from_cart_url(self):
        return reverse("core:remove-from-cart", kwargs={
            "pk": self.pk
        })

    @property
    def get_total_stock(self):
        initial = self.initial_stock
        topup = self.topup_stock
        total = initial + topup
        return total

    def save(self, *args, **kwargs):
        self.total_stock = self.get_total_stock
        super().save(*args, **kwargs)

    @property
    def articles(self):
        articles = Article.objects.order_by('-created_on')[:3]
        return articles

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(current_stock__lte=F('total_stock')), name='current_stock_less_than_total_stock')
        ]

class Stock(models.Model):
    name = models.ForeignKey(Item, on_delete=models.CASCADE)
    initial_stock = models.IntegerField()
    current_stock = models.IntegerField()

    def __str__(self):
        return self.name.item_name


class OrderItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.item.item_name}"

    def get_total_item_price(self):
        return self.quantity * self.item.price

    def get_discount_item_price(self):
        return self.quantity * self.item.discount_price

    def get_amount_saved(self):
        return self.get_total_item_price() - self.get_discount_item_price()

    def get_final_price(self):
        if self.item.discount_price:
            return self.get_discount_item_price()
        return self.get_total_item_price()


class Order(models.Model):
    STATUS = (('1', 'New Order'), ('2', 'Processing'), ('3', 'Shipped'), ('4', 'Delivered'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField()
    ordered = models.BooleanField(default=False)
    checkout_address = models.ForeignKey(
        'CheckoutAddress', on_delete=models.SET_NULL, blank=True, null=True)
    payment = models.ForeignKey(
        'Payment', on_delete=models.SET_NULL, blank=True, null=True)
    delivery_status = models.CharField(choices=STATUS, max_length=10, default=1)

    def __str__(self):
        return self.user.username

    def get_total_price(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_final_price()
        return total

# @receiver(post_save, sender=Order)
# def notify_clients(sender, instance, **kwargs):
#     channel_layer = get_channel_layer()
#     async_to_sync(channel_layer.group_send)(
#         'orders',
#         {
#             'type': 'order_created',
#             'message': json.dumps({'latest_order': instance.id}),
#         }
#     )

class CheckoutAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    country = CountryField(multiple=False)
    zip = models.CharField(max_length=100)
    phone = models.CharField(max_length=11)

    def __str__(self):
        return self.user.username


class Payment(models.Model):
    transaction_id = models.CharField(max_length=50, unique=True)
    tx_ref = models.CharField(max_length=50, unique=True)
    pay_status = models.CharField(max_length=50, default='Processing')
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.SET_NULL, blank=True, null=True)
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        try:
            stock = Stock.objects.get(id=1)
            stock.current_stock -= 20
            stock.save()
        except Exception as e:
            print(e)
        super().save(*args, **kwargs)

class Deal(models.Model):
    PACKAGE = (('0', 'Kg'), ('1', 'bag'), ('2', 'bottle'), ('3', 'tonne'), ('4', 'bunch'))
    name = models.ForeignKey(Item, on_delete=models.DO_NOTHING)
    price = models.FloatField()
    packaging = models.CharField(choices=PACKAGE, max_length=6, default=0)
    deal = models.IntegerField()
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.name

STATUS = ((0, 'DRAFT'), (1, 'PUBLISH'))
CATEGORY = (('palmoil', 'Palm Oil'), ('honey', 'Honey'), ('fish', 'Smoked Catfish'))

class Article(models.Model):
    title = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.CharField(choices=CATEGORY, max_length=7, default='fish')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blog_posts')
    updated_on = models.DateTimeField(auto_now=True)
    post = models.TextField()
    created_on = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='troika/farmfresh/news/', default='troika/accounts/products/default.jpg')
    status = models.IntegerField(choices=STATUS, default=0)

    class Meta:
        ordering = ['created_on']

    def __str__(self):
        return self.title

    @property
    def comments(self):
        comments = Comment.objects.order_by('-created_on')[:5]
        return comments

class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    author = models.CharField(max_length=80)
    email = models.EmailField()
    body = models.TextField()
    created_on = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_on']

    def __str__(self):
        return 'Comment {} by {}'.format(self.body, self.name)