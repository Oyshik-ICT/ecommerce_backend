# E-commerce API

A comprehensive Django REST Framework-based e-commerce API with user authentication, product management, shopping cart functionality, order processing, and PayPal payment integration.

## Features

- **User Management**: Custom user authentication with email-based login
- **Product Catalog**: Complete product management with categories and filtering
- **Shopping Cart**: Add, update, and manage cart items
- **Order Processing**: Convert carts to orders with stock management
- **PayPal Integration**: Secure payment processing with PayPal
- **Admin Interface**: Django admin for backend management
- **API Documentation**: Interactive Swagger/OpenAPI documentation
- **Performance Monitoring**: Silk profiler integration for development

## Tech Stack

- **Backend**: Django 5.1, Django REST Framework
- **Database**: MySQL
- **Authentication**: JWT (Simple JWT)
- **Payment**: PayPal REST SDK
- **Documentation**: drf-spectacular (OpenAPI 3.0)
- **Filtering**: django-filter
- **Performance**: django-silk (development)

## Quick Start

### Prerequisites

- Python 3.8+
- MySQL 5.7+
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Oyshik-ICT/ecommerce_backend.git
   cd ecommerce_backend
   ```

2. **Create and activate virtual environment**
   ```bash
   python3 -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   DATABASE_NAME=your_database_name
   DATABASE_USER=your_mysql_username
   DATABASE_PASS=your_mysql_password
   HOST=localhost
   PORT=3306
   PAYPAL_MODE=sandbox
   PAYPAL_CLIENT_ID=your_paypal_client_id
   PAYPAL_CLIENT_SECRET=your_paypal_client_secret
   ```

5. **Set up MySQL database**
   ```sql
   CREATE DATABASE your_database_name;
   ```

6. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

8. **Start the development server**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/`

## API Documentation

### Interactive Documentation

- **Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
- **ReDoc**: `http://localhost:8000/api/schema/redoc/`
- **OpenAPI Schema**: `http://localhost:8000/api/schema/`

### Authentication

The API uses JWT (JSON Web Tokens) for authentication.

#### Get Access Token
```http
POST /api/token/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "your_password"
}
```

#### Refresh Token
```http
POST /api/token/refresh/
Content-Type: application/json

{
    "refresh": "your_refresh_token"
}
```

#### Using Token in Requests
```http
Authorization: Bearer your_access_token
```

## API Endpoints

### Users (`/users/`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| POST | `/users/` | Register new user | Public |
| GET | `/users/` | List users | Authenticated |
| GET | `/users/{id}/` | Get user details | Authenticated |
| PUT/PATCH | `/users/{id}/` | Update user | Authenticated |
| DELETE | `/users/{id}/` | Delete user | Authenticated |

**Example: Register User**
```http
POST /users/
Content-Type: application/json

{
    "email": "newuser@example.com",
    "password": "securepassword123"
}
```

### Products (`/products/`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/products/` | List all products | Public |
| GET | `/products/{id}/` | Get product details | Public |
| POST | `/products/` | Create product | Admin |
| PUT/PATCH | `/products/{id}/` | Update product | Admin |
| DELETE | `/products/{id}/` | Delete product | Admin |

**Available Filters:**
- `name`: exact match or contains
- `price`: exact, less than, greater than, range
- `category`: exact match

**Example: Get Products with Filters**
```http
GET /products/?name__contains=laptop&price__lt=1000&category=1
```

**Create Product Example:**
```http
POST /products/
Authorization: Bearer your_admin_token
Content-Type: application/json

{
    "name": "Laptop",
    "description": "High-performance laptop",
    "price": "999.99",
    "stock": 50,
    "category": 1
}
```

### Shopping Cart (`/carts/`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/carts/` | List user's carts | Authenticated |
| POST | `/carts/` | Create new cart | Authenticated |
| GET | `/carts/{id}/` | Get cart details | Authenticated |
| PUT/PATCH | `/carts/{id}/` | Update cart | Authenticated |
| DELETE | `/carts/{id}/` | Delete cart | Authenticated |
| POST | `/carts/{id}/checkout/` | Convert cart to order | Authenticated |

**Create Cart Example:**
```http
POST /carts/
Authorization: Bearer your_token
Content-Type: application/json

{
    "cartitems": [
        {
            "product": 1,
            "quantity": 2
        },
        {
            "product": 3,
            "quantity": 1
        }
    ]
}
```

**Cart Response:**
```json
{
    "cart_id": "uuid-here",
    "user": 1,
    "cartitems": [
        {
            "product": 1,
            "quantity": 2
        }
    ],
    "total_money": "99.98",
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z"
}
```

### Orders (`/orders/`)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| GET | `/orders/` | List orders | Authenticated |
| POST | `/orders/` | Create order | Authenticated |
| GET | `/orders/{id}/` | Get order details | Authenticated |
| PUT/PATCH | `/orders/{id}/` | Update order | Admin |
| DELETE | `/orders/{id}/` | Delete order | Admin |

**Create Order Example:**
```http
POST /orders/
Authorization: Bearer your_token
Content-Type: application/json

{
    "items": [
        {
            "product": 1,
            "quantity": 2
        },
        {
            "product": 3,
            "quantity": 1
        }
    ]
}
```

**Order Response:**
```json
{
    "order_id": "uuid-here",
    "user": 1,
    "items": [
        {
            "product": 1,
            "quantity": 2
        }
    ],
    "status": "Pending",
    "payment_status": "Unpaid",
    "total_money": "99.98",
    "created_at": "2024-01-01T10:00:00Z"
}
```

## PayPal Integration

The API integrates with PayPal for secure payment processing using the PayPal REST API.

### Payment Flow

1. **Create Order**: User creates an order through the API
2. **Initiate Payment**: User initiates payment for the order
3. **PayPal Redirect**: User is redirected to PayPal for authentication
4. **Payment Execution**: After approval, payment is executed automatically
5. **Order Confirmation**: Order status is updated to "Confirmed"

### Payment Endpoints

#### Initiate Payment
```http
POST /pay/{order_id}/
Authorization: Bearer your_token
```

**Response:**
```json
{
    "approval_url": "https://www.sandbox.paypal.com/checkoutnow?token=...",
    "payment_id": "PAYID-..."
}
```

#### Payment Success Callback
```http
GET /paypal/success/?paymentId=PAYID-...&PayerID=...&order_id=uuid
```

#### Payment Cancel Callback
```http
GET /paypal/cancel/?order_id=uuid
```

### PayPal Setup

1. **Create PayPal Developer Account**
   - Go to [PayPal Developer](https://developer.paypal.com/)
   - Create a new application
   - Get Client ID and Client Secret

2. **Configure Environment Variables**
   ```env
   PAYPAL_MODE=sandbox  # Use 'live' for production
   PAYPAL_CLIENT_ID=your_client_id
   PAYPAL_CLIENT_SECRET=your_client_secret
   ```

3. **Test Payment Flow**
   - Use PayPal sandbox accounts for testing
   - Buyer account: `buyer@example.com`
   - Use sandbox credit card numbers for testing

### Payment Statuses

- **Unpaid**: Initial status when order is created
- **Payment Pending**: Payment initiated, waiting for PayPal approval
- **Paid**: Payment completed successfully

### Order Statuses

- **Pending**: Order created, payment not completed
- **Confirmed**: Payment completed, order confirmed
- **Cancelled**: Order cancelled

## Data Models

### CustomUser
- Custom user model using email as username
- Extends Django's AbstractUser
- Email-based authentication

### Category
- Product categories (Electronics, Clothing, etc.)
- Extensible for additional categories

### Product
- Product information with name, description, price
- Stock management
- Category relationship
- Image upload support

### Cart & CartItem
- Shopping cart functionality
- Multiple items per cart
- Quantity management with stock validation

### Order & OrderItem
- Order processing with automatic stock deduction
- Payment integration
- Order status tracking

## Stock Management

The API automatically manages product stock:

- **Adding to Cart**: Validates stock availability
- **Creating Order**: Reduces stock quantity
- **Updating Order**: Adjusts stock based on quantity changes
- **Cancelling Order**: Restores stock quantity

## Error Handling

The API provides detailed error responses:

```json
{
    "detail": "Error message",
    "field_errors": {
        "quantity": ["You have to choose less quantity"]
    }
}
```

Common HTTP status codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request (validation errors)
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `500`: Internal Server Error

## Development Tools

### Django Admin
Access the admin interface at `http://localhost:8000/admin/` using your superuser credentials.

### Silk Profiler (Development Only)
Monitor API performance at `http://localhost:8000/silk/`

### API Testing
Use tools like:
- **Postman**: Import the OpenAPI schema
- **curl**: Command-line testing
- **HTTPie**: User-friendly HTTP client

