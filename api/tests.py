from rest_framework.test import APITestCase
from .models import CustomUser, Product, Category
from django.urls import reverse
from rest_framework import status

class ProductAPITestCase(APITestCase):
    def setUp(self):
        # Dummy test user credentials
        self.user = CustomUser.objects.create_user(email="dada@gmail.com", password="dada")
        self.admin = CustomUser.objects.create_superuser(email="mohtasim@gmail.com", password="mohtasim")

        self.catagory = Category.objects.create(type = "Electronics")
        self.product = Product.objects.create(
            name = "Test Product",
            description = "This is a test product",
            price = "100.00",
            stock = 50,
            category = self.catagory
        )

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
            "category": 1
        }

        #for user
        self.client.login(email="dada@gmail.com", password="dada")
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        #for admin
        self.client.login(email="mohtasim@gmail.com", password="mohtasim")
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_only_admin_can_update_product(self):
        url = reverse("product-detail", args=[self.product.id])
        data = {"name": "Test Product Updated"}

        #user
        self.client.login(email="dada@gmail.com", password="dada")
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        #admin
        self.client.login(email="mohtasim@gmail.com", password="mohtasim")
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], data["name"])

    def test_only_admin_can_delete_product(self):
        url = reverse("product-detail", args=[self.product.id])
        self.client.login(email="dada@gmail.com", password="dada")

        #user
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        #admin
        self.client.login(email="mohtasim@gmail.com", password="mohtasim")
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=self.product.id).exists())