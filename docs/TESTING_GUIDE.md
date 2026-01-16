# QoE-Guard Testing Guide

> **How to test with sample APIs and your own Swagger pages**

---

## 🎯 Quick Access to Sample Data

Your QoE-Guard app has built-in sample data endpoints. Access them at:

```
http://localhost:8010/test-data/swagger-urls
http://localhost:8010/test-data/baseline
http://localhost:8010/test-data/candidate/minor
http://localhost:8010/test-data/candidate/breaking
http://localhost:8010/test-data/runtime-metrics
http://localhost:8010/test-data/changes
http://localhost:8010/test-data/all
```

---

## 📋 Sample Public APIs You Can Test

### 1. **Swagger Petstore (Official Demo)**
```
URL: https://petstore3.swagger.io/api/v3/openapi.json
```
- **Best for:** First-time testing
- **Features:** CRUD operations for pets, store, users
- **Format:** JSON
- **No auth required**

### 2. **GitHub REST API**
```
URL: https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json
```
- **Best for:** Large, real-world API testing
- **Features:** Complete GitHub API (1000+ endpoints)
- **Format:** JSON
- **Auth:** Optional (for private repos)

### 3. **Stripe API**
```
URL: https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json
```
- **Best for:** Payment API validation
- **Features:** Complete Stripe payment API
- **Format:** JSON
- **Auth:** Required for live testing

### 4. **Box API**
```
URL: https://raw.githubusercontent.com/box/box-openapi/main/openapi.json
```
- **Best for:** Cloud storage API testing
- **Features:** File management, collaboration
- **Format:** JSON
- **Auth:** Required

### 5. **APIs.guru Directory**
```
URL: https://api.apis.guru/v2/openapi.yaml
```
- **Best for:** API directory/metadata testing
- **Features:** Directory of public APIs
- **Format:** YAML
- **No auth required**

---

## 🔧 How to Test Your Own Swagger Pages

**Yes, you can absolutely test your own Swagger pages!** Here's how:

### Method 1: Direct OpenAPI JSON/YAML URL

If your API exposes the OpenAPI spec directly:

1. **Go to:** `http://localhost:8010/inventory`
2. **Enter your OpenAPI URL:**
   ```
   https://your-api.com/openapi.json
   https://your-api.com/v3/api-docs
   https://your-api.com/api-docs.yaml
   ```
3. **Add headers (if needed):**
   ```json
   {
     "Authorization": "Bearer YOUR_TOKEN",
     "X-API-Key": "your-key"
   }
   ```
4. **Click "Discover"**

### Method 2: Swagger UI Page

If you only have a Swagger UI page (like `/swagger-ui.html`):

1. **Find the OpenAPI JSON URL:**
   - Open your Swagger UI page in browser
   - Look for a link like `/openapi.json` or `/v3/api-docs`
   - Or check the browser network tab when Swagger UI loads
   - Common patterns:
     - `https://api.example.com/swagger-ui.html` → Try `https://api.example.com/openapi.json`
     - `https://api.example.com/docs` → Try `https://api.example.com/openapi.json`
     - `https://api.example.com/swagger` → Try `https://api.example.com/swagger.json`

2. **Use that direct URL in QoE-Guard**

### Method 3: Local/Private APIs

For local or private APIs:

1. **Make sure your API is accessible:**
   ```bash
   # Test if your API is reachable
   curl https://your-api.com/openapi.json
   ```

2. **If behind authentication:**
   - Add headers in the "Headers (JSON)" field:
   ```json
   {
     "Authorization": "Bearer YOUR_TOKEN",
     "Cookie": "session=YOUR_SESSION"
   }
   ```

3. **If CORS blocked:**
   - Use the direct OpenAPI JSON URL (not the Swagger UI page)
   - Or configure CORS on your API server

### Method 4: Upload Local OpenAPI File

If you have a local OpenAPI file:

1. **Host it temporarily:**
   ```bash
   # Option 1: Use Python's built-in server
   cd /path/to/your/openapi
   python3 -m http.server 8000
   # Then use: http://localhost:8000/openapi.json
   
   # Option 2: Use a file sharing service
   # Upload to GitHub Gist, Pastebin, etc.
   ```

2. **Use the hosted URL in QoE-Guard**

---

## 🧪 Step-by-Step Testing Workflow

### Test 1: Import a Public API

1. Open `http://localhost:8010/inventory`
2. Enter: `https://petstore3.swagger.io/api/v3/openapi.json`
3. Click **"Discover"**
4. Wait for import to complete
5. View discovered endpoints in the table below

### Test 2: Select and Validate Endpoints

1. After import, check boxes for endpoints you want to test
2. Click **"Run Validation"** (or go to `/validation` page)
3. Configure:
   - **Environment:** dev/staging/prod
   - **Target URL:** Your actual API base URL
   - **Concurrency:** 5 (default)
   - **Safe Methods Only:** ✓ (recommended for first test)
4. Click **"Start Validation"**
5. View results with brittleness scores

### Test 3: AI Analysis

1. Go to `http://localhost:8010/ai-analysis`
2. Use sample data from `/test-data/baseline` and `/test-data/candidate/minor`
3. Test each AI feature:
   - **LLM Diff Analysis** - Compare JSONs
   - **Semantic Drift** - Detect field renames
   - **Anomaly Detection** - Use `/test-data/runtime-metrics`
   - **NLP Classification** - Classify endpoints
   - **ML Scoring** - Use `/test-data/changes`

---

## 🔐 Authentication Examples

### Bearer Token
```json
{
  "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### API Key
```json
{
  "X-API-Key": "your-api-key-here"
}
```

### Basic Auth
```json
{
  "Authorization": "Basic base64(username:password)"
}
```

### Multiple Headers
```json
{
  "Authorization": "Bearer TOKEN",
  "X-API-Key": "KEY",
  "X-Request-ID": "12345"
}
```

---

## 🐛 Troubleshooting

### "Failed to discover OpenAPI spec"

**Solutions:**
- ✅ Check if URL is accessible: `curl https://your-api.com/openapi.json`
- ✅ Try the direct JSON URL instead of Swagger UI page
- ✅ Verify authentication headers are correct
- ✅ Check CORS settings (use JSON URL, not UI page)
- ✅ Ensure the URL returns valid OpenAPI 3.0/3.1 spec

### "CORS Error"

**Solutions:**
- ✅ Use the direct OpenAPI JSON URL (not Swagger UI)
- ✅ Configure CORS on your API server
- ✅ Use a proxy or browser extension to bypass CORS

### "Authentication Failed"

**Solutions:**
- ✅ Verify token is valid and not expired
- ✅ Check header format: `"Authorization": "Bearer TOKEN"`
- ✅ Test with `curl` first:
  ```bash
  curl -H "Authorization: Bearer TOKEN" \
       https://your-api.com/openapi.json
  ```

### "No endpoints found"

**Solutions:**
- ✅ Verify the OpenAPI spec has `paths` defined
- ✅ Check if spec version is 3.0 or 3.1 (2.0 not supported)
- ✅ Ensure paths are not empty

---

## 📊 Example: Testing Your Own API

Let's say you have an API at `https://api.mycompany.com`:

### Step 1: Find OpenAPI Spec
```bash
# Try common paths
curl https://api.mycompany.com/openapi.json
curl https://api.mycompany.com/v3/api-docs
curl https://api.mycompany.com/swagger.json
```

### Step 2: Import to QoE-Guard
1. Go to `http://localhost:8010/inventory`
2. Enter: `https://api.mycompany.com/openapi.json`
3. Add headers if needed:
   ```json
   {
     "Authorization": "Bearer YOUR_TOKEN"
   }
   ```
4. Click **"Discover"**

### Step 3: Validate
1. Select endpoints from the table
2. Go to `/validation` page
3. Set **Target URL:** `https://api.mycompany.com`
4. Run validation

### Step 4: Review Results
- Check brittleness scores
- Review QoE risk assessments
- Use AI analysis for deeper insights

---

## 🎓 Best Practices

1. **Start with public APIs** (Petstore) to learn the tool
2. **Use "Safe Methods Only"** for first tests (GET/HEAD only)
3. **Test in dev/staging** before production
4. **Review AI recommendations** before making changes
5. **Promote baselines** only after stable validation runs

---

## 📚 Additional Resources

- **API Docs:** `http://localhost:8010/docs` (Swagger UI)
- **Help Guide:** `http://localhost:8010/help`
- **Test Data:** `http://localhost:8010/test-data/all`

---

## 🚀 Quick Test Commands

```bash
# Get all sample data
curl http://localhost:8010/test-data/all

# Get sample Swagger URLs
curl http://localhost:8010/test-data/swagger-urls

# Test Petstore import (via API)
curl -X POST http://localhost:8010/specs/discover \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://petstore3.swagger.io/api/v3/openapi.json"
  }'
```

---

**Happy Testing! 🎉**

For issues or questions, check the Help Guide at `/help` or review the API docs at `/docs`.
