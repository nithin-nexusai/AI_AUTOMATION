# AiSensy Dashboard Guide for CHICX WhatsApp Bot

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Dashboard Navigation](#dashboard-navigation)
4. [Creating WhatsApp Templates](#creating-whatsapp-templates)
5. [Sending Campaigns](#sending-campaigns)
6. [Automation & Workflows](#automation--workflows)
7. [Analytics & Reports](#analytics--reports)
8. [API Integration](#api-integration)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

AiSensy is a WhatsApp Business API platform that enables you to:
- Send marketing templates (abandoned cart, promotions, announcements)
- Create automated workflows
- Manage customer conversations
- Track campaign performance
- Integrate with your backend systems

**CHICX Setup:**
- **Marketing Number**: Connected to AiSensy for template messages
- **Support Number**: Connected to Meta Cloud API for conversational AI (current bot)

---

## Getting Started

### 1. Access Your Dashboard

1. Go to [https://app.aisensy.com](https://app.aisensy.com)
2. Log in with your credentials
3. Select your CHICX workspace

### 2. Dashboard Overview

Upon login, you'll see:
- **Home**: Quick stats and recent activity
- **Contacts**: Customer database
- **Campaigns**: Template message campaigns
- **Automation**: Workflow builder
- **Templates**: WhatsApp message templates
- **Analytics**: Performance metrics
- **Settings**: Configuration and API keys

---

## Dashboard Navigation

### Main Sections

#### 1. **Home Dashboard**
- **Quick Stats**: Messages sent, delivered, read rates
- **Recent Campaigns**: Last 5 campaigns with performance
- **Active Automations**: Running workflows
- **Credit Balance**: Remaining message credits

#### 2. **Contacts**
- **All Contacts**: Complete customer list
- **Segments**: Filtered groups (e.g., "Abandoned Cart", "VIP Customers")
- **Import/Export**: Bulk contact management
- **Custom Fields**: Add metadata (order_id, cart_value, etc.)

#### 3. **Campaigns**
- **Active**: Currently running campaigns
- **Scheduled**: Future campaigns
- **Completed**: Past campaigns with analytics
- **Drafts**: Saved but not sent

#### 4. **Templates**
- **Approved**: Ready to use
- **Pending**: Awaiting Meta approval
- **Rejected**: Need modification
- **Drafts**: Not submitted yet

---

## Creating WhatsApp Templates

### Template Types

WhatsApp templates are pre-approved message formats. For CHICX, you'll need:

1. **Marketing Templates** (Promotional)
   - Abandoned cart reminders
   - New collection launches
   - Sale announcements
   - Festive offers

2. **Utility Templates** (Transactional)
   - Order confirmations
   - Shipping updates
   - Delivery notifications
   - Payment receipts

### Step-by-Step: Create a Template

#### 1. Navigate to Templates
```
Dashboard → Templates → Create New Template
```

#### 2. Choose Template Category
- **Marketing**: Promotional content (requires opt-in)
- **Utility**: Transactional updates (no opt-in needed)
- **Authentication**: OTPs and verification codes

#### 3. Fill Template Details

**Example: Abandoned Cart Template**

```
Template Name: abandoned_cart_reminder
Category: Marketing
Language: English

Header: Image
[Upload jewelry image or use dynamic variable]

Body:
Hi {{1}},

You left some beautiful pieces in your cart! 🛍️

{{2}} is waiting for you. Complete your order now and get:
✨ Free shipping on orders above ₹999
💎 Lifetime warranty on all jewelry
🎁 Special gift with your first order

Your cart value: ₹{{3}}

Don't miss out! Items are selling fast.

Shop now: {{4}}

Footer:
Reply STOP to unsubscribe

Buttons:
1. Quick Reply: "View Cart"
2. URL: "Complete Order" → {{5}}
```

**Variables Explained:**
- `{{1}}`: Customer name
- `{{2}}`: Product name
- `{{3}}`: Cart value
- `{{4}}`: Website URL
- `{{5}}`: Checkout URL

#### 4. Add Sample Content
Meta requires sample values for approval:
```
{{1}}: Priya
{{2}}: Gold Plated Necklace Set
{{3}}: 2,499
{{4}}: https://thechicx.com
{{5}}: https://thechicx.com/checkout/abc123
```

#### 5. Submit for Approval
- Review template
- Click "Submit for Approval"
- Wait 24-48 hours for Meta review
- Check status in Templates section

### Template Best Practices

✅ **DO:**
- Keep messages concise (under 1024 characters)
- Use clear call-to-action buttons
- Include opt-out instructions
- Test with sample data first
- Use dynamic variables for personalization

❌ **DON'T:**
- Use promotional language in utility templates
- Include external links in marketing templates without approval
- Use all caps or excessive emojis
- Send marketing messages without opt-in
- Use misleading or clickbait content

---

## Sending Campaigns

### Quick Campaign Setup

#### 1. Create New Campaign
```
Dashboard → Campaigns → Create Campaign
```

#### 2. Campaign Configuration

**Basic Details:**
```
Campaign Name: Diwali Sale 2024
Template: diwali_sale_announcement
Segment: All Active Customers
```

**Scheduling:**
- **Send Now**: Immediate delivery
- **Schedule**: Pick date and time
- **Optimal Time**: AI-suggested best time

**Personalization:**
```
Variable Mapping:
{{1}} → Contact.first_name
{{2}} → "50% OFF"
{{3}} → "https://thechicx.com/diwali-sale"
```

#### 3. Test Campaign
```
1. Click "Send Test Message"
2. Enter your WhatsApp number
3. Verify message appearance
4. Check links and buttons
5. Confirm personalization works
```

#### 4. Launch Campaign
```
1. Review summary
2. Check credit balance
3. Click "Launch Campaign"
4. Monitor real-time delivery
```

### Campaign Types

#### A. Abandoned Cart Recovery
```
Trigger: Cart abandoned for 2 hours
Template: abandoned_cart_reminder
Segment: Abandoned Cart (Last 24h)
Variables:
  - Customer name
  - Product name
  - Cart value
  - Checkout link
```

#### B. Order Confirmation
```
Trigger: Order placed
Template: order_confirmation
Segment: Recent Orders
Variables:
  - Order ID
  - Order total
  - Estimated delivery
  - Tracking link
```

#### C. New Collection Launch
```
Trigger: Manual/Scheduled
Template: new_collection_announcement
Segment: All Opted-In Customers
Variables:
  - Collection name
  - Launch date
  - Preview link
```

---

## Automation & Workflows

### Workflow Builder

#### 1. Access Automation
```
Dashboard → Automation → Create Workflow
```

#### 2. Workflow Components

**Triggers:**
- Contact added to segment
- Tag applied
- Custom field updated
- Time-based (daily, weekly)
- API webhook

**Actions:**
- Send template message
- Add to segment
- Update custom field
- Wait for duration
- Send to API endpoint

**Conditions:**
- If/Else logic
- Field value checks
- Segment membership
- Time conditions

#### 3. Example Workflow: Abandoned Cart

```
Workflow Name: Abandoned Cart Recovery

Trigger: Contact added to "Abandoned Cart" segment

Step 1: Wait 2 hours
Step 2: Check if "order_placed" = false
  ├─ Yes → Send "abandoned_cart_reminder" template
  └─ No → End workflow

Step 3: Wait 24 hours
Step 4: Check if "order_placed" = false
  ├─ Yes → Send "abandoned_cart_final_reminder" template
  └─ No → End workflow

Step 5: Remove from "Abandoned Cart" segment
```

#### 4. Example Workflow: Post-Purchase

```
Workflow Name: Post-Purchase Engagement

Trigger: "order_placed" = true

Step 1: Send "order_confirmation" template immediately
Step 2: Wait 1 day
Step 3: Send "shipping_update" template
Step 4: Wait 3 days
Step 5: Send "delivery_confirmation" template
Step 6: Wait 7 days
Step 7: Send "review_request" template
Step 8: Wait 30 days
Step 9: Send "repurchase_reminder" template
```

### Workflow Best Practices

1. **Test Thoroughly**: Use test contacts before going live
2. **Set Limits**: Avoid message fatigue (max 1-2 per day)
3. **Add Exit Conditions**: Stop workflow if goal achieved
4. **Monitor Performance**: Check completion rates
5. **A/B Test**: Try different message timings

---

## Analytics & Reports

### Key Metrics

#### 1. Campaign Performance
```
Dashboard → Analytics → Campaigns
```

**Metrics to Track:**
- **Sent**: Total messages sent
- **Delivered**: Successfully delivered (target: >95%)
- **Read**: Messages opened (target: >60%)
- **Clicked**: Button/link clicks (target: >10%)
- **Replied**: Customer responses (target: >5%)
- **Converted**: Desired action taken (target: >2%)

#### 2. Template Analytics
```
Dashboard → Templates → [Select Template] → Analytics
```

**Per-Template Metrics:**
- Delivery rate
- Read rate
- Click-through rate (CTR)
- Conversion rate
- Revenue generated (if tracked)

#### 3. Automation Reports
```
Dashboard → Automation → [Select Workflow] → Reports
```

**Workflow Metrics:**
- Contacts entered
- Contacts completed
- Drop-off points
- Average completion time
- Conversion rate

#### 4. Contact Insights
```
Dashboard → Contacts → [Select Contact] → Activity
```

**Per-Contact View:**
- Message history
- Campaign interactions
- Workflow participation
- Custom field values
- Lifetime value

### Export Reports

```
1. Go to Analytics section
2. Select date range
3. Choose metrics
4. Click "Export"
5. Download CSV/Excel
```

---

## API Integration

### Getting API Credentials

#### 1. Access API Settings
```
Dashboard → Settings → API → Generate API Key
```

#### 2. API Key Details
```
API Key: aisensy_xxxxxxxxxxxxxxxxxxxxxxxx
API Endpoint: https://backend.aisensy.com/campaign/t1/api/v2
```

### Common API Operations

#### 1. Send Template Message

**Endpoint:** `POST /campaign/t1/api/v2`

**Request:**
```json
{
  "apiKey": "your_api_key",
  "campaignName": "abandoned_cart_recovery",
  "destination": "919876543210",
  "userName": "Priya",
  "templateParams": [
    "Priya",
    "Gold Plated Necklace Set",
    "2499",
    "https://thechicx.com/cart/abc123"
  ],
  "media": {
    "url": "https://thechicx.com/images/product.jpg",
    "filename": "necklace.jpg"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Message sent successfully",
  "messageId": "wamid.xxxxx"
}
```

#### 2. Add Contact to Segment

**Endpoint:** `POST /contacts/add-to-segment`

**Request:**
```json
{
  "apiKey": "your_api_key",
  "phoneNumber": "919876543210",
  "segmentName": "Abandoned Cart",
  "customFields": {
    "cart_value": "2499",
    "cart_items": "Gold Necklace, Silver Earrings",
    "cart_url": "https://thechicx.com/cart/abc123"
  }
}
```

#### 3. Update Contact Custom Fields

**Endpoint:** `POST /contacts/update`

**Request:**
```json
{
  "apiKey": "your_api_key",
  "phoneNumber": "919876543210",
  "customFields": {
    "order_placed": "true",
    "order_id": "ORD123456",
    "order_value": "2499",
    "order_date": "2024-04-11"
  }
}
```

### Integration with CHICX Backend

See [`AISENSY_INTEGRATION_PLAN.md`](AISENSY_INTEGRATION_PLAN.md) for detailed backend integration guide.

---

## Best Practices

### 1. Message Timing

**Optimal Send Times:**
- **Morning**: 10:00 AM - 12:00 PM (High engagement)
- **Evening**: 6:00 PM - 8:00 PM (Peak time)
- **Avoid**: Late night (10 PM - 8 AM), early morning (6 AM - 9 AM)

**Frequency Limits:**
- Marketing: Max 1 per day, 3 per week
- Utility: As needed (order updates)
- Abandoned Cart: 2 reminders max (2h, 24h)

### 2. Personalization

**Always Include:**
- Customer name
- Relevant product details
- Personalized recommendations
- Order-specific information

**Dynamic Content:**
```
Hi {{name}},

Your {{product_name}} is ready to ship! 🎉

Order #{{order_id}}
Total: ₹{{order_total}}
Estimated Delivery: {{delivery_date}}

Track your order: {{tracking_link}}
```

### 3. Compliance

**GDPR & Privacy:**
- Obtain explicit opt-in for marketing
- Provide clear opt-out mechanism
- Store consent records
- Honor unsubscribe requests immediately

**WhatsApp Policies:**
- Use approved templates only
- Don't send spam
- Respect 24-hour conversation window
- Follow category guidelines (marketing vs utility)

### 4. A/B Testing

**Test Variables:**
- Message timing
- Template variations
- Button text
- Image vs no image
- Offer amounts

**Example Test:**
```
Version A: "Get 20% OFF"
Version B: "Save ₹500 Today"

Split: 50/50
Duration: 3 days
Measure: Click-through rate
```

### 5. Segmentation

**Key Segments:**
- **VIP Customers**: Lifetime value > ₹10,000
- **Recent Buyers**: Purchased in last 30 days
- **Abandoned Cart**: Cart value > ₹500
- **Inactive**: No purchase in 90 days
- **First-Time Buyers**: Only 1 order

---

## Troubleshooting

### Common Issues

#### 1. Template Rejected

**Reasons:**
- Promotional content in utility template
- Missing opt-out instructions
- Unclear call-to-action
- Misleading content

**Solution:**
- Review Meta's template guidelines
- Modify template per feedback
- Resubmit for approval

#### 2. Low Delivery Rate (<90%)

**Possible Causes:**
- Invalid phone numbers
- Blocked by recipients
- WhatsApp number not active

**Solution:**
- Clean contact list
- Remove invalid numbers
- Verify number format (+91XXXXXXXXXX)

#### 3. Low Read Rate (<50%)

**Possible Causes:**
- Poor timing
- Irrelevant content
- Message fatigue

**Solution:**
- Test different send times
- Improve personalization
- Reduce frequency

#### 4. API Errors

**Common Errors:**
```
Error 401: Invalid API key
→ Regenerate API key in settings

Error 400: Invalid template params
→ Check variable count and order

Error 429: Rate limit exceeded
→ Reduce request frequency

Error 500: Server error
→ Contact AiSensy support
```

### Getting Help

**Support Channels:**
- **Email**: support@aisensy.com
- **Chat**: Dashboard → Help → Live Chat
- **Documentation**: https://docs.aisensy.com
- **Community**: https://community.aisensy.com

---

## Quick Reference

### Template Variables Syntax
```
{{1}}, {{2}}, {{3}}, ... {{n}}
```

### API Rate Limits
```
- 100 requests per minute
- 10,000 requests per day
```

### Message Costs
```
- Marketing: ₹0.35 per message
- Utility: ₹0.25 per message
- Authentication: ₹0.15 per message
```

### Template Approval Time
```
- Standard: 24-48 hours
- Expedited: 4-8 hours (premium)
```

---

## Next Steps

1. **Create Your First Template**
   - Start with order confirmation (utility)
   - Use the example provided above
   - Submit for approval

2. **Set Up Abandoned Cart Workflow**
   - Create segment for abandoned carts
   - Build 2-step reminder workflow
   - Test with sample contacts

3. **Integrate with Backend**
   - Follow [`AISENSY_INTEGRATION_PLAN.md`](AISENSY_INTEGRATION_PLAN.md)
   - Implement API calls
   - Test end-to-end flow

4. **Monitor & Optimize**
   - Track campaign performance
   - A/B test message variations
   - Refine based on analytics

---

## Additional Resources

- [AiSensy Official Documentation](https://docs.aisensy.com)
- [WhatsApp Business API Guidelines](https://developers.facebook.com/docs/whatsapp)
- [CHICX AiSensy Integration Plan](AISENSY_INTEGRATION_PLAN.md)
- [WhatsApp Template Examples](WHATSAPP_TEMPLATES.md)

---

**Last Updated:** April 11, 2026  
**Version:** 1.0  
**Maintained By:** CHICX Tech Team