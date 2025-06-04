from rest_framework.test import APITestCase
from .models import CustomUser, Product, Category, Order, OrderItem
from django.urls import reverse
from rest_framework import status

class BaseAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = CustomUser.objects.create_user(email="dada@gmail.com", password="dada")
        cls.admin = CustomUser.objects.create_superuser(email="mohtasim@gmail.com", password="mohtasim")

        cls.catagory = Category.objects.create(type = "Electronics")
        cls.product = Product.objects.create(
            name = "Test Product",
            description = "This is a test product",
            price = "100.00",
            stock = 50,
            category = cls.catagory
        )

    def login_user(self):
        self.client.login(email="dada@gmail.com", password="dada")

    def login_admin(self):
        self.client.login(email="mohtasim@gmail.com", password="mohtasim")
        

class ProductAPITestCase(BaseAPITestCase):
    def test_product_list(self):
        url = reverse("product-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]["name"], self.product.name)

    def test_only_admin_can_create_product(self):
        url = reverse("product-list")
        data = {
            "name": "Test Product 1",
            "description": "This is a test product to create",
            "price": "100.00",
            "stock": 50,
            "category": self.catagory.id
        }

        #for user
        self.login_user()
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        #for admin
        self.login_admin()
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_only_admin_can_update_product(self):
        url = reverse("product-detail", args=[self.product.id])
        data = {"name": "Test Product Updated"}

        #user
        self.login_user()
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        #admin
        self.login_admin()
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], data["name"])

    def test_only_admin_can_delete_product(self):
        url = reverse("product-detail", args=[self.product.id])

        #user
        self.login_user()
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        #admin
        self.login_admin()
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())

class OrderAPITestCase(BaseAPITestCase):
    def setUp(self):
        self.order = Order.objects.create(
            user = self.user
        )

        self.orderitem = OrderItem.objects.create(
            order = self.order,
            product = self.product,
            quantity = 3
        )

        self.product.stock -= 3
        self.product.save(update_fields=["stock"])


    def test_only_authenticated_user_can_make_order(self):
        url = reverse("order-list")
        data = {
            "items":[
                {"product": self.product.id, "quantity": 2}
            ]
        }

        #unauthenticated_user
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        #authenticated_user
        self.login_user()
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_only_admin_can_update_order(self):
        data = {
            "items":[
                {"product": self.product.id, "quantity": 4}
            ]
        }
        
        order = Order.objects.first()
        url = reverse("order-detail", args=[order.order_id])

        #authenticated_user
        self.login_user()
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        #admin
        self.login_admin()
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_only_admin_can_delete_order(self):
        order = Order.objects.first()
        url = reverse("order-detail", args=[order.order_id])

        #authenticated_user
        self.login_user()
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        #admin
        self.login_admin()
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Order.objects.filter(order_id=order.order_id).exists())


