#!/bin/bash
echo "Parsing interpelli emails..."
for email_id in 89 88 68 64 63 62 55 54 53 52 28 12 11 10 8 5 50 44 41; do
  echo "Processing email $email_id..."
  response=$(curl -s -X POST "http://localhost:8001/api/interpelli/parse/$email_id")
  echo "$response" | python3 -m json.tool 2>/dev/null | grep -E '"status"|"interpello_id"|"classe_concorso"' || echo "$response"
  sleep 2
done
echo "Done!"
