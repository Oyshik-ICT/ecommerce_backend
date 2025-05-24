import logging

import paypalrestsdk
from django.conf import settings

logger = logging.getLogger(__name__)

paypalrestsdk.configure(
    {
        "mode": settings.PAYPAL_MODE,
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET,
    }
)


def get_total_money_and_insert_orderitems_in_items(order_items, items):
    """Calculate total amount and format order items for PayPal."""
    try:
        total = 0

        for item in order_items:
            total += item.sub_total()
            items.append(
                {
                    "name": item.product.name,
                    "price": f"{item.product.price:.2f}",
                    "currency": "USD",
                    "quantity": item.quantity,
                    "sku": str(item.product.id),
                }
            )

        return f"{total:.2f}"
    except Exception as e:
        logger.error(f"Error calculating total and formatting items: {str(e)}")
        raise


def create_payment_object(order, return_base_url, total, items):
    """Create PayPal payment object with order details."""

    try:
        return paypalrestsdk.Payment(
            {
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "redirect_urls": {
                    "return_url": f"{return_base_url}/paypal/success/?order_id={order.order_id}",
                    "cancel_url": f"{return_base_url}/paypal/cancel/?order_id={order.order_id}",
                },
                "transactions": [
                    {
                        "item_list": {"items": items},
                        "amount": {"total": total, "currency": "USD"},
                        "description": f"Payment for order {order.order_id}",
                    }
                ],
            }
        )
    except Exception as e:
        logger.error(f"Error creating payment object: {str(e)}")
        raise


def create_payment(request, order, return_base_url):
    """Create PayPal payment and return approval URL."""

    try:
        items = []
        order_items = order.items.all().select_related("product")

        total = get_total_money_and_insert_orderitems_in_items(order_items, items)
        payment = create_payment_object(order, return_base_url, total, items)

        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = link.href
                    return {
                        "success": True,
                        "payment_id": payment.id,
                        "approval_url": approval_url,
                    }

        else:
            logger.error(f"PayPal payment creation failed: {payment.error}")
            return {"success": False, "error": payment.error}
    except Exception as e:
        logger.error(f"Error in create_payment: {str(e)}")
        return {"success": False, "error": str(e)}


def execute_payment(payment_id, payer_id):
    """Execute PayPal payment after user approval."""

    try:
        payment = paypalrestsdk.Payment.find(payment_id)

        if payment.execute({"payer_id": payer_id}):
            return {"success": True, "payment": payment}
        else:
            logger.error(f"PayPal payment execution failed: {payment.error}")
            return {"success": False, "error": payment.error}

    except Exception as e:
        logger.error(f"Error in execute_payment: {str(e)}")
        return {"success": False, "error": str(e)}
