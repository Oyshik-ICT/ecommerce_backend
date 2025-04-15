from .models import CustomUser, Product, Order, OrderItem
from rest_framework import serializers
from django.contrib.auth.hashers import make_password

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
    class Meta:
        model = Product
        fields = "__all__"
    
class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]
    
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    class Meta:
        model = Order
        fields = ["order_id", "user", "items", "status", "created_at"]

        extra_kwargs = {"order_id":{"read_only": True}, "user":{"read_only": True}, "created_at":{"read_only": True}}

    
    def quantity_validation(self, items):
        for item in items:
            if item['quantity'] == 0:
                raise serializers.ValidationError("You have to choose atleast 1 quantity")
            if item['product'].stock < item['quantity']:
                 raise serializers.ValidationError("You have to choose less quantity")

    def update_quantity_for_create(self, product, quantity):
        product.stock = product.stock - quantity
        product.save()

    def update_quantity_for_update(self, previous_quantity, new_quantity, product_obj):
        if new_quantity == 0:
            raise serializers.ValidationError("You have to choose atleast 1 quantity")
        if previous_quantity > new_quantity:
            product_obj.stock += (previous_quantity - new_quantity)

        else:
            if (new_quantity - previous_quantity) > product_obj.stock:
                raise serializers.ValidationError("You have to choose less quantity")
            product_obj.stock -= (new_quantity - previous_quantity)

        product_obj.save()
    
    def create(self, validated_data):
        items = validated_data.pop("items")

        self.quantity_validation(items)

        instance = Order.objects.create(**validated_data)
        
        for item in items:
            OrderItem.objects.create(
                order = instance,
                product = item.get("product"),
                quantity = item.get("quantity")
            )

            self.update_quantity_for_create(item['product'], item['quantity'])
        return instance
    
    def update(self, instance, validated_data):
        if "status" in validated_data:
            instance.status = validated_data.get("status")
            instance.save()

        if "items" in validated_data:
            items = validated_data['items']
            order_items = OrderItem.objects.filter(order=instance)
            dict_order_item = {}

            for order_item in order_items:
                dict_order_item[order_item.product] = order_item


            for item in items:
                if dict_order_item.get(item["product"], -1) != -1:
                    self.update_quantity_for_update(dict_order_item[item["product"]].quantity, item["quantity"], item["product"])
                    dict_order_item[item["product"]].quantity = item["quantity"]
                    dict_order_item[item["product"]].save()
                    
                else:
                    OrderItem.objects.create(
                        order = instance,
                        product = item["product"],
                        quantity = item["quantity"]
                    )

        return instance