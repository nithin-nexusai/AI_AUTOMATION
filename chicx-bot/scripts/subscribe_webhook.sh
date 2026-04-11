#!/bin/bash

# Subscribe webhook to WhatsApp Business Account
# This script subscribes the webhook to receive messages for the specific WABA

set -e

echo "🔗 Subscribing webhook to WABA..."

WABA_ID="1583001416136225"
ACCESS_TOKEN="EAAMdulcZBdbABRK4sIRofM15QdIpGWV3ini6Se10ZChZC5t9w4UV0ZAeLi7WkPcFOeCbM0bcYPBSkyTAqPwd4zv2tGe5oDUYAtAXTejQadPjy2LiZCNqX9ESmeSI0ZCGZAlbf0mwwaXzM6d4qIoAfScIpXHAio2PkwBZAePbm0fIsgsSdEZBmDlZCaghpq9I9sIeN5lQZDZ"

echo "WABA ID: $WABA_ID"
echo ""

# Subscribe to messages field
echo "📝 Subscribing to 'messages' field..."
RESPONSE=$(curl -s -X POST \
  "https://graph.facebook.com/v21.0/${WABA_ID}/subscribed_apps" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -d "subscribed_fields=messages")

echo "Response: $RESPONSE"
echo ""

# Check current subscriptions
echo "✅ Checking current subscriptions..."
SUBSCRIPTIONS=$(curl -s -X GET \
  "https://graph.facebook.com/v21.0/${WABA_ID}/subscribed_apps" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "Current subscriptions: $SUBSCRIPTIONS"
echo ""

if echo "$SUBSCRIPTIONS" | grep -q "messages"; then
    echo "✅ SUCCESS! Webhook is now subscribed to receive messages for WABA $WABA_ID"
else
    echo "❌ WARNING: Subscription might have failed. Check the response above."
fi

# Made with Bob
