from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.contrib.auth.hashers import make_password
import uuid
from datetime import datetime

class CustomUserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email, and password.
        """
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.email
    
class Category(models.Model):
    class CategoryType(models.TextChoices):
        ELECTRONICS = "Electronics", "Electronics"
        CLOTHING = "Clothing", "Clothing"

    type = models.CharField(max_length=20, choices=CategoryType.choices)

    class Meta:
        db_table = 'categories'

    def __str__(self):
        return self.type

class Product(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")

    def __str__(self):
        return self.name
    
class Order(models.Model):
    class StatusChoice(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        CONFIRMED = 'Confirmed', 'Confirmed'
        CANCELLED = 'Cancelled', 'Cancelled'

    class PaymentStatusChoice(models.TextChoices):
        PAID = 'Paid', 'Paid'
        UNPAID = 'Unpaid', 'Unpaid'
        PAYMENT_PENDING = 'Payment Pending', 'Payment Pending'

    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="orders")
    product = models.ManyToManyField(Product, through="OrderItem", related_name="orders")
    status = models.CharField(max_length=10, choices=StatusChoice.choices, default=StatusChoice.PENDING)
    payment_status = models.CharField(max_length=15, choices=PaymentStatusChoice.choices, default=PaymentStatusChoice.UNPAID)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.order_id}, made by {self.user.email}"
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def sub_total(self):
        return self.product.price * self.quantity

class Cart(models.Model):
    cart_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="carts")
    product = models.ManyToManyField(Product, through="CartItem", related_name="carts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cartitems")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def sub_total(self):
        return self.product.price * self.quantity