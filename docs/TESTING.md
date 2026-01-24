# Testing Documentation

## Overview

This project includes comprehensive unit tests for the AI Meal Planner application. The test suite covers:

- **Utility Functions** (`test_utils.py`): Tests for data persistence, recipe selection algorithms, and grocery list generation
- **Flask Routes** (`test_routes.py`): Tests for all HTTP endpoints including CRUD operations
- **AI Integration** (`test_ai.py`): Tests for AI client configuration and meal plan generation with mocking

## Running Tests

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Tests with Coverage

```bash
pytest --cov=app --cov-report=html --cov-report=term-missing
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Run Specific Test Files

```bash
# Run only utility tests
pytest tests/test_utils.py

# Run only route tests
pytest tests/test_routes.py

# Run only AI tests
pytest tests/test_ai.py
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/test_utils.py::TestRecipeSelection

# Run a specific test function
pytest tests/test_routes.py::TestRecipesRoutes::test_add_recipe_post_success
```

### Verbose Output

```bash
pytest -v
```

### Stop on First Failure

```bash
pytest -x
```

## Test Structure

### Fixtures (`tests/conftest.py`)

The test suite uses pytest fixtures for:
- `app`: Configured Flask application for testing
- `client`: Test client for making HTTP requests
- `sample_recipe`: Single recipe for testing
- `sample_recipes`: Multiple recipes for testing selection algorithms
- `sample_meal_plan`: Sample meal plan for testing

### Test Organization

All tests are located in the `tests/` directory and organized into classes by functionality:

**tests/test_utils.py:**
- `TestDataPersistence`: Loading/saving recipes and meal plans
- `TestRecipeSelection`: Recipe selection with spacing algorithms
- `TestGroceryList`: Grocery list generation and aggregation

**tests/test_routes.py:**
- `TestIndexRoute`: Home page
- `TestRecipesRoutes`: Recipe CRUD operations
- `TestMealPlansRoutes`: Meal plan generation and viewing
- `TestHealthEndpoint`: Health check endpoint
- `TestIntegration`: End-to-end workflow tests

**tests/test_ai.py:**
- `TestAIClient`: AI client configuration
- `TestAIMealPlanGeneration`: AI-powered meal ordering
- `TestAIIntegration`: AI integration in full workflow

## Coverage Goals

Current test coverage targets:
- Line coverage: >90%
- Branch coverage: >85%

Areas covered:
- ✅ All route handlers
- ✅ Data persistence functions
- ✅ Recipe selection algorithms
- ✅ Grocery list generation
- ✅ AI integration with fallback behavior
- ✅ Error handling and edge cases

## Mocking

The test suite uses `pytest-mock` and `unittest.mock` to mock:
- File I/O operations (via temporary directories)
- OpenAI API calls
- External dependencies

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest --cov=app --cov-report=xml
```

## Writing New Tests

When adding new functionality:

1. Add test fixtures to `tests/conftest.py` if needed
2. Create test functions in the appropriate test file in `tests/` directory
3. Organize related tests into classes
4. Mock external dependencies
5. Test both success and failure cases
6. Verify edge cases and boundary conditions

Example test structure:

```python
def test_new_feature_success(client, sample_data):
    """Test successful execution of new feature."""
    response = client.post('/endpoint', data=sample_data)
    assert response.status_code == 200
    # Additional assertions

def test_new_feature_failure(client):
    """Test error handling in new feature."""
    response = client.post('/endpoint', data={})
    assert response.status_code == 400
```

## Troubleshooting

### Import Errors

If you encounter import errors, ensure you're running tests from the project root:

```bash
cd /Users/miliddle/workspace/aimealplanner
pytest
```

### Database/File Conflicts

Tests use temporary directories and should not interfere with production data. Each test gets a fresh temporary directory via the `app` fixture.

### AI Mock Not Working

Ensure you're patching at the correct import location:

```python
with patch('app.get_ai_client', return_value=mock_client):
    # Your test code
```
