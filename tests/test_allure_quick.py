"""
Quick test to verify Allure integration is working.
"""
import pytest

try:
    import allure
    ALLURE_AVAILABLE = True
except ImportError:
    ALLURE_AVAILABLE = False
    pytest.skip("allure-pytest not installed", allow_module_level=True)


@allure.feature("Allure Integration Test")
class TestAllureIntegration:
    """Verify Allure is working correctly."""
    
    @allure.story("Basic Allure Test")
    @allure.title("Verify Allure annotations work")
    @allure.severity(allure.severity_level.TRIVIAL)
    def test_allure_basic(self):
        """Basic test to verify Allure is working."""
        with allure.step("Step 1: Verify Allure is imported"):
            assert ALLURE_AVAILABLE
        
        with allure.step("Step 2: Attach test data"):
            allure.attach(
                '{"status": "success", "allure": "working"}',
                "Test Data",
                allure.attachment_type.JSON
            )
        
        with allure.step("Step 3: Assert test passes"):
            assert True
    
    @allure.story("Allure with Assertions")
    @allure.title("Test with assertions and attachments")
    @allure.severity(allure.severity_level.NORMAL)
    def test_allure_with_data(self):
        """Test with data attachments."""
        test_data = {
            "baseline": {"value": 100},
            "candidate": {"value": 200},
            "expected_changes": 1
        }
        
        allure.attach(
            str(test_data),
            "Test Input Data",
            allure.attachment_type.JSON
        )
        
        # Simulate a diff result
        result = {
            "changes": 1,
            "decision": "WARN",
            "qoe_risk": 0.5
        }
        
        allure.attach(
            str(result),
            "Test Result",
            allure.attachment_type.JSON
        )
        
        assert result["changes"] == test_data["expected_changes"]
