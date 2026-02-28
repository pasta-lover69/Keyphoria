#!/usr/bin/env python3
"""
Test script for Password Manager API
Run this to verify the API is working correctly
"""

import requests
import json

API_URL = "http://localhost:5000"
TEST_USER = "testuser123"
TEST_PASS = "testpass123"

def print_test(name):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")

def print_result(success, message=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {message}")

def test_health():
    print_test("Health Check")
    try:
        response = requests.get(f"{API_URL}/api/health")
        success = response.status_code == 200
        print_result(success, f"API is {'running' if success else 'not responding'}")
        return success
    except:
        print_result(False, "Cannot connect to API")
        return False

def test_register(session):
    print_test("User Registration")
    data = {"username": TEST_USER, "password": TEST_PASS}
    response = session.post(f"{API_URL}/register", json=data)
    
    success = response.status_code in [200, 201]
    if not success and "already exists" in response.text:
        print_result(True, "User already exists (OK)")
        return True
    
    print_result(success, f"Status: {response.status_code}")
    return success

def test_login(session):
    print_test("User Login")
    data = {"username": TEST_USER, "password": TEST_PASS}
    response = session.post(f"{API_URL}/login", json=data)
    
    success = response.status_code == 200
    print_result(success, f"Status: {response.status_code}")
    return success

def test_session(session):
    print_test("Session Check")
    response = session.get(f"{API_URL}/check-session")
    
    success = response.status_code == 200
    if success:
        data = response.json()
        logged_in = data.get('logged_in', False)
        print_result(logged_in, f"Logged in as: {data.get('username', 'N/A')}")
        return logged_in
    
    print_result(False, "Session check failed")
    return False

def test_add_password(session):
    print_test("Add Password")
    data = {
        "service": "TestService",
        "username": "testuser@example.com",
        "password": "SecureTestPassword123!"
    }
    response = session.post(f"{API_URL}/add", json=data)
    
    success = response.status_code in [200, 201]
    print_result(success, f"Status: {response.status_code}")
    return success

def test_get_passwords(session):
    print_test("Get All Passwords")
    response = session.get(f"{API_URL}/get-all-passwords")
    
    success = response.status_code == 200
    if success:
        passwords = response.json()
        count = len(passwords)
        print_result(True, f"Retrieved {count} password(s)")
        
        if count > 0:
            print("\nSample password entry:")
            pwd = passwords[0]
            print(f"  Service: {pwd.get('service')}")
            print(f"  Username: {pwd.get('username')}")
            print(f"  Password: {'*' * len(pwd.get('password', ''))}")
        
        return True
    
    print_result(False, "Failed to retrieve passwords")
    return False

def test_logout(session):
    print_test("Logout")
    response = session.post(f"{API_URL}/logout")
    
    success = response.status_code == 200
    print_result(success, f"Status: {response.status_code}")
    return success

def main():
    print("\n" + "="*60)
    print("🔐 Password Manager API Test Suite")
    print("="*60)
    print(f"\nTesting API at: {API_URL}")
    print("Make sure the API server is running (python app.py)")
    input("\nPress Enter to start tests...")
    
    session = requests.Session()
    
    results = []
    
    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("Register", test_register(session)))
    results.append(("Login", test_login(session)))
    results.append(("Session", test_session(session)))
    results.append(("Add Password", test_add_password(session)))
    results.append(("Get Passwords", test_get_passwords(session)))
    results.append(("Logout", test_logout(session)))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! API is working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Check the output above.")
    
    print("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTests cancelled by user.")
    except Exception as e:
        print(f"\n❌ Test error: {e}")
