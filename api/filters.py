import django_filters
from .models import Product

class ProductFilter(django_filters.FilterSet):
    """Filter products by name, price, and category."""

    class Meta:
        model = Product
        fields = {
            "name": ["exact", "contains"],
            "price": ["exact", "lt", "gt", "range"],
            "category": ["exact"]
        }