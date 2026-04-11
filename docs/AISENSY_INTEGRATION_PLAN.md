# AiSensy Integration Plan

## Current Status
- ✅ Support bot working (Meta Cloud API)
- ✅ Customer conversations functional
- ✅ FAQ system operational
- ⚠️ Templates not yet created

## Future Implementation (When Templates Are Ready)

### Architecture Overview

**Two WhatsApp Numbers**:
1. **Support Number** (Meta Cloud API) - For conversations + utility templates
2. **Marketing Number** (AiSensy) - For marketing templates

### Template Routing Strategy

| Template Type | Category | Send Via | Number |
|--------------|----------|----------|--------|
| Abandoned Cart | Marketing | AiSensy | Marketing |
| Order Confirmation | Utility | Meta Cloud API | Support |
| Shipping Update | Utility | Meta Cloud API | Support |
| OTP/Verification | Utility | Meta Cloud API | Support |

**Note**: General broadcasts (new products, sales) are done manually via AiSensy Dashboard

---

## Implementation Steps (Future)

### Step 1: Create Templates
**In WhatsApp Business Manager / AiSensy Dashboard**:
- [ ] Create abandoned cart template (marketing category)
- [ ] Create order confirmation template (utility category)
- [ ] Create shipping update template (utility category)
- [ ] Get template names and parameter structure

### Step 2: Get AiSensy Credentials
- [ ] AiSensy API key
- [ ] Campaign name
- [ ] Marketing WhatsApp number

### Step 3: Add Configuration
**File**: `chicx-bot/app/config.py`

Add after line 51:
```python
# AiSensy (for marketing templates)
aisensy_api_key: str = ""
aisensy_campaign_name: str = ""
aisensy_destination: str = ""  # Marketing WhatsApp number
```

**File**: `chicx-bot/.env.example`

Add:
```bash
# AiSensy (Marketing Templates)
AISENSY_API_KEY=your_api_key
AISENSY_CAMPAIGN_NAME=your_campaign_name
AISENSY_DESTINATION=your_marketing_number
```

### Step 4: Create AiSensy Service
**New File**: `chicx-bot/app/services/aisensy.py`

```python
"""AiSensy API client for sending marketing WhatsApp templates."""
import httpx
import logging
from typing import Any
from app.config import get_settings

logger = logging.getLogger(__name__)

class AiSensyClient:
    """Client for AiSensy WhatsApp API."""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.aisensy_api_key
        self.campaign_name = settings.aisensy_campaign_name
        self.destination = settings.aisensy_destination
        self.base_url = "https://backend.aisensy.com/campaign/t1/api/v2"
        self._http_client = None
    
    async def send_template(
        self,
        phone: str,
        template_name: str,
        template_params: list[str] | None = None,
    ) -> dict[str, Any]:
        """Send WhatsApp template via AiSensy.
        
        Args:
            phone: Recipient phone number (with country code)
            template_name: Name of the approved template
            template_params: List of parameter values for template
        
        Returns:
            API response dict
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        
        # TODO: Implement based on AiSensy API documentation
        # Typical payload structure:
        payload = {
            "apiKey": self.api_key,
            "campaignName": self.campaign_name,
            "destination": phone,
            "userName": template_name,
            "templateParams": template_params or [],
        }
        
        try:
            response = await self._http_client.post(
                f"{self.base_url}/send-template",
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"AiSensy API error: {e}")
            raise
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()

# Factory function
def get_aisensy_client() -> AiSensyClient:
    """Get AiSensy client instance."""
    return AiSensyClient()
```

### Step 5: Update WhatsApp Service
**File**: `chicx-bot/app/services/whatsapp.py`

Modify `send_template_message()` method (around line 941):

```python
async def send_template_message(
    self,
    to: str,
    template_name: str,
    template_category: str,  # NEW: "marketing" or "utility"
    language_code: str = "en",
    components: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Send template message with smart routing.
    
    Args:
        to: Recipient phone number
        template_name: Template name
        template_category: "marketing" or "utility"
        language_code: Language code (default: "en")
        components: Template parameters
    
    Returns:
        API response
    """
    if template_category == "marketing":
        # Route to AiSensy for marketing templates
        from app.services.aisensy import get_aisensy_client
        
        # Extract parameters from components
        params = []
        if components:
            for component in components:
                if component.get("type") == "body":
                    params = [p["text"] for p in component.get("parameters", [])]
        
        aisensy = get_aisensy_client()
        return await aisensy.send_template(to, template_name, params)
    else:
        # Route to Meta Cloud API for utility templates
        payload = OutboundTemplateMessage.create(
            to=to,
            template_name=template_name,
            language_code=language_code,
            components=components,
        )
        return await self._send_api_request(payload.model_dump())
```

### Step 6: Create Backend API Endpoints
**New File**: `chicx-bot/app/api/notifications.py`

```python
"""API endpoints for sending notifications."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.api.deps import get_db,get_redis
from app.services.whatsapp import get_whatsapp_service, WhatsAppChannel

router = APIRouter()

@router.post("/send-template")
async def send_template_notification(
    phone: str,
    template_name: str,
    template_category: str,  # "marketing" or "utility"
    parameters: list[str] = None,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    """Send template notification to user."""
    
    # Choose channel based on category
    channel = WhatsAppChannel.MARKETING if template_category == "marketing" else WhatsAppChannel.PRIMARY
    
    # Get WhatsApp service
    whatsapp = await get_whatsapp_service(db, redis_client, channel)
    
    # Build components
    components = []
    if parameters:
        components = [{
            "type": "body",
            "parameters": [{"type": "text", "text": param} for param in parameters]
        }]
    
    # Send template
    result = await whatsapp.send_template_message(
        to=phone,
        template_name=template_name,
        template_category=template_category,
        components=components,
    )
    
    return {"success": True, "message_id": result.get("messages", [{}])[0].get("id")}
```

### Step 7: Update Main App
**File**: `chicx-bot/app/main.py`

Add notifications router:
```python
from app.api.notifications import router as notifications_router

app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])
```

---

## Testing Plan (Future)

### Test Cases
1. **Abandoned Cart** (Marketing → AiSensy)
   ```bash
   curl -X POST "http://localhost:8000/api/notifications/send-template" \
     -H "Content-Type: application/json" \
     -d '{
       "phone": "919876543210",
       "template_name": "abandoned_cart",
       "template_category": "marketing",
       "parameters": ["John", "Gold Chain", "₹2,499"]
     }'
   ```

2. **Order Confirmation** (Utility → Meta)
   ```bash
   curl -X POST "http://localhost:8000/api/notifications/send-template" \
     -H "Content-Type: application/json" \
     -d '{
       "phone": "919876543210",
       "template_name": "order_confirmation",
       "template_category": "utility",
       "parameters": ["ORD123", "₹2,499"]
     }'
   ```

---

## Current Production Status

**Ready for Production**:
- ✅ Support bot (customer conversations)
- ✅ FAQ system (101 FAQs)
- ✅ Tool selection logic
- ✅ All critical bugs fixed

**Future Enhancements**:
- ⏳ Template creation (in progress)
- ⏳ AiSensy integration (after templates ready)
- ⏳ Backend notification endpoints

**Timeline**: Implementation can begin once templates are created and approved.