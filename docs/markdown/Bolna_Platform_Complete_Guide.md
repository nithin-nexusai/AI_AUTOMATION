# How to Create and Host Agents on Bolna AI Platform

**Last Updated:** December 15, 2025  
**Platform:** Bolna.ai Voice AI Platform

---

## 📋 Table of Contents

1. [Platform Overview](#platform-overview)
2. [Getting Started](#getting-started)
3. [Creating Agents (No-Code UI)](#creating-agents-no-code-ui)
4. [Creating Agents (API Method)](#creating-agents-api-method)
5. [Configuration Options](#configuration-options)
6. [Testing Your Agent](#testing-your-agent)
7. [Deployment](#deployment)
8. [Pricing & Plans](#pricing--plans)
9. [Advanced Features](#advanced-features)

---

## Platform Overview

### What is Bolna AI?

Bolna AI is a cloud platform for building and hosting conversational Voice AI agents that can:
- Handle inbound/outbound phone calls
- Qualify leads and perform sales calls
- Provide customer support
- Automate business processes
- Integrate with CRMs and business tools

### Architecture Components

**Bolna Voice AI Stack:**
```
Input (Voice Call)
    ↓
Transcriber (STT) → Deepgram, Azure, AssemblyAI, Sarvam
    ↓
LLM (Brain) → OpenAI, DeepSeek, Anthropic, Llama, Cohere, Mistral
    ↓
Synthesizer (TTS) → ElevenLabs, AWS Polly, OpenAI, Azure, Deepgram, Cartesia
    ↓
Output (Voice Response)
```

**Telephony Integration:**
- Twilio
- Plivo
- Exotel (coming soon)
- Vonage (coming soon)

---

## Getting Started

### Step 1: Sign Up

**Platform URL:** https://platform.bolna.ai/

1. Go to https://bolna.ai or https://platform.bolna.ai
2. Click "Sign Up" or "Get Started"
3. Choose your plan:
   - **Free Trial:** Explore basic features
   - **Starter:** $100 for 1,000 minutes
   - **Growth:** $250 for 4,000 minutes
   - **Pilot:** $500 for 10,000 minutes (recommended)
   - **Enterprise:** Custom pricing

4. Complete email verification
5. Login to dashboard

### Step 2: Get API Credentials (if using API)

1. Navigate to **Developers** tab in dashboard
2. Click **Generate API Key**
3. Copy and save the API key securely
4. Format: `Authorization: Bearer YOUR_API_KEY`

---

## Creating Agents (No-Code UI)

### Access the Playground

**URL:** https://playground.bolna.dev/dashboard

The Bolna Playground is a visual, no-code interface for creating agents.

### Step-by-Step Agent Creation

#### 1. Create New Agent

**In Dashboard:**
1. Click **"Create Agent"** button
2. Choose one of:
   - **Create from scratch** - Build custom agent
   - **Import from Library** - Use pre-built template
   - **Clone existing** - Duplicate an agent

#### 2. Configure Agent Settings

**Agents Tab** - Define core identity:

```yaml
# Basic Configuration
Agent Name: "CHICX Voice Assistant"
Agent Type: "customer_service" (or sales, support, etc.)
Description: "Voice AI for CHICX fashion e-commerce"
```

#### 3. Set Agent Prompt

**This is the agent's "personality" and instructions.**

**Example Prompt:**
```
You are a friendly and helpful voice assistant for CHICX, an online fashion store 
specializing in sarees, kurtis, and traditional Indian clothing.

Your responsibilities:
- Answer customer questions about products
- Help customers find products based on their preferences
- Check order status and provide shipping updates
- Answer FAQs about returns, exchanges, and policies

Tone: Warm, professional, and conversational
Language: Primarily English, with Hindi support

Keep responses concise (2-3 sentences max) since this is a voice conversation.
Always confirm important details by repeating them back to the customer.

If you don't know something, politely tell the customer you'll connect them 
with a human agent.
```

**Pro Tips for Prompts:**
- Use Bolna's Custom GPT tool to refine prompts
- Keep instructions clear and concise
- Define tone and personality
- Set boundaries (what agent can/cannot do)
- Include example conversations

#### 4. Configure LLM (Language Model)

**LLM Tab Options:**

| Provider | Model | Best For | Cost |
|----------|-------|----------|------|
| **OpenAI** | GPT-4, GPT-3.5-turbo | General purpose | Medium-High |
| **DeepSeek** | deepseek-chat | Cost-effective, good quality | Low |
| **Anthropic** | Claude-3 | Complex reasoning | High |
| **Llama** | Llama-3 | Open source, flexible | Low-Medium |
| **Mistral** | Mistral-7B | Fast, efficient | Low |

**Recommended for CHICX:** DeepSeek (cost-effective)

**Settings:**
```yaml
Provider: DeepSeek
Model: deepseek-chat
Temperature: 0.7  # Balance between creative and consistent
Max Tokens: 150  # Keep responses short for voice
```

#### 5. Configure Voice (TTS - Text-to-Speech)

**Voices Tab Options:**

| Provider | Quality | Languages | Cost |
|----------|---------|-----------|------|
| **ElevenLabs** | Premium | Multi-lingual | High |
| **AWS Polly** | Good | 60+ languages | Low |
| **Azure** | Good | 75+ languages | Medium |
| **OpenAI** | Good | Multi-lingual | Medium |
| **Deepgram** | Good | English focus | Low |
| **Cartesia** | Good | Multi-lingual | Medium |

**Recommended:** ElevenLabs for best quality

**Voice Selection:**
```yaml
Provider: ElevenLabs
Voice ID: "21m00Tcm4TlvDq8ikWAM"  # Rachel - warm female voice
Model: "eleven_multilingual_v2"  # Supports Hindi
Stability: 0.5
Similarity Boost: 0.75
Style: 0.5
```

**For Indian Languages:**
- Choose multilingual models
- Test with Hindi/Tamil phrases

#### 6. Configure Transcriber (STT - Speech-to-Text)

**Transcriber Tab Options:**

| Provider | Accuracy | Languages | Cost |
|----------|----------|-----------|------|
| **Deepgram** | Excellent | 36+ languages | Low |
| **Azure** | Excellent | 90+ languages | Medium |
| **AssemblyAI** | Very Good | English focus | Medium |
| **Sarvam** | Good | Indian languages |Low |

**Recommended:** Deepgram Nova-2

**Settings:**
```yaml
Provider: Deepgram
Model: nova-2  # Best accuracy
Language: en  # Primary language
Stream: true
Endpointing: 400  # Silence detection (ms)
Keywords:
  - "CHICX:5"
  - "saree:3"
  - "kurti:3"
  - "order:3"
```

#### 7. Set Welcome Message

**First thing agent says when call connects:**

```
Welcome Message: "Hello! Welcome to CHICX. How can I help you today?"

# For outbound calls:
Outbound Message: "Hi, this is Sarah calling from CHICX. Is this a good time to chat about your recent order?"
```

#### 8. Add Variables (Personalization)

**Variables Tab:**

Use variables to personalize conversations:

```yaml
Variables:
  {name}: "Customer's first name"
  {order_id}: "Order number"
  {tracking_number}: "Shipping tracking"
  {order_status}: "Current order status"
```

**In Prompt:**
```
Welcome {name}! I see you're calling about order {order_id}. 
Let me check the status for you.
```

#### 9. Add Functions (Tool Calling)

**Functions Tab** - Enable agent to perform actions

**Example Functions:**

**a) Search Products:**
```json
{
  "name": "search_products",
  "description": "Search for products in CHICX catalog",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query (e.g., 'red saree', 'cotton kurti')"
      },
      "category": {
        "type": "string",
        "description": "Product category filter",
        "enum": ["sarees", "kurtis", "lehengas", "all"]
      },
      "min_price": {
        "type": "number",
        "description": "Minimum price in INR"
      },
      "max_price": {
        "type": "number",
        "description": "Maximum price in INR"
      }
    },
    "required": ["query"]
  },
  "webhook_url": "https://your-backend.com/webhooks/bolna/tool"
}
```

**b) Get Order Status:**
```json
{
  "name": "get_order_status",
  "description": "Check status of customer order",
  "parameters": {
    "type": "object",
    "properties": {
      "order_id": {
        "type": "string",
        "description": "Order ID (e.g., ORD123456)"
      }
    },
    "required": ["order_id"]
  },
  "webhook_url": "https://your-backend.com/webhooks/bolna/tool"
}
```

**c) Search FAQ:**
```json
{
  "name": "search_faq",
  "description": "Search FAQ knowledge base",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Customer's question"
      }
    },
    "required": ["query"]
  },
  "webhook_url": "https://your-backend.com/webhooks/bolna/tool"
}
```

**Webhook Response Format:**
```json
{
  "result": {
    "success": true,
    "data": {
      // Your tool's response data
    },
    "message": "Human-readable summary for agent to speak"
  }
}
```

#### 10. Configure Webhooks

**Webhooks Tab:**

Set up endpoints to receive call data:

```yaml
Webhook Secret: <generate_strong_random_secret>

Webhook URLs:
  Transcript: https://your-backend.com/webhooks/bolna/transcript
  Tool Call: https://your-backend.com/webhooks/bolna/tool
  Call Complete: https://your-backend.com/webhooks/bolna/call-complete
```

**Webhook Events:**
- `transcript` - Real-time speech-to-text results
- `tool_call` - When agent needs to execute a function
- `call_complete` - When call ends (full transcript, duration, status)

#### 11. Save Agent

**Important:** Click **"Save Agent"** after every change!

Changes only take effect after saving.

---

## Creating Agents (API Method)

For programmatic control, use the Bolna API.

### Authentication

```bash
# Include in all requests
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

### Create Agent via API

**Endpoint:** `POST https://api.bolna.dev/v1/agents`

**Request Body:**
```json
{
  "agent_config": {
    "agent_name": "CHICX Voice Assistant",
    "agent_welcome_message": "Hello! Welcome to CHICX. How can I help you today?",
    "webhook_url": "https://your-backend.com/webhooks/bolna",
    "tasks": [
      {
        "task_type": "conversation",
        "toolchain": {
          "execution": "parallel",
          "pipelines": ["transcriber", "llm", "synthesizer"]
        },
        "tools_config": {
          "input": {
            "provider": "twilio",
            "stream": true
          },
          "output": {
            "provider": "twilio",
            "format": "pcm",
            "sample_rate": 8000
          },
          "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en",
            "stream": true,
            "endpointing": 400
          },
          "llm": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "max_tokens": 150,
            "temperature": 0.7,
            "request_json": true
          },
          "synthesizer": {
            "provider": "elevenlabs",
            "voice_id": "21m00Tcm4TlvDq8ikWAM",
            "model": "eleven_multilingual_v2",
            "stream": true
          }
        }
      }
    ]
  },
  "agent_prompts": {
    "task_1": {
      "system_prompt": "You are a friendly voice assistant for CHICX..."
    }
  }
}
```

**Response:**
```json
{
  "agent_id": "uuid-agent-id",
  "agent_name": "CHICX Voice Assistant",
  "created_at": "2025-12-15T13:00:00Z",
  "status": "active"
}
```

### Update Agent

**Endpoint:** `PATCH https://api.bolna.dev/v1/agents/{agent_id}`

### Delete Agent

**Endpoint:** `DELETE https://api.bolna.dev/v1/agents/{agent_id}`

### List All Agents

**Endpoint:** `GET https://api.bolna.dev/v1/agents`

---

## Testing Your Agent

### 1. Chat Testing (Text Mode)

**In Playground:**
1. Go to **Agent** tab
2. Find **"Test Chat"** panel on right
3. Type messages to test agent responses
4. Refine prompt based on results

**Benefits:**
- Fast iteration
- No call costs
- Easy debugging

### 2. Voice Testing (Call Mode)

**Outbound Test Call:**
1. Go to **Test** tab in Playground
2. Enter test phone number (your mobile)
3. Click **"Initiate Call"**
4. Answer phone and test conversation

**What to Test:**
- ✅ Greeting message
- ✅ Speech recognition accuracy
- ✅ LLM understanding
- ✅ Response quality (tone, content)
- ✅ Function calling (if configured)
- ✅ Voice quality and naturalness
- ✅ Handling of interruptions
- ✅ Error handling

### 3. Monitor Executions

**Agent Executions Tab:**
- View all past calls
- See call duration
- Read full transcripts
- Check function calls made
- Review errors

**Metrics to Monitor:**
- Call success rate
- Average call duration
- Function call success
- Customer satisfaction indicators

---

## Deployment

### Option 1: Inbound Calls (Receive Calls)

**Setup:**
1. Get a phone number from telephony provider (Twilio/Plivo)
2. In provider dashboard, set webhook URL:
   ```
   https://api.bolna.dev/v1/inbound/{agent_id}
   ```
3. Customers call this number
4. Bolna agent answers automatically

**Twilio Example:**
```
Voice Webhook: https://api.bolna.dev/v1/inbound/your-agent-id
HTTP Method: POST
```

### Option 2: Outbound Calls (Make Calls)

#### Via Playground:
1. Go to **Test** tab
2. Enter recipient number
3. Click "Make Call"

#### Via API:
**Endpoint:** `POST https://api.bolna.dev/v1/call`

```json
{
  "agent_id": "your-agent-id",
  "recipient_phone": "+919876543210",
  "variables": {
    "name": "Rahul",
    "order_id": "ORD123456"
  }
}
```

### Option 3: Batch Campaigns

**For calling multiple numbers:**

1. Go to **Batches** tab
2. Upload CSV with phone numbers and variables:
   ```csv
   phone,name,order_id
   +919876543210,Rahul,ORD123
   +919123456789,Priya,ORD456
   ```
3. Select agent
4. Schedule campaign
5. Monitor results

### Option 4: Agent Sharing

**Share agent via link:**
1. Go to agent settings
2. Click **"Generate Share Link"**
3. Share link: `https://platform.bolna.ai/agents/share/{unique_id}`
4. Recipients can test/use agent

---

## Pricing & Plans

### Cost Components

Bolna pricing has 3 parts:

**1. Voice AI Costs (Variable):**
- **STT (Speech-to-Text):** ~$0.05 per minute (Deepgram)
- **LLM (Language Model):** ~$0.02-0.10 per minute (depends on model)
- **TTS (Text-to-Speech):** ~$0.03 per minute (ElevenLabs)

**2. Telephony Costs:**
- **Twilio/Plivo:** ~$0.01-0.05 per minute (varies by region)

**3. Bolna Platform Fee:**
- **$0.02 per minute** (flat fee)

**Total Estimated Cost:**
- **~$0.06-0.15 per minute** for standard configuration
- **~$5-15 per 100 minutes**

### Pricing Plans

| Plan | Price | Minutes | Per-Minute Cost | Includes |
|------|-------|---------|-----------------|----------|
| **Free Trial** | $0 | Limited | - | Basic features, testing |
| **Starter** | $100 | 1,000 | $0.10 | Good for small projects |
| **Growth** | $250 | 4,000 | $0.063 | For established teams |
| **Pilot** | $500 | 10,000 | $0.05 | Market-ready agent, analytics, API |
| **Enterprise** | Custom | Custom | Custom | Dedicated support, SLA |

### Indian Rupee Conversion (1 USD = ₹86)

| Plan | Price (INR) | Minutes | Per-Minute Cost (INR) |
|------|-------------|---------|----------------------|
| **Starter** | ₹8,600 | 1,000 | ₹8.60 |
| **Growth** | ₹21,500 | 4,000 | ₹5.40 |
| **Pilot** | ₹43,000 | 10,000 | ₹4.30 |

**For 100 voice calls (3 min each = 300 min/month):**
- **Pilot Plan:** ₹43,000 / 10,000 × 300 = ~₹1,290/month
- **Plus** your own API costs (DeepSeek, ElevenLabs, etc.)

### Cost Optimization Tips

1. **Use cost-effective providers:**
   - LLM: DeepSeek instead of GPT-4
   - TTS: AWS Polly instead of ElevenLabs
   - STT: Deepgram (already low-cost)

2. **Bring your own API keys:**
   - Connect your own OpenAI/DeepSeek account
   - Pay providers directly
   - Only pay Bolna platform fee ($0.02/min)

3. **Optimize conversations:**
   - Keep responses concise
   - Limit max_tokens (fewer LLM costs)
   - End calls efficiently

4. **Monitor usage:**
   - Set up billing alerts
   - Track per-call costs
   - Identify expensive calls

---

## Advanced Features

### 1. No-Code Integrations

**Connect with:**
- **Zapier** - Automate workflows
- **Make.com** - Visual automation
- **n8n.io** - Self-hosted automation
- **viaSocket** - Integration platform

**Use Cases:**
- Sync call data to Google Sheets
- Create CRM records after calls
- Send SMS/email follow-ups
- Trigger Slack notifications

### 2. Custom Workflows

**Pre-call, during-call, post-call automation:**

Example: Post-call workflow
```
Call Ends 
  → Extract transcript
  → Summarize with AI
  → Create CRM entry
  → Send follow-up email
  → Notify sales team
```

### 3. Analytics Dashboard

**Track:**
- Call volume (daily/weekly/monthly)
- Success rate
- Average duration
- Peak hours
- Function call usage
- Cost per call
- Conversation outcomes

### 4. Multi-language Support

**Configure language detection:**
```yaml
Language:
  Default: "en"
  Supported: ["en", "hi", "ta", "te"]
  Auto Detect: true
```

**Agent responds in detected language.**

### 5. Transfer to Human

**Escalation triggers:**
```yaml
Escalation:
  Keywords:
    - "speak to human"
    - "customer service"
    - "manager"
  Max Failed Responses: 3
  Transfer Number: "+911234567890"
```

### 6. Sentiment Analysis

**Track customer emotion:**
- Positive, Neutral, Negative
- Adjust agent responses
- Flag unhappy customers

### 7. Call Recording & Compliance

**Settings:**
```yaml
Recording:
  Enabled: true
  Consent Message: "This call will be recorded for quality assurance."
  Storage: S3, Azure Blob, Google Cloud Storage
  Retention: 90 days
```

---

## Best Practices

### 1. Prompt Engineering

✅ **Do:**
- Be specific and clear
- Define tone and personality
- Include examples
- Set boundaries
- Test and iterate

❌ **Don't:**
- Make prompts too long
- Include contradictory instructions
- Assume agent knows context
- Skip testing

### 2. Voice Selection

- Test multiple voices with real users
- Choose warm, friendly voices for customer service
- Professional voices for business calls
- Match voice to brand personality

### 3. Function Calling

- Keep function names descriptive
- Provide clear parameter descriptions
- Handle errors gracefully
- Return human-readable responses
- Test all edge cases

### 4. Testing

- Test with real phone numbers
- Try different accents
- Test background noise scenarios
- Simulate interruptions
- Test all conversation paths

### 5. Monitoring

- Review transcripts regularly
- Track failure patterns
- Monitor costs daily
- Set up alerts for anomalies
- Gather user feedback

---

## Troubleshooting

### Common Issues

**1. Agent doesn't respond:**
- Check LLM configuration
- Verify API keys are valid
- Check webhook URLs are accessible
- Review prompt for clarity

**2. Poor speech recognition:**
- Switch to better STT provider (Deepgram Nova-2)
- Add keywords to configuration
- Adjust endpointing settings
- Test in quiet environment

**3. Unnatural voice:**
- Try different TTS provider/voice
- Adjust stability and similarity settings
- Use multilingual models for Indian languages
- Keep responses shorter and more conversational

**4. Functions not executing:**
- Check webhook endpoint is public and HTTPS
- Verify webhook secret matches
- Check function parameter schema
- Review webhook logs for errors

**5. High costs:**
- Review per-call analytics
- Switch to cheaper providers
- Optimize LLM token usage
- Set max call duration

---

## Next Steps for CHICX

### Recommended Setup:

**Platform:** Bolna Pilot Plan ($500 / ₹43,000)

**Configuration:**
```yaml
Agent Name: "CHICX Voice Assistant"
Language: en (with Hindi support)

LLM: DeepSeek deepseek-chat
TTS: ElevenLabs (Rachel voice, multilingual)
STT: Deepgram Nova-2

Functions:
  - search_products
  - get_order_status
  - get_order_history
  - search_faq

Telephony: Exotel (when available) or Twilio

Webhooks: Point to your CHICX backend
```

### Integration Steps:

1. ✅ Create Bolna account (Pilot plan)
2. ✅ Create agent in Playground
3. ✅ Upload your agent_config.yaml
4. ✅ Configure environment variables
5. ✅ Set up webhooks to your backend
6. ✅ Test with sample calls
7. ✅ Deploy to production
8. ✅ Monitor and optimize

---

## Resources

**Official Links:**
- Platform: https://platform.bolna.ai
- Documentation: https://docs.bolna.ai
- API Docs: https://api.bolna.dev/docs
- GitHub: https://github.com/bolna-ai
- Support: support@bolna.dev

**Community:**
- Discord: https://discord.gg/bolna
- YouTube: Bolna AI tutorials
- Blog: https://bolna.ai/blog

---

**Guide Version:** 1.0  
**Created:** December 15, 2025  
**For:** CHICX AI Platform Migration
