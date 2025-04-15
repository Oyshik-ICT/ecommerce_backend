from django.contrib import admin
from .models import CustomUser, Category, Product

admin.site.register(CustomUser)
admin.site.register(Category)
admin.site.register(Product)

# Register your models here.
