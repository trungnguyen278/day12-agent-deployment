# Deployment Information

## Public URL
https://lab12-agent-production.up.railway.app

## Platform
Railway

## Test Commands

### Health Check
```bash
curl https://lab12-agent-production.up.railway.app/health
# Expected: {"status":"ok","version":"1.0.0","environment":"production",...}
```

### API Test (with authentication)
```bash
curl -X POST https://lab12-agent-production.up.railway.app/ask \
  -H "X-API-Key: my-secret-api-key-2024" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello, what is Docker?"}'
# Expected: {"question":"...","answer":"...","model":"gpt-4o-mini","timestamp":"..."}
```

### Rate Limit Test
```bash
for i in {1..25}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST https://lab12-agent-production.up.railway.app/ask \
    -H "X-API-Key: my-secret-api-key-2024" \
    -H "Content-Type: application/json" \
    -d '{"question": "test"}'
done
# Expected: 200 for first 20, then 429
```

### No Auth Test
```bash
curl -X POST https://lab12-agent-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "test"}'
# Expected: 401 Unauthorized
```

## Environment Variables Set
- PORT
- ENVIRONMENT=production
- AGENT_API_KEY
- REDIS_URL (if using Redis add-on)
- DAILY_BUDGET_USD
- RATE_LIMIT_PER_MINUTE
- APP_VERSION

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Health check result](screenshots/health.png)
- [API test result](screenshots/test.png)
