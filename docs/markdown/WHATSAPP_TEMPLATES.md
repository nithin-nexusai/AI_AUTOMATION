# WhatsApp Message Templates

This document lists all WhatsApp message templates required for the CHICX bot. These templates must be created and approved in **Meta Business Manager** before use.

> **References:**
> - [Meta WhatsApp Business Blog](https://business.whatsapp.com/blog/manage-message-templates-whatsapp-business-api)
> - [360dialog Template Documentation](https://docs.360dialog.com/docs/waba-messaging/template-messaging)
> - [Infobip Template Guide](https://www.infobip.com/docs/whatsapp/message-types-and-templates/message-templates)

---

## Template Categories & Pricing

| Category | Use Case | Approval Time | Pricing |
|----------|----------|---------------|---------|
| **Authentication** | OTP, verification codes | Fast (minutes) | Always charged per message |
| **Utility** | Order updates, receipts | Fast (hours) | Free within 24h conversation window |
| **Marketing** | Promotions, reminders | Slower (1-2 days) | Always charged per message |

**Important 2025 Update:** Starting April 1, 2025, Meta temporarily pauses delivery of marketing templates to US phone numbers.

---

## Template Structure

Every template consists of these components:

| Component | Required | Limits | Notes |
|-----------|----------|--------|-------|
| **Header** | Optional | 60 chars (text) or media | TEXT, IMAGE, VIDEO, DOCUMENT, LOCATION |
| **Body** | **Required** | 1,024 chars | Main message, supports `{{1}}` placeholders |
| **Footer** | Optional | 60 chars | Non-interactive supplementary info |
| **Buttons** | Optional | Up to 10 total | Quick reply, URL, Phone, Copy Code |

**Placeholder Format:** Use `{{1}}`, `{{2}}`, `{{3}}` for dynamic values.

---

## Media Requirements

### Image Headers

| Requirement | Value |
|-------------|-------|
| **Formats** | PNG, JPEG (JPG deprecated by Meta) |
| **Max Size** | 5 MB (some sources say 2 MB for optimal) |
| **Recommended Dimensions** | 1125 x 600 pixels |
| **Aspect Ratio** | Any works, but 1125x600 prevents need to tap to view |
| **URL** | Must be publicly accessible HTTPS |

### Other Media

| Type | Formats | Max Size |
|------|---------|----------|
| Video | MP4 (H.264 codec), 3GPP | 16 MB |
| Document | PDF only | 100 MB |
| Audio | AAC, AMR, MP3, OGG | 16 MB |

---

## Button Types

| Type | Description | Max Length | Notes |
|------|-------------|------------|-------|
| **Quick Reply** | Predefined responses | 25 chars | Up to 10 buttons |
| **URL** | Link to website | 25 chars label | Up to 2 buttons, supports dynamic `{{1}}` suffix |
| **Phone** | Call button | 25 chars | Single number, international format with `+` |
| **Copy Code** | Copy to clipboard | 15 chars | For coupons/OTP codes |

### Dynamic URL Button Format

When creating a template with dynamic URL:
```
https://chicx.in/product/{{1}}
```

When sending via API, pass the dynamic part:
```json
{
  "type": "button",
  "sub_type": "url",
  "index": "0",
  "parameters": [
    {"type": "text", "text": "gold-earrings"}
  ]
}
```

Result: `https://chicx.in/product/gold-earrings`

---

## 1. Authentication Templates (OTP)

Authentication templates have special restrictions:
- **No URLs, media, or emojis allowed**
- Preset text format enforced by Meta
- Default TTL: 10 minutes
- Copy code button disables after expiration

### 1.1 `otp_login`

**Category:** Authentication
**Channel:** PRIMARY

**Template Structure (preset by Meta):**
```
{{1}} is your verification code.

For your security, do not share this code.

This code expires in 10 minutes.

[Copy Code]
```

**Components:**
| Type | Parameter | Description |
|------|-----------|-------------|
| Body | `{{1}}` | 6-digit OTP code |
| Button | COPY_CODE | Auto-copies OTP to clipboard |

**API Payload:**
```json
{
  "type": "body",
  "parameters": [{"type": "text", "text": "123456"}]
},
{
  "type": "button",
  "sub_type": "copy_code",
  "index": "0",
  "parameters": [{"type": "text", "text": "123456"}]
}
```

---

### 1.2 `otp_password_reset`

**Category:** Authentication
**Channel:** PRIMARY

Same structure as `otp_login`. The template name differentiates the use case for analytics.

---

### 1.3 `otp_purchase`

**Category:** Authentication
**Channel:** PRIMARY

Same structure as `otp_login`. Used for purchase verification OTPs.

---

## 2. Utility Templates

### 2.1 `order_update`

**Category:** Utility
**Channel:** PRIMARY

**Template Content:**
```
Order Update

Your order #{{1}} is now *{{2}}*.

Thank you for shopping with CHICX!

[Track Order]
```

**Components:**
| Type | Parameter | Description |
|------|-----------|-------------|
| Body | `{{1}}` | Order ID (e.g., "ORD123456") |
| Body | `{{2}}` | Order status (e.g., "Shipped") |
| Button | URL (dynamic) | Tracking page link |

**Button Configuration:**
- Type: `URL`
- Button Text: "Track Order"
- URL: `https://chicx.in/track/{{1}}`

**Status Values:**
- `Order Confirmed`
- `Processing`
- `Shipped`
- `Out for Delivery`
- `Delivered`
- `Cancelled`
- `Refund Initiated`
- `Refund Completed`

---

## 3. Marketing Templates

### 3.1 `new_product`

**Category:** Marketing
**Channel:** MARKETING

**Template Structure:**
```
[IMAGE HEADER - Product Poster]

New Arrival at CHICX!

*{{1}}* is now available at just {{2}}!

Shop now before it's gone.

[Shop Now]
```

**Components:**
| Type | Parameter | Description |
|------|-----------|-------------|
| Header | IMAGE | Product poster (dynamic URL, 1125x600px recommended) |
| Body | `{{1}}` | Product name |
| Body | `{{2}}` | Price (e.g., "₹1,299") |
| Button | URL (dynamic) | Product page link |

**Button Configuration:**
- Type: `URL`
- Button Text: "Shop Now"
- URL: `https://chicx.in/product/{{1}}`

---

### 3.2 `sale_announcement`

**Category:** Marketing
**Channel:** MARKETING

**Template Structure:**
```
[IMAGE HEADER - Sale Poster]

{{1}}

Get *{{2}}* on all products!

Hurry, offer valid till {{3}}.

[Shop Now]
```

**Components:**
| Type | Parameter | Description |
|------|-----------|-------------|
| Header | IMAGE | Sale poster (dynamic URL) |
| Body | `{{1}}` | Sale title (e.g., "Diwali Sale") |
| Body | `{{2}}` | Discount text (e.g., "Up to 50% OFF") |
| Body | `{{3}}` | Validity (e.g., "31st December") |
| Button | URL (dynamic) | Sale page link |

---

### 3.3 `cart_reminder`

**Category:** Marketing
**Channel:** MARKETING

**Template Content:**
```
Hi {{1}}!

You left *{{2}}* worth {{3}} in your cart.

Complete your purchase now before it sells out!

[Complete Order]
```

**Components:**
| Type | Parameter | Description |
|------|-----------|-------------|
| Body | `{{1}}` | Customer name (or "there") |
| Body | `{{2}}` | Product name |
| Body | `{{3}}` | Cart total (e.g., "₹2,499") |
| Button | URL (dynamic) | Checkout URL |

---

## API Endpoints & Payloads

### Send OTP

```bash
curl -X POST https://your-server.com/webhooks/chicx/send-otp \
  -H "Content-Type: application/json" \
  -H "X-CHICX-Secret: your_api_key" \
  -d '{
    "phone": "9876543210",
    "otp": "123456",
    "type": "login"
  }'
```

**OTP Types:**
| Type | Template Used |
|------|---------------|
| `login` | `otp_login` |
| `forgot_password` | `otp_password_reset` |
| `purchase_verification` | `otp_purchase` |

---

### Send New Product (with Poster)

```bash
curl -X POST https://your-server.com/webhooks/chicx/new-product \
  -H "Content-Type: application/json" \
  -H "X-CHICX-Secret: your_api_key" \
  -d '{
    "phones": ["9876543210", "9876543211"],
    "product_name": "Designer Gold Earrings",
    "product_price": 1299.00,
    "image_url": "https://cdn.chicx.in/posters/gold-earrings.png",
    "product_url": "https://chicx.in/product/designer-gold-earrings"
  }'
```

---

### Send Sale Announcement (with Poster)

```bash
curl -X POST https://your-server.com/webhooks/chicx/sale-announcement \
  -H "Content-Type: application/json" \
  -H "X-CHICX-Secret: your_api_key" \
  -d '{
    "phones": ["9876543210", "9876543211"],
    "sale_title": "Diwali Mega Sale",
    "discount_text": "Up to 50% OFF",
    "image_url": "https://cdn.chicx.in/posters/diwali-sale.png",
    "sale_url": "https://chicx.in/sale/diwali",
    "valid_till": "31st October"
  }'
```

---

### Send Cart Reminder

```bash
curl -X POST https://your-server.com/webhooks/chicx/cart-reminder \
  -H "Content-Type: application/json" \
  -H "X-CHICX-Secret: your_api_key" \
  -d '{
    "phone": "9876543210",
    "customer_name": "Priya",
    "product_name": "Blue Silk Saree",
    "cart_total": 2499.00,
    "checkout_url": "https://chicx.in/checkout/abc123"
  }'
```

---

### Send Order Update

```bash
curl -X POST https://your-server.com/webhooks/chicx/order-update \
  -H "Content-Type: application/json" \
  -H "X-CHICX-Secret: your_api_key" \
  -d '{
    "phone": "9876543210",
    "order_id": "ORD123456",
    "order_status": "Shipped",
    "tracking_url": "https://chicx.in/track/ORD123456"
  }'
```

---

## Creating Templates in Meta Business Manager

### Step-by-Step Guide

1. **Go to Meta Business Suite**
   - Navigate to: https://business.facebook.com/
   - Select your WhatsApp Business Account

2. **Access Message Templates**
   - Go to: WhatsApp Manager → Account Tools → Message Templates
   - Click "Create Template"

3. **Configure Template**
   - **Name:** Use exact names (e.g., `new_product`, `otp_login`)
   - **Category:** Select Authentication/Utility/Marketing
   - **Language:** English (en)

4. **Add Components**
   - **Header:** Select "Image" for marketing templates with posters
   - **Body:** Enter template text with `{{1}}`, `{{2}}` placeholders
   - **Footer:** Optional additional text
   - **Buttons:** Add as specified

5. **Provide Sample Values**
   - All placeholders require sample values during creation
   - Omitting any causes rejection

6. **Submit for Approval**
   - Review all details
   - Click "Submit"
   - Authentication: Minutes, Utility: Hours, Marketing: 1-2 days

### Authentication Template Setup

1. Select **Authentication** category
2. Meta provides preset text format
3. Add **Copy Code** button (auto-configured)
4. Optional: Set expiration time (1-90 minutes, default 10)

### Marketing Template with Image

1. Select **Marketing** category
2. Add **Header** → Choose **Image**
3. Upload sample image (for approval only)
4. Add body with placeholders
5. Add URL button with dynamic suffix

---

## Template Summary

| Template | Category | Header | Body Params | Button |
|----------|----------|--------|-------------|--------|
| `otp_login` | Authentication | None | `{{1}}`=OTP | Copy Code |
| `otp_password_reset` | Authentication | None | `{{1}}`=OTP | Copy Code |
| `otp_purchase` | Authentication | None | `{{1}}`=OTP | Copy Code |
| `order_update` | Utility | None | `{{1}}`=OrderID, `{{2}}`=Status | URL: Track Order |
| `new_product` | Marketing | **IMAGE** | `{{1}}`=Product, `{{2}}`=Price | URL: Shop Now |
| `sale_announcement` | Marketing | **IMAGE** | `{{1}}`=Title, `{{2}}`=Discount, `{{3}}`=Validity | URL: Shop Now |
| `cart_reminder` | Marketing | None | `{{1}}`=Name, `{{2}}`=Product, `{{3}}`=Total | URL: Complete Order |

---

## Channel Configuration

| Channel | Purpose | Templates |
|---------|---------|-----------|
| **PRIMARY** | Chatbot, OTP, Order Updates | `otp_*`, `order_update` |
| **MARKETING** | Promotions, Reminders | `new_product`, `sale_announcement`, `cart_reminder` |

```env
# Primary (Transactional)
WHATSAPP_PHONE_NUMBER_ID=your_primary_phone_id
WHATSAPP_ACCESS_TOKEN=your_primary_token

# Marketing (Optional - falls back to Primary)
WHATSAPP_MARKETING_PHONE_NUMBER_ID=your_marketing_phone_id
WHATSAPP_MARKETING_ACCESS_TOKEN=your_marketing_token
```

---

## Limits & Restrictions

| Limit | Value |
|-------|-------|
| Templates per unverified business | 250 |
| Templates per verified business | 6,000 |
| Body text | 1,024 characters |
| Header text | 60 characters |
| Footer text | 60 characters |
| Button label | 25 characters |
| Copy code value | 15 characters |
| Quick reply buttons | Up to 10 |
| URL buttons | Up to 2 |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Template not found` | Name mismatch | Verify exact template name in Meta |
| `Invalid parameters` | Wrong param count | Check placeholder count matches template |
| `Template not approved` | Pending review | Wait for Meta approval |
| `Invalid image URL` | Image not accessible | Ensure URL is public HTTPS, PNG/JPEG only |
| `Button requires parameter` | Missing dynamic URL | Pass parameter for dynamic URL buttons |
| `Rate limited` | Too many messages | Implement rate limiting |
| `Template paused` | Low engagement | Review content, improve relevance |

### Common Rejection Reasons

- Missing sample values for placeholders
- Requesting confidential info (full card numbers, SSN)
- Threatening or abusive content
- Violating WhatsApp Business Policy

---

## Testing Templates

```bash
curl -X POST "https://graph.facebook.com/v18.0/YOUR_PHONE_ID/messages" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "919876543210",
    "type": "template",
    "template": {
      "name": "new_product",
      "language": {"code": "en"},
      "components": [
        {
          "type": "header",
          "parameters": [
            {"type": "image", "image": {"link": "https://cdn.chicx.in/poster.png"}}
          ]
        },
        {
          "type": "body",
          "parameters": [
            {"type": "text", "text": "Gold Earrings"},
            {"type": "text", "text": "₹1,299"}
          ]
        },
        {
          "type": "button",
          "sub_type": "url",
          "index": "0",
          "parameters": [
            {"type": "text", "text": "gold-earrings"}
          ]
        }
      ]
    }
  }'
```

---

## References

- [Meta WhatsApp Business Blog - Manage Templates](https://business.whatsapp.com/blog/manage-message-templates-whatsapp-business-api)
- [360dialog - Authentication Templates](https://docs.360dialog.com/docs/waba-messaging/template-messaging/authentication-templates)
- [360dialog - Copy Code Templates](https://docs.360dialog.com/docs/waba-messaging/template-messaging/authentication-templates/copy-code-authentication-templates)
- [Infobip - Message Templates](https://www.infobip.com/docs/whatsapp/message-types-and-templates/message-templates)
- [Netcore - WhatsApp Media Sizing Guide](https://cedocs.netcorecloud.com/docs/what-is-the-right-image-size-for-a-whatsapp-template-message)
- [BotSailor - Dynamic URLs Guide](https://botsailor.com/blog/use-dynamic-url-in-calltoaction-button-in-a-message-template)
