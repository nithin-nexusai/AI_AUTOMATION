# CHICX AI Platform - API Reference

## Backend API Endpoints

### Products

```
GET /api/get_products.php
Authorization: Bearer {CHICX_API_KEY}
```

| Param | Description |
|-------|-------------|
| `search` | Search query (optional) |
| `category` | Filter by category |
| `page` | Page number (default: 1) |
| `limit` | Results per page (default: 10) |

**Response:**
```json
{
  "status": true,
  "page": 1,
  "limit": 10,
  "total_records": 2,
  "data": [
    {
      "id": "5",
      "sku": "SKU-1001",
      "category": "Furniture",
      "title": "Luxury Blue Sofa",
      "price": "45999.00"
    }
  ]
}
```

---

### Orders by Phone

```
GET /api/get_order.php?phone=9876543210
Authorization: Bearer {CHICX_API_KEY}
```

**Response:**
```json
{
  "status": true,
  "order": {
    "id": 15,
    "order_id": "ORD123456",
    "order_status": "Delivered",
    "payment": {
      "payment_method": "Razorpay",
      "payment_status": "Paid",
      "total_amount": 2499.00
    },
    "items": [...]
  }
}
```

---

### Order Status

```
GET /api/order_status.php?order_id=ORD123456
Authorization: Bearer {CHICX_API_KEY}
```

---

### Payment Status

```
GET /api/order_payment_status.php?order_id=ORD123456
Authorization: Bearer {CHICX_API_KEY}
```

---

## Notification Webhooks (CHICX → Bot)

### Send OTP

```
POST /webhooks/chicx/send-otp
X-CHICX-Secret: {CHICX_API_KEY}
Content-Type: application/json

{
  "phone": "9876543210",
  "otp": "123456"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| phone | string | Yes | Customer phone (10 digits) |
| otp | string | Yes | 6-digit OTP |

---

### Cart Reminder

```
POST /webhooks/chicx/cart-reminder
X-CHICX-Secret: {CHICX_API_KEY}
Content-Type: application/json

{
  "phone": "9876543210",
  "customer_name": "Rahul",
  "product_name": "Premium Shirt",
  "cart_total": 1299.00,
  "checkout_url": "https://chicx.in/checkout/abc"
}
```

### New Product

```
POST /webhooks/chicx/new-product
X-CHICX-Secret: {CHICX_API_KEY}

{
  "phones": ["9876543210", "9123456789"],
  "product_name": "Luxury Sofa",
  "product_price": 45999.00,
  "product_url": "https://chicx.in/products/sofa"
}
```

### Order Update

```
POST /webhooks/chicx/order-update
X-CHICX-Secret: {CHICX_API_KEY}

{
  "phone": "9876543210",
  "order_id": "ORD123456",
  "order_status": "Shipped",
  "tracking_url": "https://shiprocket.com/track/abc"
}
```

---

## WhatsApp Templates Required

| Template | Parameters |
|----------|------------|
| `cart_reminder` | {{1}}=name, {{2}}=product, {{3}}=total |
| `new_product` | {{1}}=product_name, {{2}}=price |
| `order_update` | {{1}}=order_id, {{2}}=status |

---

## Configuration

```env
# Required
CHICX_API_BASE_URL=https://api.chicx.in
CHICX_API_KEY=your_bearer_token

# For FAQ search
OPENAI_API_KEY=sk-xxx

# For Bolna voice
BOLNA_API_KEY=xxx
BOLNA_WEBHOOK_SECRET=xxx
```
