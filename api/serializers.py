import logging

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from rest_framework import serializers

from .models import Cart, CartItem, Category, CustomUser, Order, OrderItem, Product
from .validators import quantity_validation

logger = logging.getLogger(__name__)


class CustomUserSerializer(serializers.ModelSerializer):
    """Serializer for CustomUser model with password hashing."""

    class Meta:
        model = CustomUser
        fields = ["email", "password"]

        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        """Create new user with hashed password."""

        try:
            validated_data["password"] = make_password(validated_data["password"])
            return super().create(validated_data)
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

    def update(self, instance, validated_data):
        """Update user with hashed password if provided."""

        update_fields = []
        try:
            if "password" in validated_data:
                validated_data["password"] = make_password(validated_data["password"])
                update_fields.append("password")

            for attr, value in validated_data.items():
                setattr(instance, attr, value)
                update_fields.append(attr)

            instance.save(update_fields=update_fields)

            return instance
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model with optimized updates."""

    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
    )

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "stock", "category", "image"]

    def update(self, instance, validated_data):
        """Update product with only changed fields."""

        try:
            update_fields = []

            for attr, value in validated_data.items():
                setattr(instance, attr, value)
                update_fields.append(attr)

            instance.save(update_fields=update_fields)

            return instance
        except Exception as e:
            logger.error(f"Error updating product: {str(e)}")
            raise


class BulkProductPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """Optimized field that fetches all products in a single query"""

    def __init__(self, *args, **kwargs):
        self.items_field_name = kwargs.pop("items_field_name", "items")
        super().__init__(*args, **kwargs)

    def to_internal_value(self, data):
        """Convert product ID to product instance with bulk optimization."""
        try:
            if not hasattr(self.root, "_prefetched_products"):
                product_ids = []
                if (
                    hasattr(self.root, "initial_data")
                    and self.items_field_name in self.root.initial_data
                ):

                    product_ids = [
                        item["product"]
                        for item in self.root.initial_data[self.items_field_name]
                        if isinstance(item, dict) and "product" in item
                    ]

                    if product_ids:
                        products = self.get_queryset().filter(id__in=product_ids)
                        self.root._prefetched_products = {
                            str(p.pk): p for p in products
                        }

            if (
                hasattr(self.root, "_prefetched_products")
                and str(data) in self.root._prefetched_products
            ):
                return self.root._prefetched_products[str(data)]

            return super().to_internal_value(data)
        except Exception as e:
            logger.error(f"Error in bulk product field conversion: {str(e)}")
            raise


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for OrderItem model with bulk product optimization."""

    product = BulkProductPrimaryKeyRelatedField(
        queryset=Product.objects.all(), items_field_name="items"
    )

    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for Order model with stock management and bulk operations."""

    items = OrderItemSerializer(many=True)
    total_money = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "order_id",
            "user",
            "items",
            "status",
            "created_at",
            "total_money",
            "payment_id",
            "payment_status",
        ]

        extra_kwargs = {
            "order_id": {"read_only": True},
            "user": {"read_only": True},
            "payment_id": {"read_only": True},
            "payment_status": {"read_only": True},
            "created_at": {"read_only": True},
        }

    def get_total_money(self, obj):
        """Calculate total money from all order items."""

        try:
            order_items = obj.items.all()

            res = 0
            for order_item in order_items:
                res += order_item.sub_total()

            return res
        except Exception as e:
            logger.error(f"Error calculating total money: {str(e)}")
            return 0

    def update_stock_for_create(self, product, quantity):
        """Update product stock when creating order."""

        product.stock = product.stock - quantity

    def update_stock_for_update(
        self, previous_quantity, new_quantity, product_obj, update_products_stock
    ):
        """Update product stock when updating order."""
        try:
            if new_quantity == 0:
                raise serializers.ValidationError(
                    "You have to choose atleast 1 quantity"
                )
            if previous_quantity > new_quantity:
                product_obj.stock += previous_quantity - new_quantity
                update_products_stock.append(product_obj)

            else:
                if (new_quantity - previous_quantity) > product_obj.stock:
                    raise serializers.ValidationError(
                        "You have to choose less quantity"
                    )
                product_obj.stock -= new_quantity - previous_quantity
                update_products_stock.append(product_obj)
        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error updating stock: {str(e)}")
            raise

    def create(self, validated_data):
        """Create order with stock management and bulk operations."""

        try:
            items = validated_data.pop("items")

            quantity_validation(items)

            instance = Order.objects.create(**validated_data)

            update_products_stock, item_to_create = [], []

            for item in items:
                item_to_create.append(
                    OrderItem(
                        order=instance,
                        product=item.get("product"),
                        quantity=item.get("quantity"),
                    )
                )

                self.update_stock_for_create(item["product"], item["quantity"])
                update_products_stock.append(item["product"])

            Product.objects.bulk_update(update_products_stock, ["stock"])
            OrderItem.objects.bulk_create(item_to_create)

            return instance
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            raise

    def to_representation(self, instance):
        """Optimize data representation with prefetch."""

        try:
            if (
                not hasattr(instance, "_prefetched_objects_cache")
                or "items" not in instance._prefetched_objects_cache
            ):
                instance = (
                    Order.objects.filter(pk=instance.pk)
                    .prefetch_related("items__product")
                    .first()
                )
            return super().to_representation(instance)
        except Exception as e:
            logger.error(f"Error in order representation: {str(e)}")
            return super().to_representation(instance)

    def restore_product_stock(self, instance):
        """Restores stock for all products in the given order."""
        try:
            order_items = instance.items.select_related("product")
            update_products = []

            for order_item in order_items:
                order_item.product.stock += order_item.quantity
                update_products.append(order_item.product)

            Product.objects.bulk_update(update_products, fields=["stock"])
        except Exception as e:
            logger.error(f"Error restoring product stock: {str(e)}")
            raise

    def update(self, instance, validated_data):
        """Update order with stock management."""

        try:
            if "status" in validated_data:
                instance.status = validated_data.get("status")
                if validated_data.get("status") == "Cancelled":
                    self.restore_product_stock(instance)

                instance.save(update_fields=["status"])

            if "items" in validated_data:
                items = validated_data["items"]
                order_items = OrderItem.objects.filter(order=instance).select_related(
                    "product"
                )
                (
                    dict_order_item,
                    item_to_create,
                    item_to_update,
                    update_products_stock,
                ) = ({}, [], [], [])

                for order_item in order_items:
                    dict_order_item[order_item.product.id] = order_item

                for item in items:
                    if item["product"].id in dict_order_item:
                        self.update_stock_for_update(
                            dict_order_item[item["product"].id].quantity,
                            item["quantity"],
                            item["product"],
                            update_products_stock,
                        )
                        dict_order_item[item["product"].id].quantity = item["quantity"]
                        item_to_update.append(dict_order_item[item["product"].id])

                        del dict_order_item[item["product"].id]

                    else:
                        quantity_validation([item])
                        item_to_create.append(
                            OrderItem(
                                order=instance,
                                product=item["product"],
                                quantity=item["quantity"],
                            )
                        )

                        self.update_stock_for_create(item["product"], item["quantity"])
                        update_products_stock.append(item["product"])

                if item_to_update:
                    OrderItem.objects.bulk_update(item_to_update, ["quantity"])

                if item_to_create:
                    OrderItem.objects.bulk_create(item_to_create)

                if dict_order_item:
                    for k, v in dict_order_item.items():
                        v.product.stock += v.quantity
                        update_products_stock.append(v.product)

                    OrderItem.objects.filter(
                        id__in=[v.id for v in dict_order_item.values()]
                    ).delete()

                if update_products_stock:
                    Product.objects.bulk_update(update_products_stock, ["stock"])
            return instance
        except Exception as e:
            logger.error(f"Error updating order: {str(e)}")
            raise


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for CartItem model with bulk product optimization."""

    product = BulkProductPrimaryKeyRelatedField(
        queryset=Product.objects.all(), items_field_name="cartitems"
    )

    class Meta:
        model = CartItem
        fields = ["product", "quantity"]


class CartSerializer(serializers.ModelSerializer):
    """Serializer for Cart model with bulk operations and stock validation."""

    cartitems = CartItemSerializer(many=True)
    total_money = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "cart_id",
            "user",
            "cartitems",
            "created_at",
            "updated_at",
            "total_money",
        ]

        extra_kwargs = {
            "cart_id": {"read_only": True},
            "user": {"read_only": True},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }

    def get_total_money(self, obj):
        """Calculate total money from all cart items."""

        try:
            cart_items = obj.cartitems.all()
            res = 0

            for cart_item in cart_items:
                res += cart_item.sub_total()

            return res
        except Exception as e:
            logger.error(f"Error calculating cart total: {str(e)}")
            return 0

    def to_representation(self, instance):
        """Optimize data representation with prefetch."""
        try:
            if (
                not hasattr(instance, "_prefetched_objects_cache")
                or "cartitems" not in instance._prefetched_objects_cache
            ):
                instance = (
                    Cart.objects.filter(pk=instance.pk)
                    .prefetch_related("cartitems__product")
                    .first()
                )
            return super().to_representation(instance)
        except Exception as e:
            logger.error(f"Error in cart representation: {str(e)}")
            return super().to_representation(instance)

    def create(self, validated_data):
        """Create cart with bulk cart item creation."""

        try:
            cartitems = validated_data.pop("cartitems")
            quantity_validation(cartitems)
            instance = Cart.objects.create(**validated_data)

            cartitem_to_create = []

            for cartitem in cartitems:
                cartitem_to_create.append(
                    CartItem(
                        cart=instance,
                        product=cartitem.get("product"),
                        quantity=cartitem.get("quantity"),
                    )
                )

            CartItem.objects.bulk_create(cartitem_to_create)

            return instance
        except Exception as e:
            logger.error(f"Error creating cart: {str(e)}")
            raise

    def check_stock_for_update_cartitem(
        self, previous_quantity, new_quantity, product_obj
    ):
        """Validate stock availability when updating cart item."""
        try:
            if new_quantity == 0:
                raise serializers.ValidationError(
                    "You have to choose atleast 1 quantity"
                )
            if previous_quantity < new_quantity and new_quantity > product_obj.stock:
                raise serializers.ValidationError("You have to choose less quantity")
        except serializers.ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error checking stock for cart update: {str(e)}")
            raise

    def update(self, instance, validated_data):
        """Update cart with stock validation and bulk operations."""

        try:
            if "cartitems" in validated_data:
                cartitems = validated_data["cartitems"]
                cart_items = CartItem.objects.filter(cart=instance).select_related(
                    "product"
                )
                dict_cart_item, cartitem_to_create, cartitem_to_update = {}, [], []

                for cart_item in cart_items:
                    dict_cart_item[cart_item.product.id] = cart_item

                for cartitem in cartitems:
                    if cartitem["product"].id in dict_cart_item:
                        if (
                            dict_cart_item[cartitem["product"].id].quantity
                            != cartitem["quantity"]
                        ):
                            self.check_stock_for_update_cartitem(
                                dict_cart_item[cartitem["product"].id].quantity,
                                cartitem["quantity"],
                                cartitem["product"],
                            )
                            dict_cart_item[cartitem["product"].id].quantity = cartitem[
                                "quantity"
                            ]
                            cartitem_to_update.append(
                                dict_cart_item[cartitem["product"].id]
                            )

                        del dict_cart_item[cartitem["product"].id]
                    else:
                        quantity_validation([cartitem])
                        cartitem_to_create.append(
                            CartItem(
                                cart=instance,
                                product=cartitem["product"],
                                quantity=cartitem["quantity"],
                            )
                        )

                if dict_cart_item:
                    CartItem.objects.filter(
                        id__in=[v.id for v in dict_cart_item.values()]
                    ).delete()

                if cartitem_to_update:
                    CartItem.objects.bulk_update(cartitem_to_update, ["quantity"])

                if cartitem_to_create:
                    CartItem.objects.bulk_create(cartitem_to_create)

            instance.updated_at = timezone.now()
            instance.save(update_fields=["updated_at"])
            return instance
        except Exception as e:
            logger.error(f"Error updating cart: {str(e)}")
            raise
