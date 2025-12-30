# CHICX AI Platform: External API Configuration Guide

## 📋 Complete Setup Documentation for All External Services

**Version:** 1.0  
**Last Updated:** 2025-12-12  
**Document Purpose:** Comprehensive step-by-step guide for configuring all external APIs used in the CHICX AI Platform

---

## Table of Contents

1. [Quick Overview](#quick-overview)
2. [WhatsApp Cloud API (Meta)](#whatsapp-cloud-api-meta)
3. [DeepSeek LLM API](#deepseek-llm-api)
4. [OpenAI Embeddings API](#openai-embeddings-api)
5. [Exotel Telephony API](#exotel-telephony-api)
6. [ElevenLabs TTS API](#elevenlabs-tts-api)
7. [Deepgram STT API](#deepgram-stt-api)
8. [Shiprocket Shipping API](#shiprocket-shipping-api)
9. [Bolna Voice Agent (Self-Hosted)](#bolna-voice-agent-self-hosted)
10. [Complete Environment Variables](#complete-environment-variables)
11. [Cost Analysis & Estimates](#cost-analysis--estimates)
12. [Security & Best Practices](#security--best-practices)

---

## Quick Overview

### Services Summary

| # | Service | Purpose | Type | Est. Monthly Cost | Setup Time |
|---|---------|---------|------|-------------------|------------|
| 1 | **WhatsApp (Meta)** | Customer chat messaging | Cloud API | Free (1K conv) | 2-3 hours |
| 2 | **DeepSeek** | LLM for conversations | API | $2-20 | 5 minutes |
| 3 | **OpenAI** | Text embeddings (FAQ search) | API | $0.10-5 | 5 minutes |
| 4 | **Exotel** | Voice calls & telephony | API | ₹2K-5K ($24-60) | 1-2 days |
| 5 | **ElevenLabs** | Text-to-Speech (voice) | API | $11-99 | 10 minutes |
| 6 | **Deepgram** | Speech-to-Text (voice) | API | Free ($200 credits) | 5 minutes |
| 7 | **Shiprocket** | Shipping webhooks | Webhook | Free | 30 minutes |
| 8 | **Bolna** | Voice agent orchestrator | Self-hosted | Server only | 1 hour |
| 9 | **CHICX Backend** | Product/order data | Internal | N/A | Existing |

**Total Setup Time:** 1-2 days (mainly WhatsApp + Exotel verification)  
**Initial Cost:** ~$50-150/month for moderate usage

---

## WhatsApp Cloud API (Meta)

### 🎯 What You'll Need

**Before starting:**
- ✅ Facebook account
- ✅ Meta Business Manager account
- ✅ Verified business (legal entity)
- ✅ Dedicated phone number (not linked to any WhatsApp - personal or business)
- ✅ Official business website
- ✅ Business email address
- ✅ Business documents (GST, business license for India)

**⏱️ Time Required:** 2-3 hours setup + 2-5 days verification

### Step-by-Step Setup

#### Step 1: Create Meta Business Account (30 min)

1. **Go to** [business.facebook.com](https://business.facebook.com)
2. **Click** "Create Account"
3. **Enter business details:**
   ```
   Business Name: CHICX Fashion
   Your Name: [Your name]
   Business Email: [business email]
   ```
4. **Verify email** via link sent
5. **Add business address** and phone number

#### Step 2: Business Verification (Submit docs - 2-5 days wait)

1. **Navigate to** Business Settings → Security Center → Business Verification
2. **Upload documents:**
   - **For India:** GST Certificate OR Business Registration Certificate
   - **Proof of Address:** Utility bill, bank statement
   - **ID Proof:** PAN card of business owner
3. **Submit for review**
4. ⏰ **Wait:** Meta typically responds in 2-5 business days

#### Step 3: Create Meta Developer App (15 min)

1. **Go to** [developers.facebook.com](https://developers.facebook.com)
2. **Click** "My Apps" → "Create App"
3. **Select app type:** "Business"
4. **Fill details:**
   ```
   App Display Name: CHICX WhatsApp Bot
   App Contact Email: dev@chicx.in
   Business Account: [Select your Meta Business Account]
   ```
5. **Click** "Create App"
6. **Note down** your App ID

#### Step 4: Add WhatsApp Product (15 min)

1. **In your App Dashboard**, find "WhatsApp" product
2. **Click** "Set up"
3. **This automatically creates:**
   - Test WhatsApp Business Account (WABA)
   - Test phone number (for sending 1000 free messages)
4. **Copy these IDs:**
   ```
   Phone Number ID: 123456789012345
   WhatsApp Business Account ID: 987654321098765
   ```
5. **Save them** - you'll need these in `.env`

#### Step 5: Send Test Message (5 min)

1. **Go to** WhatsApp → API Setup
2. **Send test message:**
   - To: Your personal WhatsApp number
   - Template: `hello_world`
3. **Check** if message received on your phone
4. **Add test recipients** (up to 5 numbers for testing)
   - Click "To" field → "Manage phone number list"
   - Add numbers in E.164 format: `+919876543210`
   - Recipients get OTP to verify

#### Step 6: Add Production Phone Number (20 min + verification)

**⚠️ IMPORTANT:** Phone number must:
- NOT be registered with ANY WhatsApp account (personal, business, or WhatsApp Business app)
- Be a mobile number or landline
- Be able to receive SMS/calls for verification

**Steps:**

1. **Go to** WhatsApp → Getting Started → Add Phone Number
2. **Select** phone number type:
   - **Mobile** (recommended) - SMS verification
   - **Landline** - Voice call verification
3. **Enter number** in E.164 format: `+919876543210`
4. **Choose verification method:**
   - SMS (instant)
   - Voice call (for landlines)
5. **Enter the 6-digit OTP** received
6. **Set display name:**
   ```
   Display Name: CHICX
   Category: Shopping & Retail
   Description: CHICX Fashion - Sarees & Ethnic Wear
   Website: https://chicx.in
   ```
   
⏰ **Meta will review your display name** (1-2 days). You can send messages with pending display name, but it won't show to customers until approved.

#### Step 7: Create System User for Permanent Token (15 min)

**Why?** User access tokens expire. System users provide permanent tokens.

1. **Go to** Business Settings (business.facebook.com/settings)
2. **Navigate to** Users → System Users
3. **Click** "Add"
4. **Configure:**
   ```
   System User Name: CHICX API User
   System User Role: Admin
   ```
5. **Click** "Create System User"
6. **Click "Assign Assets"**
7. **Under "Apps":**
   - Select your app
   - Toggle "Manage app" (Full control)
8. **Under "WhatsApp Accounts":**
   - Select your WABA
   - Toggle "Manage WhatsApp Business Accounts" (Full control)
9. **Click** "Save Changes"

#### Step 8: Generate Permanent Access Token (10 min)

1. **Select** the system user you just created
2. **Click** "Generate New Token"
3. **Select** your app from dropdown
4. **Add permissions:**
   - ☑️ `whatsapp_business_management`
   - ☑️ `whatsapp_business_messaging`
   - ☑️ `business_management`
5. **Set expiration:** "Never" (for permanent token)
6. **Click** "Generate Token"
7. **⚠️ CRITICAL:** Copy the token IMMEDIATELY
   - It's shown only once!
   - If you lose it, you'll need to generate a new one
8. **Store securely** in `.env`:
   ```env
   WHATSAPP_ACCESS_TOKEN="EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
   ```

#### Step 9: Get App Secret (5 min)

1. **Go to** App Dashboard → Settings → Basic
2. **Click** "Show" next to "App Secret"
3. **Verify** your Facebook password
4. **Copy** the App Secret
5. **Store in `.env`:**
   ```env
   WHATSAPP_APP_SECRET="1a2b3c4d5e6f7g8h9i0j"
   ```

#### Step 10: Configure Webhooks (20 min)

**Prerequisite:** Your backend must be publicly accessible via HTTPS.

**For local testing**, use [ngrok](https://ngrok.com):
```bash
ngrok http 8000
# Copy the HTTPS URL: https://abc123.ngrok.io
```

**Steps:**

1. **Generate verify token** (random string):
   ```bash
   openssl rand -hex 32
   # Outputs: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
   ```
2. **Store in `.env`:**
   ```env
   WHATSAPP_VERIFY_TOKEN="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
   ```
3. **In Meta App Dashboard**, go to WhatsApp → Configuration
4. **Click** "Edit" next to Webhook
5. **Enter details:**
   ```
   Callback URL: https://your-domain.com/webhooks/whatsapp
   Verify Token: [paste the token you generated]
   ```
6. **Click** "Verify and Save"
   - Meta will send GET request to your URL
   - Your backend must return the challenge
7. **Subscribe to webhook fields:**
   - ☑️ `messages` (incoming messages)
   - ☑️ `messaging_product` (message status updates)
8. **Click** "Subscribe"

**Test webhook:**
```bash
# Your endpoint should respond to this
curl "https://your-domain.com/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=CHALLENGE_STRING"
# Should return: CHALLENGE_STRING
```

### Environment Variables

```env
# WhatsApp Cloud API (Meta)
WHATSAPP_PHONE_NUMBER_ID="123456789012345"
WHATSAPP_BUSINESS_ACCOUNT_ID="987654321098765"
WHATSAPP_ACCESS_TOKEN="EAAGxxxxxxxxxxxxxxxxxxxxxx"
WHATSAPP_VERIFY_TOKEN="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
WHATSAPP_APP_SECRET="1a2b3c4d5e6f7g8h9i0j"
```

### Testing Your Setup

```bash
# Test 1: Send a template message
curl -X POST \
  "https://graph.facebook.com/v21.0/${WHATSAPP_PHONE_NUMBER_ID}/messages" \
  -H "Authorization: Bearer ${WHATSAPP_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "messaging_product": "whatsapp",
    "to": "919876543210",
    "type": "template",
    "template": {
      "name": "hello_world",
      "language": { "code": "en_US" }
    }
  }'

# Expected response:
# {"messaging_product":"whatsapp","contacts":[...],"messages":[{"id":"wamid.xxx"}]}
```

### Pricing (India - as of 2025)

**Conversation-based pricing:**

| Conversation Type | First 1,000/month | After 1,000/month |
|-------------------|-------------------|-------------------|
| User-initiated (customer messages you first) | **FREE** | ₹0.45 per conversation |
| Business-initiated (you message customer first) | **FREE** | ₹0.80 per conversation |
| Service (utility/transactional) | **FREE** | ₹0.32 per conversation |

**What is a conversation?**
- 24-hour window after the first message
- All messages within 24 hours = 1 conversation
- If customer/business messages after 24 hours = new conversation

**Cost examples:**
- 0-1,000 conversations/month: **₹0**
- 2,500 conversations/month: ~₹675-1,200
- 5,000 conversations/month: ~₹1,800-3,200
- 10,000 conversations/month: ~₹3,600-6,400

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Webhook verification fails | URL not public HTTPS | Use ngrok for testing, proper SSL for production |
| "Invalid phone number" error | Number already on WhatsApp | Use a NEW number, never registered with WhatsApp |
| Display name showing "Pending" | Meta reviewing | Wait 1-2 days; ensure it matches business name |
| Message send fails (code 131026) | Template not approved | Must use approved templates or reply within 24h window |
| "Insufficient permissions" | Access token missing permissions | Regenerate token with all 3 required permissions |

### Resources

- **Official Docs:** [developers.facebook.com/docs/whatsapp/cloud-api](https://developers.facebook.com/docs/whatsapp/cloud-api)
- **API Reference:** [developers.facebook.com/docs/whatsapp/cloud-api/reference](https://developers.facebook.com/docs/whatsapp/cloud-api/reference)
- **WhatsApp Business Policy:** [www.whatsapp.com/legal/business-policy](https://www.whatsapp.com/legal/business-policy)
- **Support:** Business Support team via Meta Business Suite

---

*[Due to length, I'll provide the document in a file. Let me create the complete comprehensive version...]*
