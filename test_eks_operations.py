#!/usr/bin/env python3
"""
Test script for EKS operations in the MCP server
"""

import json
import requests
import sys
import os
from typing import Dict, Any

# Load configuration
try:
    with open('client_config.json', 'r') as f:
        config = json.load(f)
    
    MCP_SERVER_URL = config.get('mcp_server_url')
    MCP_API_KEY = config.get('mcp_api_key')
    DEFAULT_REGION = config.get('region', 'us-east-1')
except Exception as e:
    print(f"Error loading configuration: {str(e)}")
    MCP_SERVER_URL = "http://localhost:8000"
    MCP_API_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual API key when testing
    DEFAULT_REGION = "us-east-1"

# MCP API endpoint
MCP_ENDPOINT = f"{MCP_SERVER_URL}/mcp/v1/query"

# Headers for API requests
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": MCP_API_KEY
}

def call_mcp_operation(operation: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Call an MCP operation and return the response"""
    print(f"Calling MCP operation: {operation} with parameters: {json.dumps(parameters)}")
    
    payload = {
        "operation": operation,
        "parameters": parameters
    }
    
    try:
        response = requests.post(MCP_ENDPOINT, headers=HEADERS, json=payload)
        response.raise_for_status()
        result = response.json()
        print(f"MCP response: {json.dumps(result, indent=2)}")
        return result
    except requests.exceptions.RequestException as e:
        print(f"Error calling MCP operation: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        sys.exit(1)

def test_list_clusters():
    """Test the list_clusters operation"""
    print("\n=== Testing list_clusters ===")
    parameters = {
        "region": DEFAULT_REGION
    }
    
    result = call_mcp_operation("list_clusters", parameters)
    
    if result.get("status") == "success":
        clusters = result.get("data", {}).get("clusters", [])
        if clusters:
            print(f"✅ Found {len(clusters)} clusters")
            for cluster in clusters:
                print(f"  - {cluster.get('name')} ({cluster.get('status')})")
        else:
            print("❌ No clusters found")
    else:
        print(f"❌ Operation failed: {result.get('error')}")

def test_describe_cluster():
    """Test the describe_cluster operation"""
    print("\n=== Testing describe_cluster ===")
    
    # First, get a list of clusters
    parameters = {
        "region": DEFAULT_REGION
    }
    
    result = call_mcp_operation("list_clusters", parameters)
    
    if result.get("status") == "success":
        clusters = result.get("data", {}).get("clusters", [])
        if clusters:
            # Use the first cluster for testing
            cluster_name = clusters[0].get("name")
            
            parameters = {
                "region": DEFAULT_REGION,
                "cluster_name": cluster_name
            }
            
            result = call_mcp_operation("describe_cluster", parameters)
            
            if result.get("status") == "success":
                cluster = result.get("data", {}).get("cluster", {})
                if cluster:
                    print(f"✅ Successfully described cluster: {cluster.get('name')}")
                    print(f"  - Status: {cluster.get('status')}")
                    print(f"  - Version: {cluster.get('version')}")
                    print(f"  - Endpoint: {cluster.get('endpoint')}")
                else:
                    print("❌ No cluster details returned")
            else:
                print(f"❌ Operation failed: {result.get('error')}")
        else:
            print("❌ No clusters found to test describe_cluster operation")
    else:
        print(f"❌ Operation failed: {result.get('error')}")

def test_list_nodegroups():
    """Test the list_nodegroups operation"""
    print("\n=== Testing list_nodegroups ===")
    
    # First, get a list of clusters
    parameters = {
        "region": DEFAULT_REGION
    }
    
    result = call_mcp_operation("list_clusters", parameters)
    
    if result.get("status") == "success":
        clusters = result.get("data", {}).get("clusters", [])
        if clusters:
            # Use the first cluster for testing
            cluster_name = clusters[0].get("name")
            
            parameters = {
                "region": DEFAULT_REGION,
                "cluster_name": cluster_name
            }
            
            result = call_mcp_operation("list_nodegroups", parameters)
            
            if result.get("status") == "success":
                nodegroups = result.get("data", {}).get("nodegroups", [])
                if nodegroups:
                    print(f"✅ Found {len(nodegroups)} nodegroups")
                    for nodegroup in nodegroups:
                        print(f"  - {nodegroup.get('name')} ({nodegroup.get('status')})")
                else:
                    print("❌ No nodegroups found")
            else:
                print(f"❌ Operation failed: {result.get('error')}")
        else:
            print("❌ No clusters found to test list_nodegroups operation")
    else:
        print(f"❌ Operation failed: {result.get('error')}")

def test_describe_nodegroup():
    """Test the describe_nodegroup operation"""
    print("\n=== Testing describe_nodegroup ===")
    
    # First, get a list of clusters
    parameters = {
        "region": DEFAULT_REGION
    }
    
    result = call_mcp_operation("list_clusters", parameters)
    
    if result.get("status") == "success":
        clusters = result.get("data", {}).get("clusters", [])
        if clusters:
            # Use the first cluster for testing
            cluster_name = clusters[0].get("name")
            
            # Then, get a list of nodegroups
            parameters = {
                "region": DEFAULT_REGION,
                "cluster_name": cluster_name
            }
            
            result = call_mcp_operation("list_nodegroups", parameters)
            
            if result.get("status") == "success":
                nodegroups = result.get("data", {}).get("nodegroups", [])
                if nodegroups:
                    # Use the first nodegroup for testing
                    nodegroup_name = nodegroups[0].get("name")
                    
                    parameters = {
                        "region": DEFAULT_REGION,
                        "cluster_name": cluster_name,
                        "nodegroup_name": nodegroup_name
                    }
                    
                    result = call_mcp_operation("describe_nodegroup", parameters)
                    
                    if result.get("status") == "success":
                        nodegroup = result.get("data", {}).get("nodegroup", {})
                        if nodegroup:
                            print(f"✅ Successfully described nodegroup: {nodegroup.get('name')}")
                            print(f"  - Status: {nodegroup.get('status')}")
                            print(f"  - Instance Type: {nodegroup.get('instanceType')}")
                            print(f"  - Desired Size: {nodegroup.get('desiredSize')}")
                        else:
                            print("❌ No nodegroup details returned")
                    else:
                        print(f"❌ Operation failed: {result.get('error')}")
                else:
                    print("❌ No nodegroups found to test describe_nodegroup operation")
            else:
                print(f"❌ Operation failed: {result.get('error')}")
        else:
            print("❌ No clusters found to test describe_nodegroup operation")
    else:
        print(f"❌ Operation failed: {result.get('error')}")

def main():
    """Run all tests"""
    print("=== Testing EKS Operations ===")
    
    test_list_clusters()
    test_describe_cluster()
    test_list_nodegroups()
    test_describe_nodegroup()
    
    print("\n=== All tests completed ===")

if __name__ == "__main__":
    main()
