"""Script to configure Bolna agent with webhook integration.

This script creates or updates a Bolna agent to use our custom
LLM orchestration via webhooks instead of Bolna's tool calling.

Usage:
    python scripts/configure_bolna_agent.py [--agent-id AGENT_ID]
    
    If --agent-id is provided, updates existing agent.
    Otherwise, creates a new agent.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.services.bolna import get_bolna_client
from app.core.prompts import get_system_prompt


async def configure_agent(agent_id: str | None = None):
    """Configure Bolna agent with webhook integration.
    
    Args:
        agent_id: Optional existing agent ID to update
    """
    settings = get_settings()
    
    # Use production webhook URL
    webhook_url = "https://bot.thechicx.com/webhooks/bolna/conversation"
    
    # Get system prompt for voice
    system_prompt = get_system_prompt("voice")
    
    print("=" * 80)
    print("Configuring Bolna Agent")
    print("=" * 80)
    print(f"Agent Name: CHICX Voice Assistant")
    print(f"Webhook URL: {webhook_url}")
    print(f"Agent ID: {agent_id or 'New agent will be created'}")
    print(f"System Prompt Length: {len(system_prompt)} characters")
    print("=" * 80)
    
    # Confirm
    response = input("\nProceed with configuration? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Configuration cancelled.")
        return
    
    # Configure agent
    try:
        bolna_client = get_bolna_client()
        
        result = await bolna_client.create_or_update_agent(
            agent_name="CHICX Voice Assistant",
            system_prompt=system_prompt,
            webhook_url=webhook_url,
            agent_id=agent_id,
        )
        
        print("\n✅ Agent configured successfully!")
        print(f"Agent ID: {result['agent_id']}")
        print(f"Status: {result['status']}")
        print("\nNext steps:")
        print("1. Save the Agent ID to your .env file:")
        print(f"   BOLNA_CONFIRMATION_AGENT_ID={result['agent_id']}")
        print("2. Test the agent by making a call")
        print("3. Monitor logs to see conversation flow")
        
    except Exception as e:
        print(f"\n❌ Error configuring agent: {e}")
        raise
    finally:
        await bolna_client.close()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Configure Bolna agent with webhook")
    parser.add_argument(
        "--agent-id",
        type=str,
        help="Existing agent ID to update (optional)"
    )
    
    args = parser.parse_args()
    
    # Run async function
    asyncio.run(configure_agent(args.agent_id))


if __name__ == "__main__":
    main()

# Made with Bob
