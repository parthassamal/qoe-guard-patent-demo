# Quick Test APIs - Copy & Paste Ready

## 🚀 Ready-to-Use OpenAPI URLs

Copy these URLs directly into the **Endpoint Inventory** page:

### 1. Swagger Petstore (Recommended for First Test)
```
https://petstore3.swagger.io/api/v3/openapi.json
```

### 2. GitHub REST API
```
https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json
```

### 3. Stripe API
```
https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json
```

### 4. Box API
```
https://raw.githubusercontent.com/box/box-openapi/main/openapi.json
```

### 5. APIs.guru Directory
```
https://api.apis.guru/v2/openapi.yaml
```

---

## 🔧 Testing Your Own Swagger

### If you have a Swagger UI page:
1. Find the OpenAPI JSON URL (usually `/openapi.json` or `/v3/api-docs`)
2. Use that direct URL in QoE-Guard

### Common patterns:
- `https://api.example.com/swagger-ui.html` → Try `https://api.example.com/openapi.json`
- `https://api.example.com/docs` → Try `https://api.example.com/openapi.json`
- `https://api.example.com/swagger` → Try `https://api.example.com/swagger.json`

### With Authentication:
Add headers in JSON format:
```json
{
  "Authorization": "Bearer YOUR_TOKEN"
}
```

---

## 📍 Access Points

- **Inventory Page:** http://localhost:8010/inventory
- **Sample Data API:** http://localhost:8010/test-data/swagger-urls
- **Full Testing Guide:** See `docs/TESTING_GUIDE.md`

