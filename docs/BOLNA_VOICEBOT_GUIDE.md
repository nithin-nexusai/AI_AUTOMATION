# CHICX Bolna Voicebot Complete Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phone Verification](#phone-verification)
4. [Testing Guide](#testing-guide)
5. [Troubleshooting](#troubleshooting)
6. [Production Deployment](#production-deployment)

---

## Overview

This guide covers the complete setup, testing, and deployment of the CHICX Bolna voicebot integration. The system enables customers to interact with CHICX via phone calls, with AI-powered responses and tool execution.

### System Architecture
- **Bolna Platform**: Manages voice calls and AI agent
- **Backend API**: Executes tools (FAQ search, product search, order tracking)
- **Database**: Stores call records, transcripts, and conversation history
- **ngrok**: Exposes local development server to Bolna webhooks

### Key Components
- **Agent ID**: `0820a548-2aa5-4626-b29c-dba50fd7d5ec`
- **API Key**: `bn-660f0d28f61e4e3bae814c5f8b83a129`
- **Webhook URL**: `https://lady-potentiometric-gilbert.ngrok-free.dev/webhooks/bolna/call-complete`
- **Tool Endpoint**: `https://lady-potentiometric-gilbert.ngrok-free.dev/webhooks/bolna/tool`

---

## Prerequisites

### ✅ Completed Setup
- [x] Database migrations applied
- [x] 87 FAQs imported with embeddings
- [x] Docker containers running
- [x] ngrok tunnel active
- [x] Bolna dashboard configured
- [x] All 6 tools configured with `custom_task` key

### Environment Configuration
```bash
# chicx-bot/.env
BOLNA_API_KEY=bn-660f0d28f61e4e3bae814c5f8b83a129
BOLNA_AGENT_ID=0820a548-2aa5-4626-b29c-dba50fd7d5ec
BOLNA_WEBHOOK_SECRET=your_bolna_webhook_secret
```

### Tool Configurations
All 6 tools configured in Bolna with:
- **URL**: `https://lady-potentiometric-gilbert.ngrok-free.dev/webhooks/bolna/tool`
- **Key**: `custom_task` (required by Bolna)
- **Headers**: 
  - `Content-Type: application/json`
  - `X-Bolna-Secret: your_bolna_webhook_secret`

**Available Tools:**
1. `search_faq` - Search knowledge base
2. `search_products` - Browse product catalog
3. `get_product_details` - Get specific product info
4. `get_order_status` - Track order status
5. `get_order_history` - View past orders
6. `escalate_to_human` - Transfer to human agent

---

## Phone Verification

### Issue: Trial Account Restriction
```json
{
  "message": "Trial accounts can only make calls to verified phone numbers."
}
```

### Solution Steps

#### 1. Access Bolna Dashboard
1. Go to https://app.bolna.dev/
2. Log in with your credentials

#### 2. Verify Phone Number
1. Navigate to **Settings** → **Phone Verification**
2. Click **Add Phone Number**
3. Enter: `+919344063248`
4. Click **Send Verification Code**
5. Enter the SMS code received
6. Click **Verify**

#### 3. Alternative: Use Dashboard for Calls
If API calls are restricted:
1. Go to **Agents** section
2. Select agent: `0820a548-2aa5-4626-b29c-dba50fd7d5ec`
3. Click **Test Call** or **Make Call**
4. Enter verified phone number
5. Click **Start Call**

#### 4. Upgrade to Paid Plan (Optional)
For unrestricted calling:
1. Go to **Billing** → **Upgrade**
2. Choose a paid plan
3. Add payment method
4. Complete upgrade

---

## Testing Guide

### 1. Verify System Health

```bash
# Check application health
curl https://lady-potentiometric-gilbert.ngrok-free.dev/webhooks/bolna/health

# Expected response:
# {"status":"ok","service":"bolna-webhook"}
```

### 2. Test Individual Tools

#### Test FAQ Search (Working with Real Data)
```bash
curl -X POST https://lady-potentiometric-gilbert.ngrok-free.dev/webhooks/bolna/tool \
  -H "Content-Type: application/json" \
  -H "X-Bolna-Secret: your_bolna_webhook_secret" \
  -d '{
    "call_id": "test-call-001",
    "tool_name": "search_faq",
    "arguments": {"query": "return policy"}
  }'

# Expected: Returns FAQ answer about returns
```

#### Test Product Search
```bash
curl -X POST https://lady-potentiometric-gilbert.ngrok-free.dev/webhooks/bolna/tool \
  -H "Content-Type: application/json" \
  -H "X-Bolna-Secret: your_bolna_webhook_secret" \
  -d '{
    "call_id": "test-call-002",
    "tool_name": "search_products",
    "arguments": {"query": "gold chain"}
  }'

# Note: Requires CHICX API configuration
```

#### Test Order Status
```bash
curl -X POST https://lady-potentiometric-gilbert.ngrok-free.dev/webhooks/bolna/tool \
  -H "Content-Type: application/json" \
  -H "X-Bolna-Secret: your_bolna_webhook_secret" \
  -d '{
    "call_id": "test-call-003",
    "tool_name": "get_order_status",
    "user_phone": "+919876543210",
    "arguments": {"order_id": "ORD123"}
  }'

# Note: Requires Shiprocket configuration
```

### 3. Make a Test Call

#### Option A: Using Bolna Dashboard
1. Go to Bolna Dashboard → Agents
2. Select your agent: `0820a548-2aa5-4626-b29c-dba50fd7d5ec`
3. Click "Test Call" or "Make Call"
4. Enter verified phone number: `+919344063248`
5. Start the call

#### Option B: Using Bolna API
```bash
curl -X POST https://api.bolna.dev/call \
  -H "Authorization: Bearer bn-660f0d28f61e4e3bae814c5f8b83a129" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "0820a548-2aa5-4626-b29c-dba50fd7d5ec",
    "recipient_phone_number": "+919344063248"
  }'
```

### 4. Test Conversation Flows

#### Flow 1: FAQ Query
**User**: "What is your return policy?"  
**Expected**: Bot searches FAQ and provides return policy details

#### Flow 2: Product Search
**User**: "Show me gold chains"  
**Expected**: Bot searches products and lists available gold chains

#### Flow 3: Order Tracking
**User**: "Track my order ORD123"  
**Expected**: Bot asks for phone number (if not provided) and tracks order

#### Flow 4: Human Escalation
**User**: "I want to talk to a human"  
**Expected**: Bot transfers to human agent

### 5. Monitor Call Logs

```bash
# Terminal 1: Watch application logs
docker-compose -f chicx-bot/docker-compose.dev.yml logs -f app

# Terminal 2: Monitor tool calls
docker-compose -f chicx-bot/docker-compose.dev.yml logs app | grep "Bolna tool call"

# Check for errors
docker-compose -f chicx-bot/docker-compose.dev.yml logs app | grep "ERROR"
```

### 6. Verify Database Records

```bash
# Check calls table
docker-compose -f chicx-bot/docker-compose.dev.yml exec db psql -U chicx -c "
SELECT 
  id, 
  phone, 
  bolna_call_id, 
  status, 
  duration_seconds,
  started_at
FROM calls 
ORDER BY started_at DESC 
LIMIT 5;
"

# Check transcripts
docker-compose -f chicx-bot/docker-compose.dev.yml exec db psql -U chicx -c "
SELECT 
  call_id, 
  LEFT(transcript, 100) as transcript_preview 
FROM call_transcripts 
ORDER BY created_at DESC 
LIMIT 3;
"

# Check conversations
docker-compose -f chicx-bot/docker-compose.dev.yml exec db psql -U chicx -c "
SELECT 
  id, 
  user_id, 
  channel, 
  status 
FROM conversations 
ORDER BY created_at DESC 
LIMIT 5;
"
```

### 7. Expected Call Flow

#### 1. Call Initiation
```
[System] Dialing +919344063248...
[System] Call connected
[Agent] "Hello! Welcome to CHICX. How can I help you today?"
```

#### 2. User Query
```
[You] "What is your return policy?"
[System] Executing tool: search_faq
[Agent] "We offer easy returns for eligible products..."
```

#### 3. Follow-up
```
[You] "Show me gold chains"
[System] Executing tool: search_products
[Agent] "Let me search our collection for you..."
```

#### 4. Call End
```
[You] "Thank you"
[Agent] "You're welcome! Have a great day!"
[System] Call ended - Duration: 2m 34s
```

---

## Troubleshooting

### Issue: Tool Not Executing

**Symptoms:**
- Tool calls fail silently
- No response from backend
- Timeout errors

**Check:**
1. Tool name matches exactly (case-sensitive)
2. `X-Bolna-Secret` header is correct
3. Tool is configured in Bolna dashboard
4. Arguments format is correct

**Solution:**
```bash
# Test tool directly
curl -X POST https://lady-potentiometric-gilbert.ngrok-free.dev/webhooks/bolna/tool \
  -H "Content-Type: application/json" \
  -H "X-Bolna-Secret: your_bolna_webhook_secret" \
  -d '{"call_id":"test","tool_name":"search_faq","arguments":{"query":"test"}}'
```

### Issue: Webhook Not Received

**Symptoms:**
- Call completes but no database record
- No webhook logs in application

**Check:**
1. ngrok is still running
2. Webhook URL in Bolna is correct
3. Network connectivity

**Solution:**
```bash
# Restart ngrok
ngrok http 8000

# Update Bolna webhook URL with new ngrok URL
# Go to Bolna Dashboard → Agent Settings → Webhook URL
```

### Issue: FAQ Not Found

**Symptoms:**
- Bot says "I don't have information about that"
- Empty FAQ results

**Check:**
1. Embeddings are generated
2. Query is clear and specific

**Solution:**
```bash
# Verify embeddings count
docker-compose -f chicx-bot/docker-compose.dev.yml exec db psql -U chicx -c "
SELECT COUNT(*) FROM embeddings;
"
# Should show 87 embeddings

# Regenerate embeddings if needed
docker-compose -f chicx-bot/docker-compose.dev.yml exec app python scripts/generate_embeddings.py
```

### Issue: Authentication Failed

**Symptoms:**
- 401 Unauthorized errors
- "Invalid secret" messages

**Check:**
1. `X-Bolna-Secret` header is present
2. Secret matches `.env` file value

**Solution:**
```bash
# Check current secret
grep BOLNA_WEBHOOK_SECRET chicx-bot/.env

# Test with correct secret
curl -H "X-Bolna-Secret: your_bolna_webhook_secret" ...
```

### Issue: Verification Code Not Received

**Symptoms:**
- No SMS received for phone verification
- Cannot verify phone number

**Solution:**
1. Check SMS inbox and spam folder
2. Try alternative verification method (email/WhatsApp)
3. Wait 5 minutes and request new code
4. Contact Bolna support: support@bolna.dev

### Issue: Call Connects But No Audio

**Symptoms:**
- Call connects but silent
- Cannot hear agent

**Solution:**
1. Check phone volume settings
2. Check network connection quality
3. Try calling again
4. Check Bolna agent voice configuration

### Issue: Tools Not Executing During Call

**Symptoms:**
- Agent responds but doesn't use tools
- Generic responses instead of specific data

**Solution:**
1. Check webhook URL is correct in Bolna
2. Verify ngrok is still running
3. Check application logs for errors
4. Test tools directly via curl
5. Verify tool configurations in Bolna dashboard

---

## Production Deployment

### 1. Domain Setup
- [ ] Register production domain
- [ ] Configure DNS records
- [ ] Set up SSL certificates
- [ ] Update Bolna webhook URLs

### 2. Environment Configuration
```bash
# Production .env
BOLNA_API_KEY=<production_key>
BOLNA_AGENT_ID=<production_agent_id>
BOLNA_WEBHOOK_SECRET=<strong_random_secret>
CHICX_API_KEY=<production_api_key>
SHIPROCKET_EMAIL=<production_email>
SHIPROCKET_PASSWORD=<production_password>
```

### 3. External API Configuration
- [ ] Add CHICX API key to `.env`
- [ ] Add Shiprocket credentials to `.env`
- [ ] Test product search with real data
- [ ] Test order tracking with real orders

### 4. Performance Optimization
- [ ] Enable Redis caching
- [ ] Optimize database queries
- [ ] Add connection pooling
- [ ] Set up CDN for static assets

### 5. Monitoring & Alerting
- [ ] Set up error tracking (Sentry)
- [ ] Configure log aggregation
- [ ] Set up uptime monitoring
- [ ] Create alerting rules
- [ ] Monitor response times
- [ ] Track success rates

### 6. Performance Metrics

**Target Response Times:**
- FAQ search: < 1 second
- Product search: < 2 seconds
- Order tracking: < 3 seconds

**Target Success Rates:**
- Tool execution: > 95%
- FAQ retrieval: > 90%
- Call completion: > 98%

### 7. Database Performance Monitoring
```bash
# Check query performance
docker-compose -f chicx-bot/docker-compose.dev.yml exec db psql -U chicx -c "
SELECT 
  schemaname,
  tablename,
  n_tup_ins as inserts,
  n_tup_upd as updates,
  n_tup_del as deletes
FROM pg_stat_user_tables
ORDER BY n_tup_ins DESC;
"
```

---

## Quick Reference

### Important URLs
- **Bolna Dashboard**: https://app.bolna.dev/
- **Bolna API**: https://api.bolna.dev/
- **Bolna Docs**: https://docs.bolna.dev/
- **ngrok URL**: https://lady-potentiometric-gilbert.ngrok-free.dev

### Key Identifiers
- **Agent ID**: `0820a548-2aa5-4626-b29c-dba50fd7d5ec`
- **API Key**: `bn-660f0d28f61e4e3bae814c5f8b83a129`
- **Test Phone**: `+919344063248`

### Quick Commands
```bash
# Restart services
docker-compose -f chicx-bot/docker-compose.dev.yml restart

# View real-time logs
docker-compose -f chicx-bot/docker-compose.dev.yml logs -f

# Check service status
docker-compose -f chicx-bot/docker-compose.dev.yml ps

# Access database
docker-compose -f chicx-bot/docker-compose.dev.yml exec db psql -U chicx

# Test system health
curl https://lady-potentiometric-gilbert.ngrok-free.dev/webhooks/bolna/health
```

### Related Documentation
- **API Reference**: `docs/API_REFERENCE.md`
- **Backend Integration**: `docs/BACKEND_INTEGRATION_GUIDE.md`
- **WhatsApp Templates**: `docs/markdown/WHATSAPP_TEMPLATES.md`
- **Bolna Platform Guide**: `docs/markdown/Bolna_Platform_Complete_Guide.md`

---

## Support

### Bolna Support
- **Email**: support@bolna.dev
- **Documentation**: https://docs.bolna.dev/
- **Status Page**: https://status.bolna.dev/

### System Logs
```bash
# Application logs
docker-compose -f chicx-bot/docker-compose.dev.yml logs app

# Database logs
docker-compose -f chicx-bot/docker-compose.dev.yml logs db

# Redis logs
docker-compose -f chicx-bot/docker-compose.dev.yml logs redis
```

---

**Ready to Test!** 🚀

Your Bolna voicebot system is fully configured and ready for testing. Start by verifying your phone number, then make test calls to validate the complete flow.