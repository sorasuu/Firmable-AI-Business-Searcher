# Running Tests - Quick Guide

## Prerequisites

Make sure you have Python dependencies installed:
```bash
cd api
uv sync
uv sync --extra test
```

## Running All Tests

From the project root directory:

```bash
pytest api/test_api.py -v
```

**Expected Output:**
```
api/test_api.py::TestAuthentication::test_missing_auth_header PASSED
api/test_api.py::TestAuthentication::test_invalid_auth_format PASSED
api/test_api.py::TestAuthentication::test_invalid_token PASSED
api/test_api.py::TestValidation::test_missing_url PASSED
api/test_api.py::TestValidation::test_invalid_url_format PASSED
...

========================= XX passed in X.XXs =========================
```

## Running Specific Test Classes

### Test Authentication Only
```bash
pytest api/test_api.py::TestAuthentication -v
```

### Test Validation Only
```bash
pytest api/test_api.py::TestValidation -v
```

### Test Analyze Endpoint Only
```bash
pytest api/test_api.py::TestAnalyzeEndpoint -v
```

### Test Chat Endpoint Only
```bash
pytest api/test_api.py::TestChatEndpoint -v
```

## Running with Coverage Report

```bash
pytest api/test_api.py --cov=api --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`.

Open it in your browser:
```bash
# Windows
start htmlcov/index.html

# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html
```

## Test Categories

### ✅ Authentication Tests (4 tests)
- Missing auth header → 401
- Invalid auth format → 401
- Invalid token → 401
- Valid auth → passes

### ✅ Validation Tests (5 tests)
- Missing URL → 422
- Invalid URL format → 422
- Valid HTTPS URL → passes
- Optional questions field → works

### ✅ Analyze Endpoint Tests (4 tests)
- Successful analysis → 200 with insights
- Analysis with custom questions → 200 with answers
- Scraping failure → 500 with error message
- Empty scrape result → handled gracefully

### ✅ Chat Endpoint Tests (3 tests)
- Successful chat → 200 with response
- Chat with conversation history → maintains context
- Chat failure → 500 with error message

### ✅ Health Check Tests (3 tests)
- `/api/health` endpoint → 200 healthy
- `/health` endpoint → 200 healthy
- Root `/` endpoint → 200 with API info

### ✅ Error Handling Tests (2 tests)
- Malformed JSON → 400/422
- Empty scrape result → handled

## Troubleshooting

### "Import could not be resolved" errors
These are VS Code warnings. The tests will run fine if dependencies are installed:
```bash
cd api
uv sync
uv sync --extra test
```

### "Module not found" when running tests
Make sure you're in the project root directory, not the `api/` folder:
```bash
# Wrong (from api/ folder)
cd api
pytest test_api.py

# Correct (from project root)
pytest api/test_api.py
```

### Tests fail with connection errors
The tests use mocking, so they don't need actual services running. If you see connection errors, check that mocking is working properly.

### Environment variables not found
The tests mock external services, so you don't need `.env.local` for testing. However, if you want to run integration tests, set:
```bash
export API_SECRET_KEY="test-key"
export GROQ_API_KEY="test-key"
```

## Continuous Integration

To add these tests to CI/CD (GitHub Actions):

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v3
        with:
          version: "latest"
      - run: cd api && uv sync
      - run: cd api && uv sync --extra test
      - run: pytest api/test_api.py -v --cov=api
```

## Quick Test Before Deployment

Before deploying, run this quick check:

```bash
# Run all tests
pytest api/test_api.py -v

# If all pass, you're good to deploy! ✅
```

---

**Note**: These tests focus on API behavior and don't require external services. For integration testing with real Groq API, create separate integration tests.
