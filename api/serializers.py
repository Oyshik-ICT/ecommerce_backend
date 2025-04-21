from .models import CustomUser, Product, Order, OrderItem, Category
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.db import connection

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["email", "password"]

        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        if "password" in validated_data:
            validated_data["password"] = make_password(validated_data["password"])

        return super().update(instance, validated_data)
    
    
class ProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset = Category.objects.all(),
    )

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'stock', 'category']

    def update(self, instance, validated_data):
        update_fields = []

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            update_fields.append(attr)

        instance.save(update_fields=update_fields)

        return instance
    
class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]
    
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total_money = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["order_id", "user", "items", "status", "created_at", "total_money"]

        extra_kwargs = {"order_id":{"read_only": True}, "user":{"read_only": True}, "created_at":{"read_only": True}}

    def get_total_money(self, obj):
        order_items = obj.items.all()
        
        res = 0
        for order_item in order_items:
            res += order_item.sub_total()

        return res


    
    def quantity_validation(self, items):
        for item in items:
            if item['quantity'] == 0:
                raise serializers.ValidationError("You have to choose atleast 1 quantity")
            if item['product'].stock < item['quantity']:
                 raise serializers.ValidationError("You have to choose less quantity")

    def update_quantity_for_create(self, product, quantity):
        product.stock = product.stock - quantity
        # product.save(update_fields=['stock'])

    def update_quantity_for_update(self, previous_quantity, new_quantity, product_obj, product_quantity_update):
        if new_quantity == 0:
            raise serializers.ValidationError("You have to choose atleast 1 quantity")
        if previous_quantity > new_quantity:
            product_obj.stock += (previous_quantity - new_quantity)
            product_quantity_update.append(product_obj)

        else:
            if (new_quantity - previous_quantity) > product_obj.stock:
                raise serializers.ValidationError("You have to choose less quantity")
            product_obj.stock -= (new_quantity - previous_quantity)
            product_quantity_update.append(product_obj)


    
    def create(self, validated_data):
        items = validated_data.pop("items")
        
        self.quantity_validation(items)

        instance = Order.objects.create(**validated_data)

        update_products_stock, item_to_create = [], []
        
        for item in items:
            item_to_create.append(
                OrderItem(
                order = instance,
                product = item.get("product"),
                quantity = item.get("quantity")
                )
            )

            self.update_quantity_for_create(item['product'], item['quantity'])
            update_products_stock.append(item['product'])

        Product.objects.bulk_update(update_products_stock, ['stock'])
        OrderItem.objects.bulk_create(item_to_create)

        return instance
    
    def to_representation(self, instance):
            if not hasattr(instance, '_prefetched_objects_cache') or 'items' not in instance._prefetched_objects_cache:
                instance = Order.objects.filter(pk=instance.pk).prefetch_related('items__product').first()
            return super().to_representation(instance)
    
    def update(self, instance, validated_data):
        if "status" in validated_data:
            instance.status = validated_data.get("status")
            instance.save(update_fields=['status'])

        if "items" in validated_data:
            items = validated_data['items']
            order_items = OrderItem.objects.filter(order=instance).select_related("product")
            dict_order_item, item_to_create, item_to_update, product_quantity_update = {}, [], [], []

            for order_item in order_items:
                dict_order_item[order_item.product.id] = order_item

            for item in items:
                if item["product"].id in dict_order_item:
                    self.update_quantity_for_update(dict_order_item[item["product"].id].quantity, item["quantity"], item["product"], product_quantity_update)
                    dict_order_item[item["product"].id].quantity = item["quantity"]
                    item_to_update.append(dict_order_item[item["product"].id])
                    
                else:
                    item_to_create.append(
                        OrderItem(
                        order = instance,
                        product = item["product"],
                        quantity = item["quantity"]
                    )
                    )

            if product_quantity_update:
                Product.objects.bulk_update(product_quantity_update, ["stock"])
            if item_to_update:
                OrderItem.objects.bulk_update(item_to_update, ["quantity"])

            if item_to_create:
                OrderItem.objects.bulk_create(item_to_create)

        return instance