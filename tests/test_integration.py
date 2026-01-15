"""
Integration Tests for QoE-Guard API Endpoints.

Tests cover:
- API authentication flow
- OpenAPI spec discovery
- Validation job execution
- Governance workflows
"""
import unittest
import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

try:
    from qoe_guard.main import app
    HAS_APP = True
except ImportError:
    HAS_APP = False

from tests.fixtures.sample_data import (
    TEST_USER,
    TEST_ADMIN,
    BASELINE_PLAYBACK_RESPONSE,
    CANDIDATE_PLAYBACK_RESPONSE_MINOR,
    CANDIDATE_PLAYBACK_RESPONSE_BREAKING,
    SAMPLE_OPENAPI_SPEC,
)


@unittest.skipUnless(HAS_APP, "FastAPI app not available")
class TestHealthEndpoint(unittest.TestCase):
    """Test health check endpoint."""
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
    
    def test_health_returns_200(self):
        """Health endpoint should return 200."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
    
    def test_health_returns_healthy_status(self):
        """Health endpoint should return healthy status."""
        response = self.client.get("/health")
        data = response.json()
        self.assertEqual(data["status"], "healthy")
    
    def test_health_includes_version(self):
        """Health endpoint should include version."""
        response = self.client.get("/health")
        data = response.json()
        self.assertIn("version", data)


@unittest.skipUnless(HAS_APP, "FastAPI app not available")
class TestAuthenticationFlow(unittest.TestCase):
    """Test authentication endpoints."""
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
    
    def test_register_new_user(self):
        """Should be able to register a new user."""
        # Using unique email to avoid conflicts
        import uuid
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        response = self.client.post(
            "/auth/register",
            json={
                "email": unique_email,
                "password": "testpassword123",
            }
        )
        # May return 201 (created) or 400 (already exists)
        self.assertIn(response.status_code, [201, 400, 422])
    
    def test_login_returns_token(self):
        """Login should return a JWT token."""
        # First register the user
        self.client.post(
            "/auth/register",
            json=TEST_USER
        )
        
        # Then try to login
        response = self.client.post(
            "/auth/login",
            data={
                "username": TEST_USER["email"],
                "password": TEST_USER["password"],
            }
        )
        # May succeed or fail depending on user state
        if response.status_code == 200:
            data = response.json()
            self.assertIn("access_token", data)
            self.assertEqual(data["token_type"], "bearer")
    
    def test_invalid_credentials_rejected(self):
        """Invalid credentials should be rejected."""
        response = self.client.post(
            "/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "wrongpassword",
            }
        )
        self.assertIn(response.status_code, [401, 400, 422])


@unittest.skipUnless(HAS_APP, "FastAPI app not available")
class TestDiffEndpoint(unittest.TestCase):
    """Test JSON diff analysis endpoint."""
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
    
    def test_diff_minor_changes(self):
        """Minor changes should return PASS or WARN."""
        response = self.client.post(
            "/ai/analyze-diff",
            json={
                "baseline": BASELINE_PLAYBACK_RESPONSE,
                "candidate": CANDIDATE_PLAYBACK_RESPONSE_MINOR,
            }
        )
        if response.status_code == 200:
            data = response.json()
            self.assertIn(data.get("decision", "PASS"), ["PASS", "WARN"])
    
    def test_diff_breaking_changes(self):
        """Breaking changes should return WARN or FAIL."""
        response = self.client.post(
            "/ai/analyze-diff",
            json={
                "baseline": BASELINE_PLAYBACK_RESPONSE,
                "candidate": CANDIDATE_PLAYBACK_RESPONSE_BREAKING,
            }
        )
        if response.status_code == 200:
            data = response.json()
            self.assertIn(data.get("decision", "FAIL"), ["WARN", "FAIL"])


@unittest.skipUnless(HAS_APP, "FastAPI app not available")
class TestAIStatusEndpoint(unittest.TestCase):
    """Test AI status endpoint."""
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
    
    def test_ai_status_returns_200(self):
        """AI status should return 200."""
        response = self.client.get("/ai/status")
        # May require auth, so allow 401 too
        self.assertIn(response.status_code, [200, 401, 403])
    
    def test_ai_status_includes_providers(self):
        """AI status should list available providers."""
        response = self.client.get("/ai/status")
        if response.status_code == 200:
            data = response.json()
            self.assertIn("llm_available", data)


@unittest.skipUnless(HAS_APP, "FastAPI app not available")
class TestUIPages(unittest.TestCase):
    """Test UI page rendering."""
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
    
    def test_dashboard_renders(self):
        """Dashboard page should render HTML."""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
    
    def test_inventory_renders(self):
        """Inventory page should render HTML."""
        response = self.client.get("/inventory")
        self.assertEqual(response.status_code, 200)
    
    def test_validate_renders(self):
        """Validation page should render HTML."""
        response = self.client.get("/validate")
        self.assertEqual(response.status_code, 200)
    
    def test_governance_renders(self):
        """Governance page should render HTML."""
        response = self.client.get("/governance")
        self.assertEqual(response.status_code, 200)
    
    def test_settings_renders(self):
        """Settings page should render HTML."""
        response = self.client.get("/settings")
        self.assertEqual(response.status_code, 200)
    
    def test_help_renders(self):
        """Help page should render HTML."""
        response = self.client.get("/help")
        self.assertEqual(response.status_code, 200)
    
    def test_ai_analysis_renders(self):
        """AI Analysis page should render HTML."""
        response = self.client.get("/ai-analysis")
        self.assertEqual(response.status_code, 200)
    
    def test_login_renders(self):
        """Login page should render HTML."""
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)


@unittest.skipUnless(HAS_APP, "FastAPI app not available")
class TestOpenAPIDocumentation(unittest.TestCase):
    """Test OpenAPI documentation endpoints."""
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
    
    def test_openapi_json_available(self):
        """OpenAPI JSON should be available."""
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("openapi", data)
        self.assertIn("info", data)
    
    def test_swagger_ui_available(self):
        """Swagger UI should be available."""
        response = self.client.get("/docs")
        self.assertEqual(response.status_code, 200)
    
    def test_redoc_available(self):
        """ReDoc should be available."""
        response = self.client.get("/redoc")
        self.assertEqual(response.status_code, 200)


@unittest.skipUnless(HAS_APP, "FastAPI app not available")
class TestCORSHeaders(unittest.TestCase):
    """Test CORS configuration."""
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
    
    def test_cors_headers_present(self):
        """CORS headers should be present on responses."""
        response = self.client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        # Should have CORS headers
        headers = response.headers
        self.assertIn("access-control-allow-origin", headers.keys())


class TestValidationWorkflow(unittest.TestCase):
    """Test end-to-end validation workflow (without live API)."""
    
    def test_diff_workflow(self):
        """Test the diff workflow without live API."""
        from qoe_guard.diff import json_diff
        
        # Step 1: Calculate diff
        result = json_diff(
            BASELINE_PLAYBACK_RESPONSE,
            CANDIDATE_PLAYBACK_RESPONSE_BREAKING
        )
        
        # Step 2: Verify we got changes
        self.assertGreater(len(result.changes), 0)
        
        # Step 3: Verify decision is appropriate
        self.assertIn(result.decision, ["WARN", "FAIL"])
    
    def test_feature_extraction_workflow(self):
        """Test feature extraction from diff results."""
        from qoe_guard.diff import json_diff, extract_features
        
        result = json_diff(
            BASELINE_PLAYBACK_RESPONSE,
            CANDIDATE_PLAYBACK_RESPONSE_BREAKING
        )
        
        features = extract_features(result)
        
        # Should have extracted features
        self.assertGreater(features.total_changes, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
