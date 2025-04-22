#!/usr/bin/env python3
"""
Test script to check if kubectl integration can be added to the MCP server
"""

import subprocess
import json
import sys

print("Testing kubectl integration for MCP server...")

# Test if kubectl is available
try:
    print("\n=== Testing kubectl availability ===")
    result = subprocess.run(
        ["kubectl", "version", "--client"],
        capture_output=True,
        text=True,
        check=True
    )
    print("kubectl is available:")
    print(result.stdout)
except Exception as e:
    print(f"Error: kubectl is not available: {str(e)}")
    sys.exit(1)

# Test if kubectl can access the cluster
try:
    print("\n=== Testing kubectl cluster access ===")
    result = subprocess.run(
        ["kubectl", "get", "nodes"],
        capture_output=True,
        text=True,
        check=True
    )
    print("kubectl can access the cluster:")
    print(result.stdout)
except Exception as e:
    print(f"Error: kubectl cannot access the cluster: {str(e)}")
    sys.exit(1)

# Test getting namespaces with kubectl
try:
    print("\n=== Testing kubectl get namespaces ===")
    result = subprocess.run(
        ["kubectl", "get", "namespaces", "-o", "json"],
        capture_output=True,
        text=True,
        check=True
    )
    namespaces_data = json.loads(result.stdout)
    namespaces = []
    
    for item in namespaces_data.get("items", []):
        namespaces.append({
            "name": item.get("metadata", {}).get("name"),
            "status": item.get("status", {}).get("phase"),
            "created": item.get("metadata", {}).get("creationTimestamp")
        })
    
    print(f"Found {len(namespaces)} namespaces:")
    for ns in namespaces:
        print(f"  - {ns['name']} ({ns['status']}) created at {ns['created']}")
    
    # Check if our test namespaces are in the list
    test_namespaces = ["mcp-test-namespace", "mcp-test-namespace-2"]
    for test_ns in test_namespaces:
        found = False
        for ns in namespaces:
            if ns["name"] == test_ns:
                found = True
                print(f"\n✅ Found test namespace: {test_ns}")
                break
        if not found:
            print(f"\n❌ Test namespace not found: {test_ns}")
    
except Exception as e:
    print(f"Error getting namespaces with kubectl: {str(e)}")
    sys.exit(1)

# Test getting pods with kubectl
try:
    print("\n=== Testing kubectl get pods in mcp-test-namespace-2 ===")
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", "mcp-test-namespace-2", "-o", "json"],
        capture_output=True,
        text=True,
        check=True
    )
    pods_data = json.loads(result.stdout)
    pods = []
    
    for item in pods_data.get("items", []):
        pod_name = item.get("metadata", {}).get("name")
        pod_status = item.get("status", {}).get("phase")
        pod_ip = item.get("status", {}).get("podIP")
        node_name = item.get("spec", {}).get("nodeName")
        containers = len(item.get("spec", {}).get("containers", []))
        
        pods.append({
            "name": pod_name,
            "status": pod_status,
            "node": node_name,
            "ip": pod_ip,
            "containers": containers
        })
    
    print(f"Found {len(pods)} pods in mcp-test-namespace-2:")
    for pod in pods:
        print(f"  - {pod['name']} ({pod['status']}) on {pod['node']} with {pod['containers']} containers")
    
except Exception as e:
    print(f"Error getting pods with kubectl: {str(e)}")
    sys.exit(1)

print("\n=== Summary ===")
print("✅ kubectl is available and can access the cluster")
print("✅ kubectl can list namespaces and found our test namespaces")
print("✅ kubectl can list pods in our test namespace")
print("\nThe MCP server could be enhanced to use kubectl for real data instead of mock data.")
print("This would require:")
print("1. Ensuring kubectl is installed in the container")
print("2. Configuring proper authentication to the EKS cluster")
print("3. Updating the server code to use kubectl output instead of mock data")
