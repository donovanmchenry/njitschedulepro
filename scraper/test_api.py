#!/usr/bin/env python3
"""Test script to explore the NJIT API endpoints."""

import requests
import json

BASE_URL = "https://generalssb-prod.ec.njit.edu/BannerExtensibility"

# Setup session
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
})

print("Testing NJIT API endpoints...\n")

# Test 1: Default term
print("=" * 60)
print("Test 1: Fetching default term")
print("=" * 60)
url = f"{BASE_URL}/restAPI/virtualDomains/stuRegCrseSchedDefaultTerm"
print(f"URL: {url}\n")

try:
    response = session.get(url)
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Response length: {len(response.text)} bytes")
    print(f"\nFirst 500 characters of response:")
    print(response.text[:500])
    print("\n")

    if response.headers.get('Content-Type', '').startswith('application/json'):
        data = response.json()
        print("JSON parsed successfully!")
        print(json.dumps(data, indent=2)[:1000])
    else:
        print("Response is not JSON")

except Exception as e:
    print(f"Error: {e}")

print("\n")

# Test 2: Subject list
print("=" * 60)
print("Test 2: Fetching subject list for term 202501")
print("=" * 60)
url = f"{BASE_URL}/restAPI/virtualDomains/stuRegCrseSchedSubjList"
params = {'term': '202501', 'attr': ''}
print(f"URL: {url}")
print(f"Params: {params}\n")

try:
    response = session.get(url, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Response length: {len(response.text)} bytes")
    print(f"\nFirst 500 characters of response:")
    print(response.text[:500])
    print("\n")

    if response.headers.get('Content-Type', '').startswith('application/json'):
        data = response.json()
        print("JSON parsed successfully!")
        print(json.dumps(data, indent=2)[:1000])
    else:
        print("Response is not JSON")

except Exception as e:
    print(f"Error: {e}")

print("\n")

# Test 3: Sections for CS
print("=" * 60)
print("Test 3: Fetching CS sections for term 202501")
print("=" * 60)
url = f"{BASE_URL}/restAPI/virtualDomains/stuRegCrseSchedSectionsExcel"
params = {
    'term': '202501',
    'subject': 'CS',
    'attr': '',
    'prof_ucid': ''
}
print(f"URL: {url}")
print(f"Params: {params}\n")

try:
    response = session.get(url, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Response length: {len(response.text)} bytes")
    print(f"\nFirst 1000 characters of response:")
    print(response.text[:1000])
    print("\n")

    if response.headers.get('Content-Type', '').startswith('application/json'):
        data = response.json()
        print("JSON parsed successfully!")
        if 'data' in data:
            print(f"Found {len(data['data'])} records")
            if data['data']:
                print("\nFirst record:")
                print(json.dumps(data['data'][0], indent=2))
    else:
        print("Response is not JSON")
        print(f"\nFull response:\n{response.text}")

except Exception as e:
    print(f"Error: {e}")
