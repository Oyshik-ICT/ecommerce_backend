from django.shortcuts import render
from .models import CustomUser, Product, Order, Cart
from .serializers import CustomUserSerializer, ProductSerializer, OrderSerializer, CartSerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from django.db import transaction

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    def get_permissions(self):
        if self.action == "Create":
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if not user.is_staff:
            qs = qs.filter(email=user)
        return qs

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    queryset = Product.objects.select_related("category")

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAdminUser]

        return super().get_permissions() 
    
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if not user.is_staff:
            qs = qs.filter(user=user).prefetch_related('items__product')
        elif self.request.method not in ['PATCH', 'DELETE']:
            qs = qs.prefetch_related('items__product')
        return qs
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser]
        else:
            self.permission_classes = [IsAuthenticated]

        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    queryset = Cart.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        if not user.is_staff:
            qs = qs.filter(user=user)

        if self.request.method not in ["DELETE", "PATCH"]:
            qs = qs.prefetch_related('cartitems__product')

        return qs
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def checkout(self, request, pk=None):
        cart = self.get_object()
        if cart.user != request.user:
            return Response(
                {"details": "You don't have permission to checkout this cart"},
                status=status.HTTP_403_FORBIDDEN
            )

        cart_items = cart.cartitems.all()

        if not cart_items.exists():
            return Response(
                {"details": "Cart is empty"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order_data = {
            "items":[
                {
                    "product": cart_item.product.id,
                    "quantity": cart_item.quantity
                }

                for cart_item in cart_items
            ]
        }

        serializer = OrderSerializer(data=order_data, context={'request': request})

        if serializer.is_valid():
            order = serializer.save(user=self.request.user)

            cart.delete()

            return Response(
                OrderSerializer(order).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

        

