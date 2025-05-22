import paypalrestsdk
from django.conf import settings

paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE, 
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

def get_total_money_and_insert_orderitems_in_items(order_items, items):
    total = 0

    for item in order_items:
        total += item.sub_total()
        items.append({
            "name": item.product.name,
            "price": f"{item.product.price:.2f}",
            "currency": "USD",
            "quantity": item.quantity,
            "sku": str(item.product.id)
        })

    return f"{total:.2f}"

def create_payment_object(order, return_base_url, total, items):
    return paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": f"{return_base_url}/paypal/success/?order_id={order.order_id}",
            "cancel_url": f"{return_base_url}/paypal/cancel/?order_id={order.order_id}"
        },
        "transactions": [{
            "item_list": {
                "items": items
            },
            "amount": {
                "total": total,
                "currency": "USD"
            },
            "description": f"Payment for order {order.order_id}"
        }]
    })

def create_payment(request, order, return_base_url):
    items = []
    order_items = order.items.all().select_related('product')

    total = get_total_money_and_insert_orderitems_in_items(order_items, items)
    payment = create_payment_object(order, return_base_url, total, items)

    if payment.create():
        for link in payment.links:
            if link.rel == 'approval_url':
                approval_url = link.href
                return {
                    "success": True,
                    "payment_id": payment.id,
                    "approval_url": approval_url
                }
            
    else:
        return {
            "success": False,
            "error": payment.error
        }

def execute_payment(payment_id, payer_id):
    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        return {
            "success": True,
            "payment": payment
        }
    
    return {
        "success": False,
        "error": payment.error
    }

    