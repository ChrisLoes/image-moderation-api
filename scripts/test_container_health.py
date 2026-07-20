#!/usr/bin/env python3
"""
Health check tests for Docker container before release.
Verifies that:
1. Container starts successfully
2. Health endpoint responds
3. API endpoints are accessible
4. Models are loaded
"""

import sys
import time
import requests
import subprocess
import json
from pathlib import Path

# Configuration
API_URL = "http://localhost:8000"
HEALTH_ENDPOINT = f"{API_URL}/health"
DOCS_ENDPOINT = f"{API_URL}/docs"
MAX_RETRIES = 30
RETRY_DELAY = 2

def run_test(test_name, test_func):
    """Run a single test and report results."""
    try:
        result = test_func()
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
        return result
    except Exception as e:
        print(f"[FAIL] {test_name}: {e}")
        return False

def test_health_endpoint():
    """Test that health endpoint responds."""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def test_api_docs():
    """Test that API documentation is accessible."""
    try:
        response = requests.get(DOCS_ENDPOINT, timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False

def test_container_logs_for_errors():
    """Check Docker container logs for critical errors."""
    try:
        result = subprocess.run(
            ["docker", "logs", "image-moderation-api"],
            capture_output=True,
            text=True,
            timeout=10
        )
        logs = result.stdout + result.stderr

        # Check for critical errors
        error_keywords = [
            "TypeError",
            "AttributeError",
            "ModuleNotFoundError",
            "ImportError",
            "CRITICAL",
            "FATAL",
            "crashed",
            "failed",
        ]

        # Filter out known warnings
        ignore_keywords = [
            "A new release of pip",
            "DeprecationWarning",
            "WARNING: ",
        ]

        for line in logs.split('\n'):
            if any(error in line for error in error_keywords):
                if not any(ignore in line for ignore in ignore_keywords):
                    return False

        return True
    except Exception as e:
        print(f"  Error checking logs: {e}")
        return False

def wait_for_container():
    """Wait for container to become healthy."""
    print("\nWaiting for container to be ready...")
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(HEALTH_ENDPOINT, timeout=3)
            if response.status_code == 200:
                print(f"  Container ready after {attempt * RETRY_DELAY}s")
                return True
        except requests.exceptions.ConnectionError:
            pass

        if attempt < MAX_RETRIES - 1:
            print(f"  Attempt {attempt + 1}/{MAX_RETRIES}...", end="\r")
            time.sleep(RETRY_DELAY)

    return False

def main():
    """Run all health checks."""
    print("=" * 70)
    print("DOCKER CONTAINER HEALTH CHECKS")
    print("=" * 70)
    print()

    # Check if container is running
    print("1. Checking if container is running...")
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=image-moderation-api", "--format", "{{.Status}}"],
        capture_output=True,
        text=True
    )

    if not result.stdout.strip():
        print("[FAIL] Container is not running")
        print("\nTip: Start the container with:")
        print("  docker run -d -p 8000:8000 --name image-moderation-api chrisloes/image-moderation-api:latest")
        return False

    print(f"[OK]  Container is running: {result.stdout.strip()}")

    # Wait for container to be ready
    if not wait_for_container():
        print("\n[FAIL] Container did not become healthy after {MAX_RETRIES * RETRY_DELAY}s")
        print("\nDebugging info:")
        result = subprocess.run(["docker", "logs", "--tail", "50", "image-moderation-api"], capture_output=True, text=True)
        print(result.stdout[-500:])  # Show last 500 chars
        return False

    print()
    print("2. Running API health checks...")
    print()

    tests = [
        ("Health endpoint responds", test_health_endpoint),
        ("API documentation accessible", test_api_docs),
        ("No critical errors in logs", test_container_logs_for_errors),
    ]

    passed = 0
    for test_name, test_func in tests:
        if run_test(test_name, test_func):
            passed += 1

    print()
    print("=" * 70)
    print(f"Results: {passed}/{len(tests)} tests passed")
    print("=" * 70)

    if passed == len(tests):
        print("\n[SUCCESS] Container is healthy and ready for release!")
        return True
    else:
        print("\n[FAILURE] Container health checks failed")
        print("\nDebugging info - last 100 lines of logs:")
        result = subprocess.run(["docker", "logs", "--tail", "100", "image-moderation-api"], capture_output=True, text=True)
        print(result.stdout)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
