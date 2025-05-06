from rest_framework import serializers

def quantity_validation(items):
    for item in items:
        if item['quantity'] == 0:
            raise serializers.ValidationError("You have to choose atleast 1 quantity")
        if item['product'].stock < item['quantity']:
                raise serializers.ValidationError("You have to choose less quantity")