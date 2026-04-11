# AiSensy Complete Guide

## Overview

AiSensy handles ALL marketing for CHICX (abandoned cart, campaigns, broadcasts). The chicx-bot focuses only on customer support conversations.

**Architecture:**
- **chicx-bot**: Support conversations, FAQ, order inquiries (1 WhatsApp number)
- **AiSensy**: All marketing campaigns and broadcasts (separate WhatsApp number)

---

## Table of Contents

1. [Dashboard Usage](#dashboard-usage)
2. [Backend Integration](#backend-integration)
3. [Segments & Automation](#segments--automation)

---

## Dashboard Usage

### Accessing AiSensy Dashboard

**URL:** https://app.aisensy.com

**Login:**
1. Enter your registered email/phone
2. Enter password or use OTP
3. Select your workspace (if multiple)

### Dashboard Overview

**Main Sections:**
- **Dashboard** - Analytics and overview
- **Contacts** - Manage customer database
- **Campaigns** - Create and manage campaigns
- **Templates** - WhatsApp message templates
- **Automation** - Workflow automation
- **Analytics** - Performance metrics
- **Settings** - Account and integration settings

---

### Managing Contacts

#### Import Contacts

**Via CSV:**
1. Go to **Contacts → Import**
2. Download sample CSV template
3. Fill in: Name, Phone (with country code), Custom attributes
4. Upload CSV file
5. Map columns to fields
6. Click **Import**

**Via API:**
```python
import httpx

async def add_contact_to_aisensy(phone: str, name: str, tags: list[str] = None):
    """Add contact to AiSensy."""
    payload = {
        "apiKey": "your_api_key",
        "campaignName": "your_campaign",
        "destination": phone,  # e.g., "919876543210"
        "userName": name,
        "tags": tags or [],
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://backend.aisensy.com/campaign/t1/api/v2/contacts/add",
            json=payload
        )
        return response.json()
```

#### Segments

**Create Segment:**
1. Go to **Contacts → Segments**
2. Click **Create Segment**
3. Set conditions:
   - Has tag: "abandoned_cart"
   - Last activity: "Last 24 hours"
   - Custom attribute: cart_value > 1000
4. Name segment: "High Value Abandoned Cart"
5. Save

**Use Cases:**
- Abandoned Cart - Last 24h
- VIP Customers (order_count > 5)
- New Customers (created_at < 7 days)
- Inactive Users (last_activity > 30 days)

---

### Creating Templates

#### Template Types

**Marketing Templates:**
- Abandoned cart reminders
- New product announcements
- Sales and promotions
- Seasonal offers

**Utility Templates:**
- Order confirmations
- Shipping updates
- OTP/verification codes

#### Create Template

1. Go to **Templates → Create Template**
2. Select **Category**:
   - Marketing (for campaigns)
   - Utility (for transactional)
3. **Template Name**: `abandoned_cart_reminder`
4. **Language**: English
5. **Header** (optional):
   - Text, Image, Video, or Document
6. **Body**:
   ```
   Hi {{1}}, you left {{2}} in your cart worth {{3}}!
   
   Complete your order now and get FREE shipping.
   ```
7. **Footer** (optional): "Reply STOP to unsubscribe"
8. **Buttons** (optional):
   - Call to Action: "Complete Order" → URL
   - Quick Reply: "Need Help?"
9. **Submit for Approval**

**Approval Time:** 24-48 hours

---

### Creating Campaigns

#### Broadcast Campaign

1. Go to **Campaigns → Create Campaign**
2. **Campaign Type**: Broadcast
3. **Name**: "Diwali Sale 2024"
4. **Select Template**: Choose approved template
5. **Select Audience**:
   - All contacts
   - Specific segment
   - Upload CSV
6. **Schedule**:
   - Send now
   - Schedule for later
7. **Preview** and **Send**

#### Automated Campaign

1. Go to **Campaigns → Create Campaign**
2. **Campaign Type**: Automated
3. **Trigger**: When contact enters segment
4. **Select Segment**: "Abandoned Cart - 24h"
5. **Select Template**: `abandoned_cart_reminder`
6. **Delay**: 1 hour after entering segment
7. **Frequency**: Once per contact
8. **Activate**

---

### Analytics

**Campaign Performance:**
- **Sent**: Total messages sent
- **Delivered**: Successfully delivered
- **Read**: Messages read by recipients
- **Replied**: Responses received
- **Clicked**: Button/link clicks
- **Conversion**: Orders placed (if tracked)

**Best Practices:**
- Send between 10 AM - 8 PM
- Avoid weekends for business messages
- Test with small segment first
- A/B test different templates

---

## Backend Integration

### How AiSensy Knows About Events

**AiSensy CANNOT automatically detect cart abandonment** - you must push events from your CHICX backend.

### Integration Flow

```
Customer abandons cart
    ↓
CHICX Backend detects it
    ↓
Backend calls AiSensy API to tag user
    ↓
AiSensy creates segment automatically
    ↓
Automated campaign triggers
```

### Implementation

#### 1. Add AiSensy Client to CHICX Backend

```python
# In your CHICX e-commerce backend
import httpx

class AiSensyClient:
    def __init__(self, api_key: str, campaign_name: str):
        self.api_key = api_key
        self.campaign_name = campaign_name
        self.base_url = "https://backend.aisensy.com/campaign/t1/api/v2"
    
    async def tag_contact(
        self,
        phone: str,
        tags: list[str],
        attributes: dict = None
    ):
        """Tag a contact for segmentation."""
        payload = {
            "apiKey": self.api_key,
            "campaignName": self.campaign_name,
            "destination": phone,
            "tags": tags,
        }
        
        if attributes:
            payload["attributes"] = attributes
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/contacts/tag",
                json=payload
            )
            return response.json()
```

#### 2. Detect Cart Abandonment

```python
# In your CHICX backend
async def on_cart_abandoned(user_id: int, cart_data: dict):
    """Called when user abandons cart (30+ min inactive)."""
    
    # Get user details
    user = get_user_by_id(user_id)
    phone = user['phone']
    
    # Calculate cart value
    cart_value = sum(item['price'] * item['quantity'] for item in cart_data['items'])
    
    # Tag in AiSensy
    aisensy = AiSensyClient(api_key="your_key", campaign_name="your_campaign")
    await aisensy.tag_contact(
        phone=phone,
        tags=["abandoned_cart"],
        attributes={
            "cart_value": str(cart_value),
            "cart_items": len(cart_data['items']),
            "abandoned_at": datetime.now().isoformat(),
        }
    )
```

#### 3. Schedule Detection Job

```python
# Cron job: Run every 30 minutes
async def detect_abandoned_carts():
    """Find carts abandoned for 30+ minutes."""
    
    # Query your database
    abandoned_carts = db.query("""
        SELECT user_id, cart_data, updated_at
        FROM carts
        WHERE status = 'active'
        AND updated_at < NOW() - INTERVAL '30 minutes'
        AND abandoned_at IS NULL
    """)
    
    aisensy = AiSensyClient(api_key="your_key", campaign_name="your_campaign")
    
    for cart in abandoned_carts:
        user = get_user_by_id(cart['user_id'])
        cart_value = calculate_cart_value(cart['cart_data'])
        
        # Tag in AiSensy
        await aisensy.tag_contact(
            phone=user['phone'],
            tags=["abandoned_cart"],
            attributes={
                "cart_value": str(cart_value),
                "cart_items": len(cart['cart_data']['items']),
            }
        )
        
        # Mark as abandoned in your DB
        db.execute("""
            UPDATE carts
            SET abandoned_at = NOW()
            WHERE user_id = ?
        """, cart['user_id'])
```

---

## Segments & Automation

### Create Abandoned Cart Segment

1. **Dashboard → Contacts → Segments**
2. **Create Segment**: "Abandoned Cart - Recent"
3. **Conditions**:
   - Has tag: "abandoned_cart"
   - Tag added: "Last 24 hours"
   - cart_value > 500 (optional)
4. **Save**

### Create Automated Campaign

1. **Dashboard → Campaigns → Create**
2. **Type**: Automated
3. **Trigger**: "When contact enters segment"
4. **Segment**: "Abandoned Cart - Recent"
5. **Template**: Your abandoned cart template
6. **Delay**: 1 hour after entering segment
7. **Frequency**: Once per contact per 7 days
8. **Activate**

### Other Use Cases

#### New Customer Welcome

```python
# When new user registers
await aisensy.tag_contact(
    phone=user['phone'],
    tags=["new_customer"],
    attributes={
        "signup_date": datetime.now().isoformat(),
        "source": "website",
    }
)
```

**Segment**: Has tag "new_customer" + signup_date < 7 days  
**Campaign**: Welcome message with discount code

#### VIP Customers

```python
# When customer places 5th order
if user['order_count'] >= 5:
    await aisensy.tag_contact(
        phone=user['phone'],
        tags=["vip_customer"],
        attributes={
            "total_orders": user['order_count'],
            "lifetime_value": user['total_spent'],
        }
    )
```

**Segment**: Has tag "vip_customer"  
**Campaign**: Exclusive VIP offers

---

## API Reference

### Base URL
```
https://backend.aisensy.com/campaign/t1/api/v2
```

### Add/Update Contact

**Endpoint:** `POST /contacts/add`

**Payload:**
```json
{
  "apiKey": "your_api_key",
  "campaignName": "your_campaign",
  "destination": "919876543210",
  "userName": "John Doe",
  "tags": ["customer", "vip"],
  "attributes": {
    "email": "john@example.com",
    "city": "Mumbai"
  }
}
```

### Tag Contact

**Endpoint:** `POST /contacts/tag`

**Payload:**
```json
{
  "apiKey": "your_api_key",
  "campaignName": "your_campaign",
  "destination": "919876543210",
  "tags": ["abandoned_cart"],
  "attributes": {
    "cart_value": "2499",
    "cart_items": "3"
  }
}
```

### Send Template

**Endpoint:** `POST /send-template`

**Payload:**
```json
{
  "apiKey": "your_api_key",
  "campaignName": "your_campaign",
  "destination": "919876543210",
  "userName": "abandoned_cart_reminder",
  "templateParams": ["John", "Gold Chain", "₹2,499"]
}
```

---

## Best Practices

### Segmentation
- Keep segments simple and focused
- Use clear naming conventions
- Regularly clean up inactive segments
- Test segments with small groups first

### Campaigns
- Always preview before sending
- Test with your own number first
- Respect opt-out requests immediately
- Monitor delivery rates and adjust timing

### Templates
- Keep messages concise and clear
- Use personalization ({{1}}, {{2}})
- Include clear call-to-action
- Add unsubscribe option for marketing

### Compliance
- Get explicit consent before messaging
- Honor opt-out requests within 24 hours
- Don't send promotional messages after 9 PM
- Follow WhatsApp Business Policy

---

## Troubleshooting

### Contact Not Receiving Messages

**Check:**
1. Phone number format (with country code, no +)
2. Contact opted out?
3. Template approved?
4. Campaign active?
5. Segment conditions met?

### Low Delivery Rate

**Possible Causes:**
- Invalid phone numbers
- Users blocked your number
- Sending outside business hours
- Template quality score low

**Solutions:**
- Clean contact list regularly
- Send during 10 AM - 8 PM
- Improve template content
- Monitor analytics

### API Errors

**Common Issues:**
- Invalid API key → Check credentials
- Rate limit exceeded → Slow down requests
- Template not found → Verify template name
- Invalid phone format → Use country code without +

---

## Summary

### chicx-bot (Support)
- Customer conversations
- FAQ support
- Order inquiries
- OTP authentication
- Voice confirmations

### AiSensy (Marketing)
- Abandoned cart campaigns
- Product announcements
- Sales promotions
- Bulk broadcasts
- Customer segments

**Integration:** Your CHICX backend pushes events to AiSensy API, which triggers automated campaigns based on segments.

**Cost:** Included in your AiSensy Pro plan (unlimited contacts, segments, API access).