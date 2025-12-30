# Bolna Self-Hosted Configuration Archive

**Archived Date:** December 15, 2025  
**Reason:** Migrated from self-hosted Bolna to Bolna managed platform

## What's Archived

- `agent_config.yaml` - Bolna voice agent configuration (now managed in Bolna dashboard)

## Migration Details

**From:** Self-hosted Bolna (http://localhost:5001)  
**To:** Bolna managed platform (https://api.bolna.dev)

## How to Restore (if needed)

If you need to rollback to self-hosted:

1. Copy `agent_config.yaml` back to `chicx-bot/bolna/`
2. Update `.env`:
   ```bash
   BOLNA_BASE_URL=http://localhost:5001
   BOLNA_API_KEY=your_self_generated_key
   ```
3. Deploy Bolna locally using Docker:
   ```bash
   cd chicx-bot/bolna
   docker run -d -p 5001:5001 \
     -v $(pwd)/agent_config.yaml:/app/config.yaml \
     bolna/bolna:latest
   ```

## Cost Comparison

- **Self-hosted:** ₹830/month (DigitalOcean Droplet)
- **Managed platform:** ₹17,000-43,000/month ($200-500)

## Reference

See migration guide: `docs/Bolna_Migration_Guide.md`
