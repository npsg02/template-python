#!/bin/bash

# Admin API Examples for OpenAI Proxy
# These examples show how to manage providers, keys, and model mappings

BASE_URL="http://localhost:8000"
ADMIN_KEY="admin-key-12345"  # Use your actual admin API key

echo "🔧 Testing OpenAI Proxy Admin API"
echo "=================================="

# Test 1: List Providers
echo "📋 1. List All Providers"
curl -s -H "Authorization: Bearer $ADMIN_KEY" \
     "$BASE_URL/admin/providers" | jq '.'
echo ""

# Test 2: Create New Provider
echo "📋 2. Create New Provider"
curl -s -H "Authorization: Bearer $ADMIN_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "anthropic-claude",
       "provider_type": "anthropic",
       "base_url": "https://api.anthropic.com/v1",
       "config_json": {"timeout": 30},
       "timeout_seconds": 30,
       "max_retries": 3
     }' \
     "$BASE_URL/admin/providers" | jq '.'
echo ""

# Test 3: List API Keys
echo "📋 3. List All API Keys"
curl -s -H "Authorization: Bearer $ADMIN_KEY" \
     "$BASE_URL/admin/keys" | jq '.[] | {id, provider_id, key_id, masked_key, status}'
echo ""

# Test 4: Add New API Key
echo "📋 4. Add New API Key"
curl -s -H "Authorization: Bearer $ADMIN_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "provider_id": 1,
       "key_id": "openai-backup-key",
       "key_value": "sk-example-backup-key-replace-me",
       "priority": 200,
       "rate_limit_rpm": 500,
       "rate_limit_tpm": 50000,
       "daily_quota": 1000
     }' \
     "$BASE_URL/admin/keys" | jq '.'
echo ""

# Test 5: List Model Mappings
echo "📋 5. List All Model Mappings"
curl -s -H "Authorization: Bearer $ADMIN_KEY" \
     "$BASE_URL/admin/mappings" | jq '.[] | {alias_name, provider_id, provider_model_name, order_index}'
echo ""

# Test 6: Create Model Mapping
echo "📋 6. Create New Model Mapping"
curl -s -H "Authorization: Bearer $ADMIN_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "alias_name": "claude-v1",
       "provider_id": 2,
       "provider_model_name": "claude-1",
       "order_index": 0,
       "is_default": true,
       "config_json": {"temperature": 0.7}
     }' \
     "$BASE_URL/admin/mappings" | jq '.'
echo ""

# Test 7: Get Key Health Status
echo "📋 7. Get Key Health Status"
curl -s -H "Authorization: Bearer $ADMIN_KEY" \
     "$BASE_URL/admin/keys/1/health" | jq '.'
echo ""

# Test 8: System Health Check
echo "📋 8. System Health Check"
curl -s -H "Authorization: Bearer $ADMIN_KEY" \
     "$BASE_URL/admin/health" | jq '.'
echo ""

# Test 9: Filter Model Mappings by Alias
echo "📋 9. Filter Model Mappings by Alias"
curl -s -H "Authorization: Bearer $ADMIN_KEY" \
     "$BASE_URL/admin/mappings?alias_name=gpt-3.5-turbo" | jq '.'
echo ""

# Test 10: Filter API Keys by Provider
echo "📋 10. Filter API Keys by Provider"
curl -s -H "Authorization: Bearer $ADMIN_KEY" \
     "$BASE_URL/admin/keys?provider_id=1" | jq '.'
echo ""

# Test 11: Reset Circuit Breaker
echo "📋 11. Reset Circuit Breaker for Provider"
curl -s -X POST -H "Authorization: Bearer $ADMIN_KEY" \
     "$BASE_URL/admin/circuit-breaker/1/reset" | jq '.'
echo ""

# Test 12: Update Provider Status
echo "📋 12. Update Provider (disable)"
curl -s -X PUT -H "Authorization: Bearer $ADMIN_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "status": "disabled"
     }' \
     "$BASE_URL/admin/providers/2" | jq '.'
echo ""

# Test 13: Error Handling - Unauthorized
echo "📋 13. Error Handling - Unauthorized Access"
curl -s -H "Authorization: Bearer invalid-key" \
     "$BASE_URL/admin/providers" | jq '.'
echo ""

echo "✅ All admin tests completed!"
echo ""
echo "💡 Admin API Tips:"
echo "   - Always use HTTPS in production"
echo "   - Rotate admin API keys regularly"
echo "   - Monitor admin API usage with audit logs"
echo "   - Use strong authentication for admin endpoints"
echo "   - Test key health before making changes"