#!/bin/bash
echo "Reprocessing all 19 interpelli..."
echo "=================================="

# List of all interpello email IDs
INTERPELLI=(5 8 10 11 12 28 41 44 50 52 53 54 55 62 63 64 68 88 89)

TOTAL=${#INTERPELLI[@]}
CURRENT=0

for email_id in "${INTERPELLI[@]}"; do
  CURRENT=$((CURRENT + 1))
  echo ""
  echo "[$CURRENT/$TOTAL] Processing email $email_id..."

  response=$(curl -s -X POST "http://localhost:8001/api/interpelli/parse/$email_id")

  # Check if successful
  if echo "$response" | grep -q '"success": true'; then
    echo "✅ Successfully scheduled parsing for email $email_id"
  else
    echo "❌ Failed to schedule parsing for email $email_id"
    echo "Response: $response"
  fi

  # Wait 2 seconds between requests to avoid overwhelming the system
  if [ $CURRENT -lt $TOTAL ]; then
    sleep 2
  fi
done

echo ""
echo "=================================="
echo "✅ All $TOTAL interpelli have been scheduled for parsing"
echo "The Celery workers will process them in background."
echo "Check progress with: curl http://localhost:8001/api/interpelli/"
