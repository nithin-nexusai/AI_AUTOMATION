# AiSensy Integration Guide for Backend Team

**Target Audience:** CHICX E-commerce Backend Developers  
**Purpose:** Integrate AiSensy API for marketing automation  
**Last Updated:** April 22, 2026

---

## What You Need to Know

### Your Responsibility

**Backend team's job:** Detect events and tag contacts in AiSensy

**You do NOT handle:**
- Creating message templates (Marketing team)
- Configuring campaigns (Marketing team)
- Sending messages (AiSensy platform)
- Analytics and reporting (Marketing team)

### How It Works

```
Your Backend detects event (e.g., cart abandoned)
    ↓
Call AiSensy API to tag the customer
    ↓
Done! Marketing team's campaigns handle the rest
```

---

## Setup

### 1. Get Credentials from Marketing Team

Ask marketing team for:
- **API Key** (starts with `sk_live_...`)
- **Campaign Name** (e.g., `chicx_main_campaign`)

### 2. Add to Environment Variables

```env
AISENSY_API_KEY=sk_live_your_api_key_here
AISENSY_CAMPAIGN_NAME=chicx_main_campaign
```

### 3. Create HTTP Client

Build a simple HTTP client that can:
- Make POST requests to `https://backend.aisensy.com/campaign/t1/api/v2/contacts/tag`
- Send JSON payload
- Handle 10 second timeout
- Retry on failure (3 attempts with exponential backoff)
- Log errors

---

## What Events to Detect

You need to detect and tag 3 types of events:

### Event 1: Abandoned Cart

**When:** Cart inactive for 30+ minutes without purchase

**What to do:**
1. Run cron job every 30 minutes
2. Query database for abandoned carts
3. For each cart, call AiSensy API with:
   - Phone number (format: "919876543210")
   - Tag: `["abandoned_cart"]`
   - Attributes: `cart_value`, `product_name`, `customer_name`
4. Mark cart as notified in your database

**Database tracking:** Add `abandoned_notified` boolean flag to prevent duplicates

---

### Event 2: New Customer Registration

**When:** New user account created

**What to do:**
1. Hook into registration flow
2. Call AiSensy API with:
   - Phone number
   - Tag: `["new_customer"]`
   - Attributes: `signup_date`, `source`

---

### Event 3: VIP Customer Identification

**When:** Daily at 2 AM (cron job)

**What to do:**
1. Query database for customers with:
   - 5+ completed orders OR
   - Lifetime value ≥ ₹10,000
2. For each VIP, call AiSensy API with:
   - Phone number
   - Tag: `["vip_customer"]`
   - Attributes: `total_orders`, `lifetime_value`

---

## API Call Format

### Endpoint
```
POST https://backend.aisensy.com/campaign/t1/api/v2/contacts/tag
```

### Request Payload
```json
{
  "apiKey": "sk_live_your_api_key",
  "campaignName": "chicx_main_campaign",
  "destination": "919876543210",
  "tags": ["abandoned_cart"],
  "attributes": {
    "customer_name": "John Doe",
    "cart_value": "2499",
    "product_name": "Gold Chain"
  }
}
```

### Phone Number Format
- Include country code
- No + symbol
- No spaces
- Example: "919876543210" (not "+91 9876543210")

### Success Response
```json
{
  "status": "success",
  "message": "Contact tagged successfully"
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Invalid API key",
  "error_code": "AUTH_FAILED"
}
```

---

## Error Handling

### Common Errors

**401 Unauthorized**
- Check API key is correct
- Verify campaign name matches

**429 Rate Limit**
- Max 100 requests per minute
- Add 600ms delay between requests
- Implement retry with exponential backoff

**Invalid Phone Number**
- Verify format: country code + number, no +
- Example: "919876543210"

### Retry Logic

For failed API calls:
1. Wait 4 seconds
2. Retry (attempt 2)
3. Wait 8 seconds
4. Retry (attempt 3)
5. Log error and alert team

---

## Testing

### Test Steps

1. **Get test credentials** from marketing team
2. **Make test API call** with your own phone number
3. **Ask marketing team** to verify in AiSensy dashboard:
   - Contact exists
   - Tags applied correctly
   - Attributes stored properly

### Test Payload
```json
{
  "apiKey": "sk_test_your_test_key",
  "campaignName": "test_campaign",
  "destination": "919876543210",
  "tags": ["test"],
  "attributes": {
    "test": "true"
  }
}
```

---

## Production Checklist

Before deploying:

- [ ] Production API credentials configured
- [ ] Environment variables set
- [ ] HTTP client implemented with timeout
- [ ] Retry logic implemented
- [ ] Error logging configured
- [ ] Abandoned cart cron job scheduled (every 30 minutes)
- [ ] VIP customer cron job scheduled (daily 2 AM)
- [ ] Database tracking flags added
- [ ] Tested with real phone numbers
- [ ] Marketing team verified tags in dashboard

---

## Cron Jobs

```bash
# Abandoned cart detection - Every 30 minutes
*/30 * * * * /path/to/detect_abandoned_carts

# VIP customer identification - Daily at 2 AM
0 2 * * * /path/to/identify_vip_customers
```

---

## Quick Reference

### What Backend Does
1. Detect events (cart abandonment, orders, etc.)
2. Call AiSensy API to tag contacts
3. Log successes and failures

### What Marketing Does
1. Create message templates
2. Configure automated campaigns
3. Monitor performance
4. Optimize messaging

### Integration Point
- **Single API endpoint:** POST /contacts/tag
- **Your job:** Tag contacts when events occur
- **Their job:** Everything else

---

## Support

**For API/Integration Issues:**
- Contact: Tech Lead
- Slack: #backend-support

**For Campaign/Template Issues:**
- Contact: Marketing Team
- They manage AiSensy dashboard

**AiSensy Technical Support:**
- Email: support@aisensy.com
- Include: API key, phone number, error message

---

## Summary

**What you build:**
- HTTP client for AiSensy API
- Event detection (abandoned cart, VIP customers, new customers)
- Cron jobs for periodic checks
- Error handling and logging

**What you DON'T build:**
- Message templates (marketing team creates in AiSensy)
- Campaign logic (marketing team configures in AiSensy)
- Message sending (AiSensy platform handles)
- Analytics (marketing team monitors in AiSensy)

**Your integration is complete when:**
- Events are detected correctly
- API calls succeed
- Contacts are tagged in AiSensy
- Marketing team confirms tags appear in dashboard

That's it! Keep it simple - detect events, tag contacts, done.
