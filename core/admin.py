from django.contrib import admin
from .models import (
    Item,
    OrderItem,
    Order,
    CheckoutAddress,
    Payment, Stock, Deal, Article, Comment
)

admin.site.register(Item)
admin.site.register(OrderItem)
admin.site.register(Order)
admin.site.register(CheckoutAddress)
admin.site.register(Payment)
admin.site.register(Stock)
admin.site.register(Deal)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'status', 'created_on', 'image')
    list_filter = ('status',)
    search_fields = ['title', 'post']
    prepopulated_fields = {'slug': ('title',)}


admin.site.register(Article, ArticleAdmin)
admin.site.register(Comment)
