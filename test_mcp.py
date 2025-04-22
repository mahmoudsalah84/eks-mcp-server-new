#!/usr/bin/env python3
"""
Test script for the EKS MCP Server
"""

import json
import time
import requests

BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/health")
    end_time = time.time()
    
    print(f"Health check response time: {end_time - start_time:.4f} seconds")
    print(f"Status code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def test_operations():
    """Test the operations endpoint"""
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/mcp/v1/operations")
    end_time = time.time()
    
    print(f"Operations response time: {end_time - start_time:.4f} seconds")
    print(f"Status code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def test_list_clusters():
    """Test the list_clusters operation"""
    payload = {
        "operation": "list_clusters",
        "parameters": {
            "region": "us-east-1"
        }
    }
    
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/mcp/v1/query", json=payload)
    end_time = time.time()
    
    print(f"List clusters response time: {end_time - start_time:.4f} seconds")
    print(f"Status code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def test_list_namespaces():
    """Test the list_namespaces operation"""
    payload = {
        "operation": "list_namespaces",
        "parameters": {
            "cluster_name": "test-cluster",
            "region": "us-east-1"
        }
    }
    
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/mcp/v1/query", json=payload)
    end_time = time.time()
    
    print(f"List namespaces response time: {end_time - start_time:.4f} seconds")
    print(f"Status code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def test_list_pods():
    """Test the list_pods operation"""
    payload = {
        "operation": "list_pods",
        "parameters": {
            "cluster_name": "test-cluster",
            "namespace": "default",
            "region": "us-east-1"
        }
    }
    
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/mcp/v1/query", json=payload)
    end_time = time.time()
    
    print(f"List pods response time: {end_time - start_time:.4f} seconds")
    print(f"Status code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print()

def main():
    """Run all tests"""
    print("Testing EKS MCP Server...")
    print("=" * 50)
    
    # Wait for server to start
    time.sleep(2)
    
    test_health()
    test_operations()
    test_list_clusters()
    test_list_namespaces()
    test_list_pods()

if __name__ == "__main__":
    main()
