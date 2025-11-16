#!/bin/bash

# OpenAI Proxy API Examples
# Make sure the proxy server is running on localhost:8000

BASE_URL="http://localhost:8000"
API_KEY="mock-api-key-123"  # Use your actual API key

echo "🚀 Testing OpenAI Proxy API Examples"
echo "===================================="

# Test 1: Health Check
echo "📋 1. Health Check"
curl -s "$BASE_URL/health" | jq '.'
echo ""

# Test 2: List Models
echo "📋 2. List Available Models"
curl -s -H "Authorization: Bearer $API_KEY" \
     "$BASE_URL/v1/models" | jq '.data[] | .id'
echo ""

# Test 3: Simple Chat Completion
echo "📋 3. Simple Chat Completion"
curl -s -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [
         {"role": "user", "content": "What is the capital of France?"}
       ],
       "max_tokens": 50
     }' \
     "$BASE_URL/v1/chat/completions" | jq '.choices[0].message'
echo ""

# Test 4: Chat Completion with System Message
echo "📋 4. Chat Completion with System Message"
curl -s -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [
         {"role": "system", "content": "You are a helpful assistant that responds in JSON format."},
         {"role": "user", "content": "What are the colors of the rainbow?"}
       ],
       "max_tokens": 100
     }' \
     "$BASE_URL/v1/chat/completions" | jq '.choices[0].message'
echo ""

# Test 5: Streaming Chat Completion
echo "📋 5. Streaming Chat Completion (first 5 chunks)"
curl -s -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [
         {"role": "user", "content": "Tell me a short joke"}
       ],
       "stream": true
     }' \
     "$BASE_URL/v1/chat/completions" | head -5
echo ""

# Test 6: Text Embeddings
echo "📋 6. Text Embeddings"
curl -s -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "text-embedding-ada-002",
       "input": "Hello, world!"
     }' \
     "$BASE_URL/v1/embeddings" | jq '.data[0] | {index, embedding: (.embedding | length)}'
echo ""

# Test 7: Multiple Input Embeddings
echo "📋 7. Multiple Input Embeddings"
curl -s -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "text-embedding-ada-002",
       "input": ["Hello, world!", "Goodbye, world!", "How are you?"]
     }' \
     "$BASE_URL/v1/embeddings" | jq '.data | map({index, embedding_size: (.embedding | length)})'
echo ""

# Test 8: Error Handling - Invalid Model
echo "📋 8. Error Handling - Invalid Model"
curl -s -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "invalid-model",
       "messages": [
         {"role": "user", "content": "Hello"}
       ]
     }' \
     "$BASE_URL/v1/chat/completions" | jq '.'
echo ""

# Test 9: Error Handling - Missing Auth
echo "📋 9. Error Handling - Missing Authorization"
curl -s -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [
         {"role": "user", "content": "Hello"}
       ]
     }' \
     "$BASE_URL/v1/chat/completions" | jq '.'
echo ""

echo "✅ All tests completed!"
echo ""
echo "💡 Tips:"
echo "   - Replace 'mock-api-key-123' with your actual API key"
echo "   - Add real OpenAI API keys to test actual providers"
echo "   - Check logs at the proxy server for detailed information"
echo "   - Use /metrics endpoint to see Prometheus metrics"