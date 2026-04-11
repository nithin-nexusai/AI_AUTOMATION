# Simplified Architecture - Support Bot Only

## Overview

The chicx-bot is now **simplified to focus only on customer support**. All marketing activities (abandoned cart, campaigns, broadcasts) are handled directly through the **AiSensy dashboard**.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Customer Interactions                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
        ┌─────────────────────────────────────────┐
        │                                         │
        ↓                                         ↓
┌───────────────────┐                  ┌──────────────────────┐
│   Support Bot     │                  │   Marketing          │
│   (chicx-bot)     │                  │   (AiSensy Dashboard)│
├───────────────────┤                  ├──────────────────────┤
│ • FAQ Support     │                  │ • Abandoned Cart     │
│ • Order Inquiries │                  │ • New Products       │
│ • Product Search  │                  │ • Sales Campaigns    │
│ • Conversations   │                  │ • Bulk Broadcasts    │
│                   │                  │ • Segments           │
│ Meta Cloud API    │                  │ AiSensy Platform     │
│ (1 WhatsApp #)    │                  │ (Separate WhatsApp #)│
└───────────────────┘                  └──────────────────────┘
        │                                         │
        ↓                                         ↓
┌───────────────────┐                  ┌──────────────────────┐
│ chicx-bot DB      │                  │ AiSensy Cloud        │
│ • Conversations   │                  │ • Contact Segments   │
│ • FAQs (pgvector) │                  │ • Campaign Stats     │
│ • Call Records    │                  │ • Templates          │
└───────────────────┘                  └──────────────────────┘
```

## What chicx-bot Does (Support Only)

### ✅ Handles:
1. **Customer Conversations** - AI-powered chat support
2. **FAQ Queries** - Semantic search with 101 FAQs
3. **Product Search** - Real-time product catalog queries
4. **Order Inquiries** - Order status and history
5. **Voice Calls** - Bolna integration for order confirmations

### ❌ Does NOT Handle:
1. ~~Marketing campaigns~~
2. ~~Abandoned cart reminders~~
3. ~~Bulk broadcasts~~
4. ~~Promotional messages~~
5. ~~Segment-based targeting~~

## What AiSensy Dashboard Does (Marketing Only)

### ✅ Handles:
1. **Abandoned Cart Campaigns** - Automated reminders
2. **New Product Announcements** - Bulk broadcasts
3. **Sales & Promotions** - Targeted campaigns
4. **Customer Segments** - Tag-based filtering
5. **Template Management** - Marketing templates

### How It Works:
1. Your CHICX backend detects events (cart abandonment, new orders)
2. Backend calls AiSensy API to tag contacts
3. AiSensy creates segments automatically
4. You trigger campaigns from AiSensy dashboard
5. Messages sent from separate marketing WhatsApp number

## Configuration Changes

### Before (Complex - Two Numbers):
```python
# Support number
whatsapp_phone_number_id: str = ""
whatsapp_access_token: str = ""

# Marketing number
whatsapp_marketing_phone_number_id: str = ""
whatsapp_marketing_access_token: str = ""
```

### After (Simple - One Number):
```python
# Support bot only
whatsapp_phone_number_id: str = ""
whatsapp_access_token: str = ""
# Marketing handled via AiSensy dashboard (separate number)
```

## Benefits of This Approach

### 1. **Simplicity**
- chicx-bot focuses on what it does best: support conversations
- No complex routing logic for marketing vs support
- Easier to maintain and debug

### 2. **Separation of Concerns**
- Support team manages chicx-bot
- Marketing team manages AiSensy dashboard
- Clear ownership and responsibilities

### 3. **Better Tools for Each Use Case**
- **chicx-bot**: AI conversations, semantic search, real-time queries
- **AiSensy**: Campaign management, segments, analytics, A/B testing

### 4. **Cost Efficiency**
- No need to build marketing automation in chicx-bot
- AiSensy Pro plan already includes all marketing features
- Avoid duplicate functionality

### 5. **Scalability**
- Support bot scales independently
- Marketing campaigns scale independently
- No interference between the two

## Integration Points

### CHICX Backend → AiSensy
Your main e-commerce backend pushes events to AiSensy:

```python
# When cart is abandoned
aisensy.tag_contact(
    phone="919876543210",
    tags=["abandoned_cart"],
    attributes={"cart_value": "2499"}
)

# When order is placed
aisensy.tag_contact(
    phone="919876543210",
    tags=["customer", "purchased"],
    attributes={"order_id": "ORD123", "order_value": "2499"}
)
```

### AiSensy Dashboard → Customers
Marketing team creates campaigns:
1. Create segment: "Abandoned Cart - Last 24h"
2. Create campaign: "Cart Reminder"
3. Set trigger: "When contact enters segment"
4. Activate campaign

## File Changes Made

### Updated Files:
1. **`chicx-bot/app/config.py`**
   - Removed marketing WhatsApp number config
   - Simplified to single support number
   - Added clarifying comments

### New Documentation:
1. **`docs/SIMPLIFIED_ARCHITECTURE.md`** (this file)
   - Explains new simplified approach
   - Clear separation of responsibilities

2. **`docs/AISENSY_SEGMENTS_INTEGRATION.md`**
   - How to integrate CHICX backend with AiSensy
   - Segment creation and campaign setup

3. **`docs/AISENSY_DASHBOARD_GUIDE.md`**
   - Complete guide to using AiSensy dashboard
   - Campaign creation, templates, automation

## Migration Path

### If You Already Have Marketing Code:
1. **Keep it for now** - It won't break anything
2. **Test AiSensy dashboard** - Verify it meets your needs
3. **Gradually migrate** - Move campaigns one by one
4. **Remove old code** - Once fully migrated

### If Starting Fresh:
1. **Use this simplified approach** - No marketing code needed
2. **Set up AiSensy dashboard** - Create segments and campaigns
3. **Integrate CHICX backend** - Push events to AiSensy API
4. **Launch** - Support bot and marketing work independently

## Summary

| Feature | chicx-bot | AiSensy Dashboard |
|---------|-----------|-------------------|
| Customer Support | ✅ | ❌ |
| FAQ Search | ✅ | ❌ |
| Product Queries | ✅ | ❌ |
| Order Status | ✅ | ❌ |
| Voice Calls | ✅ | ❌ |
| Abandoned Cart | ❌ | ✅ |
| Campaigns | ❌ | ✅ |
| Broadcasts | ❌ | ✅ |
| Segments | ❌ | ✅ |
| A/B Testing | ❌ | ✅ |

**Result**: Simpler codebase, better tools for each use case, easier maintenance.