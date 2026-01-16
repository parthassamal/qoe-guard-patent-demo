# QoE-Guard Test Results: Swagger Petstore API

**Test Date:** January 16, 2026  
**API Tested:** Swagger Petstore (Official Demo)  
**URL:** `https://petstore3.swagger.io/api/v3/openapi.json`

---

## 🖼️ Test Screenshots

<div align="center">

<table>
<tr>
<td align="center">
<strong>Imported Specification</strong><br/>
<img src="screenshots/test-petstore-imported.png" alt="Petstore API Imported" width="400"/>
</td>
<td align="center">
<strong>Operations View</strong><br/>
<img src="screenshots/test-petstore-operations.png" alt="Petstore Operations" width="400"/>
</td>
</tr>
</table>

</div>

---

## ✅ Import Results

### Successfully Imported

- **Spec ID:** `c07d2352-e2d9-493f-b57c-cc7cecd9fe03`
- **Title:** Swagger Petstore - OpenAPI 3.0
- **Version:** OpenAPI 3.0.4
- **Endpoints Discovered:** **19 operations**
- **Import Date:** 2026-01-16
- **Source URL:** `https://petstore3.swagger.io/api/v3/openapi.json`

### Import Details

- ✅ OpenAPI spec successfully fetched
- ✅ Spec parsed and validated
- ✅ All operations extracted
- ✅ Stored in QoE-Guard database
- ✅ Ready for validation

---

## 📋 Discovered Operations (19 total)

### Pet Operations (8 endpoints)

| # | Method | Path | Summary |
|---|--------|------|---------|
| 1 | POST | `/pet` | Add a new pet to the store |
| 2 | PUT | `/pet` | Update an existing pet |
| 3 | GET | `/pet/findByStatus` | Finds Pets by status |
| 4 | GET | `/pet/findByTags` | Finds Pets by tags |
| 5 | GET | `/pet/{petId}` | Find pet by ID |
| 6 | POST | `/pet/{petId}` | Updates a pet in the store with form data |
| 7 | DELETE | `/pet/{petId}` | Deletes a pet |
| 8 | POST | `/pet/{petId}/uploadImage` | Uploads an image |

### Store Operations (3 endpoints)

| # | Method | Path | Summary |
|---|--------|------|---------|
| 9 | GET | `/store/inventory` | Returns pet inventories by status |
| 10 | POST | `/store/order` | Place an order for a pet |
| 11 | GET | `/store/order/{orderId}` | Find purchase order by ID |
| 12 | DELETE | `/store/order/{orderId}` | Delete purchase order by identifier |

### User Operations (8 endpoints)

| # | Method | Path | Summary |
|---|--------|------|---------|
| 13 | POST | `/user` | Create user |
| 14 | POST | `/user/createWithList` | Creates list of users with given input array |
| 15 | GET | `/user/login` | Logs user into the system |
| 16 | GET | `/user/logout` | Logs out current logged in user session |
| 17 | GET | `/user/{username}` | Get user by user name |
| 18 | PUT | `/user/{username}` | Update user resource |
| 19 | DELETE | `/user/{username}` | Delete user resource |

---

## 🎯 Test Summary

### What Was Tested

1. ✅ **OpenAPI Discovery**
   - Fetched OpenAPI spec from public URL
   - Parsed OpenAPI 3.0.4 format
   - Extracted all paths and operations

2. ✅ **Operation Extraction**
   - Identified 19 unique operations
   - Categorized by tags (pet, store, user)
   - Extracted method, path, summary for each

3. ✅ **Database Storage**
   - Spec stored with unique ID
   - Operations linked to spec
   - Metadata preserved (version, title, description)

### Next Steps for Validation

To validate these endpoints:

1. **Go to:** `http://localhost:8010/inventory`
2. **Click "View"** on the imported spec
3. **Select endpoints** to validate (checkboxes)
4. **Go to:** `http://localhost:8010/validation`
5. **Configure:**
   - Target URL: `https://petstore3.swagger.io/api/v3`
   - Environment: dev
   - Safe Methods Only: ✓ (for GET endpoints)
6. **Run validation** to get brittleness scores

---

## 📸 Detailed Screenshots

### Imported Specification in Inventory

<div align="center">

<img src="screenshots/test-petstore-imported.png" alt="Petstore API Imported in Inventory" width="800"/>

**Figure 1: Swagger Petstore API Successfully Imported**

</div>

**Details:**
- Shows the imported specification in the "Imported Specifications" table
- Displays: Title (Swagger Petstore - OpenAPI 3.0), Source URL, Version (3.0.4), Endpoint count (19)
- "View" button available to see operations

---

### Operations Table View

<div align="center">

<img src="screenshots/test-petstore-operations.png" alt="Petstore Operations Table" width="800"/>

**Figure 2: All 19 Operations Displayed in Table**

</div>

**Details:**
- Operations table showing all discovered endpoints
- Filter options for HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Search functionality for finding specific operations
- Checkboxes for selecting operations for validation

---

## ✅ Test Status: **PASSED**

The Swagger Petstore API was successfully:
- ✅ Discovered and imported
- ✅ Parsed correctly (OpenAPI 3.0.4)
- ✅ All 19 operations extracted
- ✅ Ready for validation testing

---

## 🔄 Testing Your Own Swagger Pages

**Yes, you can test your own Swagger pages!** Here's how:

### Method 1: Direct OpenAPI URL
```
1. Go to: http://localhost:8010/inventory
2. Enter your OpenAPI JSON URL
3. Add headers if needed (authentication)
4. Click "Discover & Import"
```

### Method 2: Find OpenAPI URL from Swagger UI
```
If you have: https://api.example.com/swagger-ui.html
Try: https://api.example.com/openapi.json
```

### Common Patterns:
- `/swagger-ui.html` → `/openapi.json`
- `/docs` → `/openapi.json`
- `/swagger` → `/swagger.json`

### With Authentication:
```json
{
  "Authorization": "Bearer YOUR_TOKEN"
}
```

---

## 📚 Additional Resources

- **Testing Guide:** `docs/TESTING_GUIDE.md`
- **Quick Reference:** `docs/QUICK_TEST_APIS.md`
- **App Walkthrough:** `docs/APP_WALKTHROUGH.md`

---

**Test completed successfully!** 🎉
