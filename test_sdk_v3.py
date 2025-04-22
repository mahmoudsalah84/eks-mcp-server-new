#!/usr/bin/env python3
"""
Test script for EKS MCP Server SDK V3 operations
"""

import json
import sys
from k8s_operations_sdk_v3 import KubernetesOperationsSDKV3

# Test parameters
CLUSTER_NAME = "sample-eks-cluster"
REGION = "us-east-1"
TEST_NAMESPACE = "mcp-test-namespace"
TEST_NAMESPACE_2 = "mcp-test-namespace-2"

def test_get_namespaces():
    """Test the get_namespaces operation"""
    print("\n=== Testing get_namespaces ===")
    try:
        namespaces = KubernetesOperationsSDKV3.get_namespaces(CLUSTER_NAME, REGION)
        print(f"Found {len(namespaces)} namespaces:")
        for ns in namespaces:
            print(f"  - {ns['name']} ({ns['status']})")
        
        if TEST_NAMESPACE in [ns['name'] for ns in namespaces]:
            print(f"✅ Found test namespace: {TEST_NAMESPACE}")
        else:
            print(f"❌ Test namespace not found: {TEST_NAMESPACE}")
            
        return namespaces
    except Exception as e:
        print(f"❌ Error getting namespaces: {str(e)}")
        return []

def test_get_pods(namespace):
    """Test the get_pods operation"""
    print(f"\n=== Testing get_pods ({namespace}) ===")
    try:
        pods = KubernetesOperationsSDKV3.get_pods(CLUSTER_NAME, namespace, REGION)
        print(f"Found {len(pods)} pods in namespace {namespace}:")
        for pod in pods:
            print(f"  - {pod['name']} ({pod['status']})")
        return pods
    except Exception as e:
        print(f"❌ Error getting pods: {str(e)}")
        return []

def test_describe_pod(namespace, pod_name):
    """Test the describe_pod operation"""
    print(f"\n=== Testing describe_pod ({namespace}/{pod_name}) ===")
    try:
        pod_info = KubernetesOperationsSDKV3.describe_pod(CLUSTER_NAME, namespace, pod_name, REGION)
        print(f"Pod details for {pod_name}:")
        print(f"  Name: {pod_info['name']}")
        print(f"  Namespace: {pod_info['namespace']}")
        print(f"  Status: {pod_info['phase']}")
        print(f"  Node: {pod_info['nodeName']}")
        print(f"  IP: {pod_info['podIP']}")
        print(f"  Containers: {len(pod_info['containers'])}")
        return True
    except Exception as e:
        print(f"❌ Error describing pod: {str(e)}")
        return False

def test_get_deployments(namespace):
    """Test the get_deployments operation"""
    print(f"\n=== Testing get_deployments ({namespace}) ===")
    try:
        deployments = KubernetesOperationsSDKV3.get_deployments(CLUSTER_NAME, namespace, REGION)
        print(f"Found {len(deployments)} deployments in namespace {namespace}:")
        for deployment in deployments:
            print(f"  - {deployment['name']} (Replicas: {deployment['replicas']})")
        return deployments
    except Exception as e:
        print(f"❌ Error getting deployments: {str(e)}")
        return []

def test_describe_deployment(namespace, deployment_name):
    """Test the describe_deployment operation"""
    print(f"\n=== Testing describe_deployment ({namespace}/{deployment_name}) ===")
    try:
        deployment_info = KubernetesOperationsSDKV3.describe_deployment(CLUSTER_NAME, namespace, deployment_name, REGION)
        print(f"Deployment details for {deployment_name}:")
        print(f"  Name: {deployment_info['name']}")
        print(f"  Namespace: {deployment_info['namespace']}")
        print(f"  Replicas: {deployment_info['replicas']}")
        print(f"  Strategy: {deployment_info['strategy']}")
        print(f"  Containers: {len(deployment_info['containers'])}")
        return True
    except Exception as e:
        print(f"❌ Error describing deployment: {str(e)}")
        return False

def test_get_services(namespace):
    """Test the get_services operation"""
    print(f"\n=== Testing get_services ({namespace}) ===")
    try:
        services = KubernetesOperationsSDKV3.get_services(CLUSTER_NAME, namespace, REGION)
        print(f"Found {len(services)} services in namespace {namespace}:")
        for service in services:
            print(f"  - {service['name']} (Type: {service['type']}, IP: {service['clusterIP']})")
        return services
    except Exception as e:
        print(f"❌ Error getting services: {str(e)}")
        return []

def test_get_pod_logs(namespace, pod_name):
    """Test the get_pod_logs operation"""
    print(f"\n=== Testing get_pod_logs ({namespace}/{pod_name}) ===")
    try:
        logs = KubernetesOperationsSDKV3.get_pod_logs(CLUSTER_NAME, namespace, pod_name, REGION, tail=10)
        print(f"Logs for pod {pod_name} (first 200 chars):")
        print(logs[:200] + "..." if len(logs) > 200 else logs)
        return True
    except Exception as e:
        print(f"❌ Error getting pod logs: {str(e)}")
        return False

def test_list_nodegroups():
    """Test the list_nodegroups operation"""
    print("\n=== Testing list_nodegroups ===")
    try:
        nodegroups = KubernetesOperationsSDKV3.list_nodegroups(CLUSTER_NAME, REGION)
        print(f"Found {len(nodegroups)} nodegroups:")
        for ng in nodegroups:
            print(f"  - {ng['name']} ({ng['status']}, {ng['instanceType']})")
        return nodegroups
    except Exception as e:
        print(f"❌ Error listing nodegroups: {str(e)}")
        return []

def test_describe_nodegroup(nodegroup_name):
    """Test the describe_nodegroup operation"""
    print(f"\n=== Testing describe_nodegroup ({nodegroup_name}) ===")
    try:
        nodegroup_info = KubernetesOperationsSDKV3.describe_nodegroup(CLUSTER_NAME, nodegroup_name, REGION)
        print(f"Nodegroup details for {nodegroup_name}:")
        print(f"  Name: {nodegroup_info['name']}")
        print(f"  Status: {nodegroup_info['status']}")
        print(f"  Instance Types: {', '.join(nodegroup_info['instanceTypes'])}")
        print(f"  Capacity Type: {nodegroup_info['capacityType']}")
        print(f"  Scaling Config: Min={nodegroup_info['scalingConfig']['minSize']}, Max={nodegroup_info['scalingConfig']['maxSize']}, Desired={nodegroup_info['scalingConfig']['desiredSize']}")
        return True
    except Exception as e:
        print(f"❌ Error describing nodegroup: {str(e)}")
        return False

def main():
    """Main function"""
    print("Starting EKS MCP Server SDK V3 operations test")
    
    # Test AWS operations
    nodegroups = test_list_nodegroups()
    if nodegroups:
        test_describe_nodegroup(nodegroups[0]['name'])
    
    # Test get_namespaces
    namespaces = test_get_namespaces()
    if not namespaces:
        print("❌ Failed to get namespaces, aborting further tests")
        sys.exit(1)
    
    # Test operations on test namespace
    pods = test_get_pods(TEST_NAMESPACE)
    deployments = test_get_deployments(TEST_NAMESPACE)
    services = test_get_services(TEST_NAMESPACE)
    
    # Test pod operations if pods were found
    if pods:
        pod_name = pods[0]['name']
        test_describe_pod(TEST_NAMESPACE, pod_name)
        test_get_pod_logs(TEST_NAMESPACE, pod_name)
    
    # Test deployment operations if deployments were found
    if deployments:
        deployment_name = deployments[0]['name']
        test_describe_deployment(TEST_NAMESPACE, deployment_name)
    
    print("\n=== Test Summary ===")
    print("✅ Completed testing all SDK V3 operations")

if __name__ == "__main__":
    main()
