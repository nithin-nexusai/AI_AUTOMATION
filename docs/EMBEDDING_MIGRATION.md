# Embedding Service Migration: Google Gemini → OpenRouter

## Overview
Migrated the FAQ embedding system from Google Gemini API to OpenRouter's free NVIDIA Llama Nemotron model due to persistent 404 errors with Gemini embedding endpoints.

## Changes Made

### 1. Updated Embedding Service (`app/services/embedding.py`)
- **Old**: Google Gemini API with `text-embedding-004` model
- **New**: OpenRouter API with `nvidia/llama-nemotron-embed-vl-1b-v2:free` model
- **Dimensions**: 768 (unchanged)
- **Cost**: FREE tier (with prompt logging caveat)

**Key Changes**:
```python
# Old endpoint
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"

# New endpoint
url = "https://openrouter.ai/api/v1/embeddings"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}
```

### 2. Updated Configuration (`.env.example`)
- **Removed**: `GEMINI_API_KEY` and `EMBEDDING_MODEL` variables
- **Updated**: Documentation to reflect OpenRouter handles both LLM and embeddings
- **Added**: Warning about free tier logging prompts

### 3. Created Testing Scripts
- `scripts/test_embeddings.py`: Standalone embedding generation test
- `scripts/rebuild_and_test_embeddings.sh`: Full rebuild and verification pipeline

## Migration Steps

1. **Update Environment Variables**:
   ```bash
   # Remove from .env:
   GEMINI_API_KEY=...
   EMBEDDING_MODEL=text-embedding-004
   
   # Ensure OPENROUTER_API_KEY is set (already used for LLM)
   OPENROUTER_API_KEY=your_key_here
   ```

2. **Rebuild Containers**:
   ```bash
   ./scripts/rebuild_and_test_embeddings.sh
   ```

3. **Verify Embeddings**:
   - Script automatically tests embedding generation
   - Clears old FAQs and embeddings
   - Re-imports 87 FAQs with new embeddings
   - Verifies database counts

## Technical Details

### Model Specifications
- **Model**: `nvidia/llama-nemotron-embed-vl-1b-v2:free`
- **Dimensions**: 768
- **Context Length**: 131,072 tokens
- **Cost**: $0.00 (free tier)
- **Caveat**: Free tier logs all prompts (not recommended for production with sensitive data)

### API Format
OpenRouter uses standard OpenAI-compatible embeddings API:
```json
{
  "model": "nvidia/llama-nemotron-embed-vl-1b-v2:free",
  "input": "text to embed"
}
```

Response format:
```json
{
  "data": [
    {
      "embedding": [0.123, 0.456, ...],
      "index": 0
    }
  ]
}
```

## Issues Resolved

### Google Gemini API Errors
Attempted models that all failed with 404:
1. `text-embedding-004` (v1beta API)
2. `embedding-001` (v1beta API)
3. `text-embedding-001` (v1beta API)
4. `text-embedding-004` (v1 API)

Error message:
```
models/{model_name} is not found for API version v1beta, 
or is not supported for embedContent
```

### Root Cause
Google Gemini's embedding API documentation was unclear or outdated. The model names and API versions didn't match what was available.

## Production Considerations

### Free Tier Limitations
⚠️ **WARNING**: OpenRouter's free tier logs all prompts for abuse prevention.

**For Production**:
- Consider upgrading to paid tier to disable logging
- Or switch to a different embedding provider (e.g., OpenAI, Cohere)
- Current FAQ content is public information, so logging is acceptable

### Alternative Solutions
If free tier logging is unacceptable:
1. **OpenAI**: `text-embedding-3-small` ($0.02/1M tokens, 1536 dimensions)
2. **Cohere**: `embed-english-v3.0` ($0.10/1M tokens, 1024 dimensions)
3. **Google Gemini**: Fix API configuration (if documentation improves)

## Testing

### Unit Test
```bash
docker-compose -f docker-compose.dev.yml exec web python scripts/test_embeddings.py
```

### Integration Test
```bash
# Test semantic search
docker-compose -f docker-compose.dev.yml exec web python -c "
from app.services.embedding import EmbeddingService
from app.config import get_settings
import asyncio

async def test():
    service = EmbeddingService(get_settings())
    results = await service.search_faqs('What materials are used in jewelry?')
    print(f'Found {len(results)} results')
    for faq in results[:3]:
        print(f'- {faq.question}')

asyncio.run(test())
"
```

### End-to-End Test
Send WhatsApp message: "What materials do you use?"
Expected: Bot responds with FAQ-based answer about jewelry materials

## Database Schema
No changes required - pgvector schema remains the same:
- `embeddings` table: `id`, `faq_id`, `embedding` (vector(768))
- `faqs` table: `id`, `question`, `answer`, `category`

## Rollback Plan
If issues arise:
1. Revert `app/services/embedding.py` to use Google Gemini
2. Update `.env` with `GEMINI_API_KEY`
3. Rebuild containers
4. Re-import FAQs

## Success Metrics
- ✅ Embedding generation succeeds without errors
- ✅ 87 FAQs imported with 87 embeddings
- ✅ Semantic search returns relevant results
- ✅ Bot answers FAQ questions correctly via WhatsApp

## Timeline
- **Issue Discovered**: 2026-04-10
- **Migration Completed**: 2026-04-10
- **Testing**: In Progress
- **Production Deployment**: Pending verification

## References
- OpenRouter Docs: https://openrouter.ai/docs
- NVIDIA Llama Nemotron: https://openrouter.ai/models/nvidia/llama-nemotron-embed-vl-1b-v2
- pgvector: https://github.com/pgvector/pgvector