# CHICX AI Platform — API Quick Reference

> This is the short-form reference. For detailed payloads, examples, and templates see [BACKEND_INTEGRATION_GUIDE.md](./BACKEND_INTEGRATION_GUIDE.md).

---

## 1. Notification Webhooks (CHICX Backend → Bot)

Your backend calls these to send WhatsApp messages and trigger voice calls.

**Base URL:** `https://{BOT_SERVER}/webhooks/chicx`  
**Auth header:** `X-CHICX-Secret: {CHICX_API_KEY}`  
**Content-Type:** `application/json`

| # | Endpoint | Method | Purpose |
|---|----------|--------|---------|
| 1 | `/webhooks/chicx/send-otp` | POST | Send login OTP via WhatsApp |
| 2 | `/webhooks/chicx/order-update` | POST | Order status change notification via WhatsApp |
| 3 | `/webhooks/chicx/confirm-order` | POST | Trigger outbound voice call to confirm COD order |

> [!NOTE]
> **Marketing notifications** (cart reminders, new arrivals, sales) are handled via **AiSensy** platform. See [`BACKEND_AISENSY_INTEGRATION.md`](./BACKEND_AISENSY_INTEGRATION.md).

### Quick Payloads

#### 1. Send OTP
```json
{ "phone": "9876543210", "otp": "123456" }
```

#### 2. Order Update
```json
{
  "phone": "9876543210",
  "order_id": "ORD123456",
  "order_status": "Shipped",
  "tracking_url": "https://shiprocket.com/track/abc",
  "delivery_date": "2025-12-30"
}
```

**Recommended status values:** `Order Placed`, `Order Confirmed`, `Shipped`, `Out for Delivery`, `Delivered`, `Cancelled`

#### 3. Confirm Order (Voice Call)
```json
{
  "phone": "9876543210",
  "order_id": "ORD123456",
  "customer_name": "Rahul",
  "items": [
    { "name": "Blue Saree", "qty": 1, "price": 2499 }
  ],
  "total_amount": 2499.00,
  "cod": true,
  "delivery_address": "123 Main Street, Chennai 600001"
}
```

---

## 2. Data APIs (CHICX Backend → Bot)

The bot calls these endpoints to fetch product and order data.

**Base URL:** `https://{CHICX_API_BASE_URL}`
**Auth header:** `Authorization: Bearer {CHICX_API_KEY}`

| # | Endpoint | Method | Purpose |
|---|----------|--------|---------|
| 1 | `/api/get_products.php` | GET | Search products with filters |
| 2 | `/api/get_order.php?order_id={id}` | GET | Get order details by ID |
| 3 | `/api/get_order.php?phone={phone}` | GET | Get orders by phone number |
| 4 | `/api/order_status.php?order_id={id}` | GET | Get order status (lightweight) |
| 5 | `/api/my_orders.php?user_id={id}` | GET | Get orders by user ID |

### Key Response Format Requirements

#### Products API Response
```json
{
  "status": true,
  "page": 1,
  "total_records": 45,
  "total_pages": 5,
  "data": [...]  // ⚠️ Must be "data" not "products"
}
```

#### Order API Response
```json
{
  "status": true,
  "order": {
    "order_id": "ORD123",
    "phone": "9876543210",  // ⚠️ 10 digits, no +
    "order_status": "Shipped",
    "status": "Shipped"  // ⚠️ Include both fields
  }
}
```

---

## 3. Callback API (Bot → CHICX Backend)

The bot calls this endpoint **after** a confirmation voice call completes.

> [!CRITICAL]
> Your backend **MUST implement** this endpoint to receive confirmation results.

```
POST {CHICX_API_BASE_URL}/api/confirm_order.php
Authorization: Bearer {CHICX_API_KEY}
```

**Payload the bot sends:**
```json
{
  "order_id": "ORD123456",
  "confirmed": true,
  "confirmation_method": "voice_call",
  "notes": "Customer confirmed order via voice call"
}
```

| Field | Type | Description |
|-------|------|-------------|
| order_id | string | The order ID |
| confirmed | boolean | `true` = customer confirmed, `false` = rejected/no answer |
| confirmation_method | string | Always `"voice_call"` |
| notes | string | Details (e.g., "Call not answered: missed") |

---

## 3. APIs Bot Consumes (CHICX Backend must provide)

The bot calls these to answer customer queries about products and orders.

**Base URL:** `{CHICX_API_BASE_URL}`  
**Auth:** `Authorization: Bearer {CHICX_API_KEY}`

| # | Endpoint | Method | Purpose |
|---|----------|--------|---------|
| 1 | `/api/get_products.php` | GET | Product search (params: `search`, `category`, `min_price`, `max_price`, `limit`) |
| 2 | `/api/get_products.php?search={id}` | GET | Single product details |
| 3 | `/api/get_order.php?order_id={id}` | GET | Order details by ID |
| 4 | `/api/get_order.php?phone={phone}` | GET | Order history by phone |
| 5 | `/api/confirm_order.php` | POST | Receive confirmation call result (see Section 2) |

---

## 4. Stats APIs (Bot → Dashboard)

**Base URL:** `https://{BOT_SERVER}/api/stats`  
**Auth header:** `X-API-Key: {ADMIN_API_KEY}`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/stats/overview` | GET | Key metrics (conversations, orders, calls, messages today) |
| `/api/stats/messages-per-day?days=30` | GET | Message trend (1-90 days) |
| `/api/stats/conversations` | GET | Conversation list (filter: status, search, page, limit) |
| `/api/stats/calls` | GET | Call logs (filter: status, direction, phone, language, has_recording, date range, duration range, sort) |
| `/api/stats/calls/{call_id}` | GET | Single call details + transcript |
| `/api/stats/calls/{call_id}/audio` | GET | Call recording URL |

---

## 5. API Field → Template Variable Mapping

> [!IMPORTANT]
> Each notification API maps your payload fields directly to Meta WhatsApp template variables. If a required field is missing, the API will return a validation error.

### OTP (`otp_login` template)
| Template Part | Variable | API Field | Required |
|---------------|----------|-----------|----------|
| Body | `{{1}}` | `otp` | ✅ Yes |
| Button (Copy Code) | `{{1}}` | `otp` | ✅ Yes |

### Cart Reminder (`cart_reminder` template)
| Template Part | Variable | API Field | Fallback | Required |
|---------------|----------|-----------|----------|----------|
| Body | `{{1}}` | `customer_name` | `"there"` | No |
| Body | `{{2}}` | `product_name` | — | ✅ Yes |
| Body | `{{3}}` | `cart_total` | `"your cart"` | No |
| Button (URL) | suffix | `checkout_url` | not sent | No |

### Order Update (`order_update` template)
| Template Part | Variable | API Field | Required |
|---------------|----------|-----------|----------|
| Body | `{{1}}` | `order_id` | ✅ Yes |
| Body | `{{2}}` | `order_status` | ✅ Yes |
| Button (URL) | suffix | `tracking_url` | No |

### New Product (`new_product` template)
| Template Part | Variable | API Field | Required |
|---------------|----------|-----------|----------|
| Header | Image | `image_url` (HTTPS) | ✅ Yes |
| Body | `{{1}}` | `title` | ✅ Yes |
| Body | `{{2}}` | `body` | ✅ Yes |
| Button (URL) | suffix | `product_url` | No |

### Sale Announcement (`sale_announcement` template)
| Template Part | Variable | API Field | Required |
|---------------|----------|-----------|----------|
| Header | Image | `image_url` (HTTPS) | ✅ Yes |
| Body | `{{1}}` | `title` | ✅ Yes |
| Body | `{{2}}` | `body` | ✅ Yes |
| Button (URL) | suffix | `sale_url` | No |

---

## 6. Environment Variables

### Bot Server needs from CHICX Backend
```env
CHICX_API_BASE_URL=https://api.chicx.in
CHICX_API_KEY=your_backend_bearer_token
```

### Dashboard / Backend needs from Bot Server
```env
BOT_API_BASE_URL=https://bot.chicx.in
ADMIN_API_KEY=admin_api_key_for_stats
CHICX_WEBHOOK_SECRET=webhook_secret_for_notifications
```

---

## 7. Error Response Format

All endpoints return errors as:
```json
{
  "status": "error",
  "message": "Description of what went wrong"
}
```

| HTTP Status | Meaning |
|-------------|---------|
| 401 | Invalid or missing API key |
| 400 | Invalid request payload |
| 429 | Rate limited |
| 500 | Server error |
