#!/usr/bin/env python3
"""
Test script for EKS MCP Server with kubectl operations
"""

import requests
import json
import sys
import time
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Server configuration
SERVER_URL = "http://3.90.45.69:8000"
API_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual API key when testing
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# Test parameters
CLUSTER_NAME = "sample-eks-cluster"
REGION = "us-east-1"
TEST_NAMESPACE = "mcp-test-namespace"
TEST_NAMESPACE_2 = "mcp-test-namespace-2"

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

def test_list_namespaces():
    """Test the list_namespaces operation"""
    print("\n=== Testing list_namespaces ===")
    response = call_operation("list_namespaces", {
        "cluster_name": CLUSTER_NAME,
        "region": REGION
    })
    print(f"MCP response: {json.dumps(response, indent=2)}")
    
    if response and response.get("status") == "success":
        namespaces = response.get("data", {}).get("namespaces", [])
        namespace_names = [ns.get("name") for ns in namespaces]
        
        if TEST_NAMESPACE in namespace_names:
            print(f"✅ Found namespace: {TEST_NAMESPACE}")
        else:
            print(f"❌ Test namespace not found: {TEST_NAMESPACE}")
        
        if TEST_NAMESPACE_2 in namespace_names:
            print(f"✅ Found namespace: {TEST_NAMESPACE_2}")
        else:
            print(f"❌ Test namespace not found: {TEST_NAMESPACE_2}")
            
        return TEST_NAMESPACE in namespace_names or TEST_NAMESPACE_2 in namespace_names
    else:
        print("❌ Operation failed")
        return False

def test_list_pods(namespace):
    """Test the list_pods operation"""
    print(f"\n=== Testing list_pods ({namespace}) ===")
    response = call_operation("list_pods", {
        "cluster_name": CLUSTER_NAME,
        "namespace": namespace,
        "region": REGION
    })
    print(f"MCP response: {json.dumps(response, indent=2)}")
    
    if response and response.get("status") == "success":
        pods = response.get("data", {}).get("pods", [])
        if pods:
            print(f"✅ Found {len(pods)} pods in namespace {namespace}")
            return pods
        else:
            print(f"❌ No pods found in namespace {namespace}")
            return []
    else:
        print("❌ Operation failed")
        return []

def test_get_deployments(namespace):
    """Test the get_deployments operation"""
    print(f"\n=== Testing get_deployments ({namespace}) ===")
    response = call_operation("get_deployments", {
        "cluster_name": CLUSTER_NAME,
        "namespace": namespace,
        "region": REGION
    })
    print(f"MCP response: {json.dumps(response, indent=2)}")
    
    if response and response.get("status") == "success":
        deployments = response.get("data", {}).get("deployments", [])
        if deployments:
            print(f"✅ Found {len(deployments)} deployments in namespace {namespace}")
            return deployments
        else:
            print(f"❌ No deployments found in namespace {namespace}")
            return []
    else:
        print("❌ Operation failed")
        return []

def test_describe_deployment(namespace, deployment_name):
    """Test the describe_deployment operation"""
    print(f"\n=== Testing describe_deployment ({namespace}/{deployment_name}) ===")
    response = call_operation("describe_deployment", {
        "cluster_name": CLUSTER_NAME,
        "namespace": namespace,
        "deployment_name": deployment_name,
        "region": REGION
    })
    print(f"MCP response: {json.dumps(response, indent=2)}")
    
    if response and response.get("status") == "success":
        deployment = response.get("data", {}).get("deployment", {})
        if deployment and deployment.get("name") == deployment_name:
            print(f"✅ Deployment details retrieved for: {deployment_name}")
            return True
        else:
            print(f"❌ Deployment details not matching: {deployment_name}")
            return False
    else:
        print("❌ Operation failed")
        return False

def test_get_services(namespace):
    """Test the get_services operation"""
    print(f"\n=== Testing get_services ({namespace}) ===")
    response = call_operation("get_services", {
        "cluster_name": CLUSTER_NAME,
        "namespace": namespace,
        "region": REGION
    })
    print(f"MCP response: {json.dumps(response, indent=2)}")
    
    if response and response.get("status") == "success":
        services = response.get("data", {}).get("services", [])
        if services:
            print(f"✅ Found {len(services)} services in namespace {namespace}")
            return services
        else:
            print(f"❌ No services found in namespace {namespace}")
            return []
    else:
        print("❌ Operation failed")
        return []

def test_describe_pod(namespace, pod_name):
    """Test the describe_pod operation"""
    print(f"\n=== Testing describe_pod ({namespace}/{pod_name}) ===")
    response = call_operation("describe_pod", {
        "cluster_name": CLUSTER_NAME,
        "namespace": namespace,
        "pod_name": pod_name,
        "region": REGION
    })
    print(f"MCP response: {json.dumps(response, indent=2)}")
    
    if response and response.get("status") == "success":
        pod = response.get("data", {}).get("pod", {})
        if pod and pod.get("name") == pod_name:
            print(f"✅ Pod details retrieved for: {pod_name}")
            return True
        else:
            print(f"❌ Pod details not matching: {pod_name}")
            return False
    else:
        print("❌ Operation failed")
        return False

def test_get_pod_logs(namespace, pod_name):
    """Test the get_pod_logs operation"""
    print(f"\n=== Testing get_pod_logs ({namespace}/{pod_name}) ===")
    response = call_operation("get_pod_logs", {
        "cluster_name": CLUSTER_NAME,
        "namespace": namespace,
        "pod_name": pod_name,
        "tail": 10,
        "region": REGION
    })
    print(f"MCP response: {json.dumps(response, indent=2)}")
    
    if response and response.get("status") == "success":
        logs = response.get("data", {}).get("logs", "")
        if logs:
            print(f"✅ Logs retrieved for pod: {pod_name}")
            return True
        else:
            print(f"❌ No logs found for pod: {pod_name}")
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
            print(f"❌ No nodegroups found")
            return []
    else:
        print("❌ Operation failed")
        return []

def test_describe_nodegroup(nodegroup_name):
    """Test the describe_nodegroup operation"""
    print(f"\n=== Testing describe_nodegroup ({nodegroup_name}) ===")
    response = call_operation("describe_nodegroup", {
        "cluster_name": CLUSTER_NAME,
        "nodegroup_name": nodegroup_name,
        "region": REGION
    })
    print(f"MCP response: {json.dumps(response, indent=2)}")
    
    if response and response.get("status") == "success":
        nodegroup = response.get("data", {}).get("nodegroup", {})
        if nodegroup and nodegroup.get("name") == nodegroup_name:
            print(f"✅ Nodegroup details retrieved for: {nodegroup_name}")
            return True
        else:
            print(f"❌ Nodegroup details not matching: {nodegroup_name}")
            return False
    else:
        print("❌ Operation failed")
        return False

def main():
    """Main function"""
    print("Starting EKS MCP Server kubectl operations test")
    print(f"Server URL: {SERVER_URL}")
    
    # Test health endpoint
    if not test_health():
        print("❌ Health check failed, aborting tests")
        sys.exit(1)
    
    # Test AWS operations
    nodegroups = test_list_nodegroups()
    if nodegroups:
        test_describe_nodegroup(nodegroups[0]["name"])
    
    # Test Kubernetes operations
    test_list_namespaces()
    
    # Test operations on test namespace
    pods = test_list_pods(TEST_NAMESPACE)
    deployments = test_get_deployments(TEST_NAMESPACE)
    services = test_get_services(TEST_NAMESPACE)
    
    # Test operations on test namespace 2
    pods2 = test_list_pods(TEST_NAMESPACE_2)
    deployments2 = test_get_deployments(TEST_NAMESPACE_2)
    services2 = test_get_services(TEST_NAMESPACE_2)
    
    # Test pod operations if pods were found
    if pods:
        pod_name = pods[0].get("name")
        test_describe_pod(TEST_NAMESPACE, pod_name)
        test_get_pod_logs(TEST_NAMESPACE, pod_name)
    
    # Test deployment operations if deployments were found
    if deployments:
        deployment_name = deployments[0].get("name")
        test_describe_deployment(TEST_NAMESPACE, deployment_name)
    
    print("\n=== Test Summary ===")
    print("✅ Completed testing all kubectl operations")

if __name__ == "__main__":
    main()
