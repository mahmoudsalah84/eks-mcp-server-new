#!/usr/bin/env python3
"""
Test script for EKS MCP Server AWS operations
"""

import requests
import json
import sys
import time

# Server configuration
SERVER_URL = "http://107.20.57.177:8000"
API_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual API key when testing
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# Test parameters
CLUSTER_NAME = "sample-eks-cluster"
REGION = "us-east-1"
NODEGROUP_NAME = "standard-workers"

def call_operation(operation, parameters):
    """Call an operation on the MCP server"""
    url = f"{SERVER_URL}/mcp/v1/query"
    payload = {
        "operation": operation,
        "parameters": parameters
    }
    
    print(f"Calling MCP operation: {operation} with parameters: {json.dumps(parameters)}")
    
    try:
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling operation {operation}: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None

def test_health():
    """Test the health endpoint"""
    print("\n=== Testing health endpoint ===")
    url = f"{SERVER_URL}/health"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        print(f"Health check response: {json.dumps(response.json(), indent=2)}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error checking health: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False

def test_list_clusters():
    """Test the list_clusters operation"""
    print("\n=== Testing list_clusters ===")
    response = call_operation("list_clusters", {"region": REGION})
    print(f"MCP response: {json.dumps(response, indent=2)}")
    
    if response and response.get("status") == "success":
        clusters = response.get("data", {}).get("clusters", [])
        if CLUSTER_NAME in [cluster.get("name") for cluster in clusters]:
            print(f"✅ Found cluster: {CLUSTER_NAME}")
            return True
        else:
            print(f"❌ Cluster not found: {CLUSTER_NAME}")
            return False
    else:
        print("❌ Operation failed")
        return False

def test_describe_cluster():
    """Test the describe_cluster operation"""
    print("\n=== Testing describe_cluster ===")
    response = call_operation("describe_cluster", {
        "cluster_name": CLUSTER_NAME,
        "region": REGION
    })
    print(f"MCP response: {json.dumps(response, indent=2)}")
    
    if response and response.get("status") == "success":
        cluster = response.get("data", {}).get("cluster", {})
        if cluster.get("name") == CLUSTER_NAME:
            print(f"✅ Cluster details retrieved for: {CLUSTER_NAME}")
            return True
        else:
            print(f"❌ Cluster details not matching: {CLUSTER_NAME}")
            return False
    else:
        print("❌ Operation failed")
        return False

def test_list_nodegroups():
    """Test the list_nodegroups operation"""
    print("\n=== Testing list_nodegroups ===")
    response = call_operation("list_nodegroups", {
        "cluster_name": CLUSTER_NAME,
        "region": REGION
    })
    print(f"MCP response: {json.dumps(response, indent=2)}")
    
    if response and response.get("status") == "success":
        nodegroups = response.get("data", {}).get("nodegroups", [])
        if nodegroups:
            print(f"✅ Found {len(nodegroups)} nodegroups")
            return nodegroups
        else:
            print("❌ No nodegroups found")
            return []
    else:
        print("❌ Operation failed")
        return []

def test_describe_nodegroup():
    """Test the describe_nodegroup operation"""
    print("\n=== Testing describe_nodegroup ===")
    response = call_operation("describe_nodegroup", {
        "cluster_name": CLUSTER_NAME,
        "nodegroup_name": NODEGROUP_NAME,
        "region": REGION
    })
    print(f"MCP response: {json.dumps(response, indent=2)}")
    
    if response and response.get("status") == "success":
        nodegroup = response.get("data", {}).get("nodegroup", {})
        if nodegroup and nodegroup.get("name") == NODEGROUP_NAME:
            print(f"✅ Nodegroup details retrieved for: {NODEGROUP_NAME}")
            return True
        else:
            print(f"❌ Nodegroup details not matching: {NODEGROUP_NAME}")
            return False
    else:
        print("❌ Operation failed")
        return False

def main():
    """Main function"""
    print("Starting EKS MCP Server AWS operations test")
    print(f"Server URL: {SERVER_URL}")
    
    # Test health endpoint
    if not test_health():
        print("❌ Health check failed, aborting tests")
        sys.exit(1)
    
    # Test AWS operations
    test_list_clusters()
    test_describe_cluster()
    nodegroups = test_list_nodegroups()
    
    # Test nodegroup operations if nodegroups were found
    if nodegroups:
        nodegroup_name = nodegroups[0].get("name")
        test_describe_nodegroup()
    
    print("\n=== Test Summary ===")
    print("✅ Completed testing all AWS operations")

if __name__ == "__main__":
    main()
