from django.shortcuts import render
from .models import CustomUser, Product, Order, Cart
from .serializers import CustomUserSerializer, ProductSerializer, OrderSerializer, CartSerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.decorators import action
from django.db import transaction
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .utils import create_payment, execute_payment
from django_filters.rest_framework import DjangoFilterBackend
from .filters import ProductFilter
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

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
    queryset = Product.objects.select_related("category").order_by("pk")
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter
    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            self.permission_classes = [AllowAny]
        else:
            self.permission_classes = [IsAdminUser]

        return super().get_permissions() 
    
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.order_by("-created_at")

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
    queryset = Cart.objects.order_by("-created_at")
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

        
class CreatePaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, order_id=order_id)

        if order.user != request.user and not request.user.is_staff:
            return Response(
                {"details": "You don't have permission to pay for this order"},
                status=status.HTTP_403_FORBIDDEN
            )

        if order.payment_status in [Order.PaymentStatusChoice.PAID, Order.PaymentStatusChoice.PAYMENT_PENDING]:
            return Response(
                {"detail": f"This order is already {order.payment_status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        protocol = 'https' if request.is_secure() else 'http'
        domain = request.get_host()
        base_url = f"{protocol}://{domain}"

        payment_data = create_payment(request, order, base_url)

        if payment_data["success"]:
            order.payment_status = Order.PaymentStatusChoice.PAYMENT_PENDING
            order.payment_id = payment_data["payment_id"]

            order.save(update_fields=["payment_status", "payment_id"])

            return Response({
                "approval_url": payment_data["approval_url"],
                "payment_id": payment_data["payment_id"]
            })
        
        return Response(
            {"detail": "Failed to create PayPal payment", "error": payment_data["error"]},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
class PaymentSuccessAPIView(APIView):

    def get(self, request):
        payment_id = request.GET.get("paymentId")
        payer_id = request.GET.get("PayerID")
        order_id = request.GET.get("order_id")

        if not all([payment_id, payer_id, order_id]):
            return Response(
                {"details": "Missing required parameters"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order = get_object_or_404(Order, order_id=order_id)
        result = execute_payment(payment_id, payer_id)

        if result["success"]:
            order.payment_status = Order.PaymentStatusChoice.PAID
            order.status = Order.StatusChoice.CONFIRMED

            order.save(update_fields=["payment_status", "status"])

            return Response({
                "detail": "Payment completed successfully",
                "order_id": order.order_id
            })
        
        return Response(
            {"detail": "Payment execution failed", "error": result["error"]},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
class PaymentCancelAPIView(APIView):

    def get(self, request):
        order_id = request.GET.get("order_id")

        if not order_id:
            return Response(
                {"details": "Missing order_id parameters"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order = get_object_or_404(Order, order_id=order_id)

        if order.payment_status == Order.PaymentStatusChoice.PAYMENT_PENDING:
            order.payment_status = Order.PaymentStatusChoice.UNPAID
            order.payment_id = None

            order.save(update_fields=["payment_status", "payment_id"])

        return Response(
            {"detail": "Payment was cancelled", "order_id": order.order_id},
        )