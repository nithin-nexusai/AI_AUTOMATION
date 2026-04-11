# AiSensy Segments & Database Integration Guide

## Understanding AiSensy Segments

### What Are Segments?

Segments in AiSensy are **filtered groups of contacts** based on specific criteria. They allow you to target specific customer groups with personalized campaigns.

### How AiSensy Knows About Cart Abandonment

**AiSensy CANNOT automatically detect cart abandonment** - it doesn't have direct access to your database. You need to **push data to AiSensy** using their API.

## Two Integration Approaches

### Option 1: Push Events to AiSensy (Recommended for Pro Plan)

Your CHICX backend pushes events to AiSensy when they happen.

#### How It Works:

```
Customer abandons cart
    ↓
CHICX Backend detects it
    ↓
Backend calls AiSensy API to tag user
    ↓
AiSensy creates segment automatically
    ↓
You trigger campaign to that segment
```

#### Implementation:

**1. Add AiSensy Contact Tagging API**

```python
# In chicx-bot/app/services/aisensy.py

async def tag_contact(
    self,
    phone: str,
    tags: list[str],
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Tag a contact in AiSensy for segmentation.
    
    Args:
        phone: Contact phone number (with country code)
        tags: List of tags (e.g., ["abandoned_cart", "high_value"])
        attributes: Custom attributes (e.g., {"cart_value": "2499", "product": "Gold Chain"})
    
    Returns:
        API response
    """
    if self._http_client is None:
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    payload = {
        "apiKey": self.api_key,
        "campaignName": self.campaign_name,
        "destination": phone,
        "tags": tags,
    }
    
    if attributes:
        payload["attributes"] = attributes
    
    try:
        response = await self._http_client.post(
            f"{self.base_url}/contacts/tag",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"AiSensy tag contact error: {e}")
        raise
```

**2. Create Webhook Endpoint in Your CHICX Backend**

Your main CHICX e-commerce backend should call this when cart is abandoned:

```python
# Example: In your CHICX backend (not chicx-bot)
# File: /api/cart_abandoned.php or similar

async def on_cart_abandoned(user_id: int, cart_data: dict):
    """Called when user abandons cart."""
    
    # Get user phone from your database
    user = get_user_by_id(user_id)
    phone = user['phone']
    
    # Calculate cart value
    cart_value = sum(item['price'] * item['quantity'] for item in cart_data['items'])
    
    # Tag in AiSensy
    aisensy_client = get_aisensy_client()
    await aisensy_client.tag_contact(
        phone=phone,
        tags=["abandoned_cart"],
        attributes={
            "cart_value": str(cart_value),
            "cart_items": len(cart_data['items']),
            "abandoned_at": datetime.now().isoformat(),
        }
    )
```

**3. Create Segment in AiSensy Dashboard**

1. Go to **Contacts → Segments**
2. Click **Create Segment**
3. Set conditions:
   - Tag = "abandoned_cart"
   - Abandoned_at = "Last 24 hours"
4. Save as "Abandoned Cart - 24h"

**4. Create Automated Campaign**

1. Go to **Campaigns → Create Campaign**
2. Select segment: "Abandoned Cart - 24h"
3. Choose template: "abandoned_cart_reminder"
4. Set trigger: "When contact enters segment"
5. Activate campaign

### Option 2: Sync Database to AiSensy (Batch Approach)

Run a scheduled job that syncs your database to AiSensy periodically.

#### How It Works:

```
Cron job runs every hour
    ↓
Query CHICX database for abandoned carts
    ↓
For each abandoned cart:
    - Tag user in AiSensy
    - Add cart details as attributes
    ↓
AiSensy segments update automatically
```

#### Implementation:

**1. Create Sync Script**

```python
# File: chicx-bot/scripts/sync_segments.py

import asyncio
from datetime import datetime, timedelta
from app.services.aisensy import get_aisensy_client
from app.services.chicx_api import get_chicx_client

async def sync_abandoned_carts():
    """Sync abandoned carts to AiSensy."""
    
    # This would query YOUR main CHICX database
    # Not the chicx-bot database (which only has conversations)
    
    # Example query (you need to implement this in your CHICX backend):
    # SELECT user_id, phone, cart_data, updated_at 
    # FROM carts 
    # WHERE status = 'abandoned' 
    # AND updated_at > NOW() - INTERVAL 24 HOUR
    
    abandoned_carts = await get_abandoned_carts_from_chicx_db()
    
    aisensy = get_aisensy_client()
    
    for cart in abandoned_carts:
        try:
            await aisensy.tag_contact(
                phone=cart['phone'],
                tags=["abandoned_cart"],
                attributes={
                    "cart_value": str(cart['total_value']),
                    "cart_items": cart['item_count'],
                    "abandoned_at": cart['updated_at'].isoformat(),
                }
            )
            print(f"Tagged {cart['phone']} for abandoned cart")
        except Exception as e:
            print(f"Error tagging {cart['phone']}: {e}")

if __name__ == "__main__":
    asyncio.run(sync_abandoned_carts())
```

**2. Schedule with Cron**

```bash
# Run every hour
0 * * * * cd /opt/chicx-bot && python scripts/sync_segments.py
```

## Database Schema Considerations

### Your Current Setup:

**chicx-bot database** (PostgreSQL):
- Only stores **conversation data**
- User model has: `id`, `phone`, `name`, `created_at`
- No cart or order data

**CHICX main database** (your e-commerce backend):
- Stores **all business data**: products, orders, carts, users
- This is where cart abandonment is tracked

### Integration Architecture:

```
┌─────────────────────────────────────────┐
│   CHICX Main Database (E-commerce)      │
│   - Users                                │
│   - Products                             │
│   - Orders                               │
│   - Carts (with abandonment tracking)   │
└─────────────────┬───────────────────────┘
                  │
                  │ API Calls
                  ↓
┌─────────────────────────────────────────┐
│   chicx-bot (WhatsApp Bot)              │
│   - Conversations                        │
│   - FAQs                                 │
│   - Calls CHICX API for order/cart data │
└─────────────────┬───────────────────────┘
                  │
                  │ Push Events
                  ↓
┌─────────────────────────────────────────┐
│   AiSensy (Marketing Platform)          │
│   - Contact segments                     │
│   - Campaign automation                  │
│   - Template messages                    │
└─────────────────────────────────────────┘
```

## Recommended Approach for Your Pro Plan

### Step 1: Add Cart Abandonment Tracking to CHICX Backend

In your main CHICX e-commerce backend, add:

```sql
-- Add to your CHICX database
ALTER TABLE carts ADD COLUMN abandoned_at TIMESTAMP NULL;
ALTER TABLE carts ADD COLUMN reminded_at TIMESTAMP NULL;

-- Create index for performance
CREATE INDEX idx_carts_abandoned ON carts(abandoned_at) WHERE abandoned_at IS NOT NULL;
```

### Step 2: Detect Abandonment

```php
// In your CHICX backend (PHP example)
// File: /cron/check_abandoned_carts.php

// Run every 30 minutes
$abandoned_threshold = 30; // minutes

$query = "
    UPDATE carts 
    SET abandoned_at = NOW() 
    WHERE status = 'active' 
    AND updated_at < DATE_SUB(NOW(), INTERVAL $abandoned_threshold MINUTE)
    AND abandoned_at IS NULL
";

mysqli_query($conn, $query);

// Get newly abandoned carts
$query = "
    SELECT c.*, u.phone 
    FROM carts c 
    JOIN users u ON c.user_id = u.id 
    WHERE c.abandoned_at IS NOT NULL 
    AND c.reminded_at IS NULL
";

$result = mysqli_query($conn, $query);

while ($cart = mysqli_fetch_assoc($result)) {
    // Call AiSensy API to tag user
    tag_user_in_aisensy($cart['phone'], 'abandoned_cart', [
        'cart_value' => $cart['total'],
        'cart_items' => $cart['item_count'],
    ]);
    
    // Mark as reminded
    mysqli_query($conn, "UPDATE carts SET reminded_at = NOW() WHERE id = {$cart['id']}");
}
```

### Step 3: Create AiSensy Segment

1. **Dashboard → Contacts → Segments**
2. **Create Segment**: "Abandoned Cart - Recent"
3. **Conditions**:
   - Has tag: "abandoned_cart"
   - Tag added: "Last 24 hours"
4. **Save**

### Step 4: Create Automated Campaign

1. **Dashboard → Campaigns → Create**
2. **Type**: Automated
3. **Trigger**: "When contact enters segment"
4. **Segment**: "Abandoned Cart - Recent"
5. **Template**: Your abandoned cart template
6. **Delay**: 1 hour after entering segment
7. **Activate**

## Cost Considerations

### AiSensy Pro Plan Includes:

- ✅ Unlimited contacts
- ✅ Unlimited segments
- ✅ API access for tagging
- ✅ Automated campaigns
- ✅ Custom attributes

### API Rate Limits:

- Contact tagging: ~100 requests/minute
- Template sending: Based on your WhatsApp tier

## Testing the Integration

### Test Abandoned Cart Flow:

```bash
# 1. Tag a test user
curl -X POST "https://backend.aisensy.com/campaign/t1/api/v2/contacts/tag" \
  -H "Content-Type: application/json" \
  -d '{
    "apiKey": "your_api_key",
    "campaignName": "your_campaign",
    "destination": "919876543210",
    "tags": ["abandoned_cart"],
    "attributes": {
      "cart_value": "2499",
      "cart_items": "3"
    }
  }'

# 2. Check if user appears in segment (AiSensy Dashboard)

# 3. Verify campaign triggers automatically
```

## Summary

**AiSensy CANNOT directly access your database.** You must:

1. **Detect abandonment** in your CHICX backend
2. **Push events** to AiSensy via API (tag contacts)
3. **Create segments** in AiSensy based on tags
4. **Set up automated campaigns** to target those segments

**Recommended**: Use **Option 1 (Push Events)** for real-time targeting with your Pro plan.

## Next Steps

1. Add cart abandonment tracking to CHICX backend database
2. Implement AiSensy contact tagging API
3. Create cron job to detect and tag abandoned carts
4. Set up segments and automated campaigns in AiSensy dashboard
5. Test with a few users before full rollout