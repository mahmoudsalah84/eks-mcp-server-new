#!/usr/bin/env python3
"""
Test script for MCP operations with the new namespace (without modifying mock data)
"""

import requests
import json
import sys

# Load config
with open('client_config.json') as f:
    config = json.load(f)

server_url = config['mcp_server_url']
api_key = config['mcp_api_key']
headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}

# Function to call MCP server
def call_mcp(operation, params={}):
    payload = {'operation': operation, 'parameters': params}
    try:
        print(f"Calling MCP operation: {operation} with parameters: {json.dumps(params)}")
        response = requests.post(f'{server_url}/mcp/v1/query', 
                                headers=headers, 
                                json=payload)
        return response.json()
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

# Test list_namespaces
print('\n=== Testing list_namespaces ===')
mcp_namespaces = call_mcp('list_namespaces', {'cluster_name': 'sample-eks-cluster', 'region': 'us-east-1'})
print('MCP response:', json.dumps(mcp_namespaces, indent=2))

# Check if mcp-test-namespace-2 is in the response
found_namespace = False
if mcp_namespaces.get('status') == 'success':
    namespaces = mcp_namespaces.get('data', {}).get('namespaces', [])
    for ns in namespaces:
        if ns.get('name') == 'mcp-test-namespace-2':
            found_namespace = True
            print("\n✅ mcp-test-namespace-2 found in MCP response!")
            break

if not found_namespace:
    print("\n❌ mcp-test-namespace-2 NOT found in MCP response.")
    print("This is expected if the server is using static mock data without this namespace.")

# Test list_pods with the new namespace
print('\n=== Testing list_pods (mcp-test-namespace-2) ===')
mcp_pods = call_mcp('list_pods', {'cluster_name': 'sample-eks-cluster', 'namespace': 'mcp-test-namespace-2', 'region': 'us-east-1'})
print('MCP response:', json.dumps(mcp_pods, indent=2))

# Check if pods are returned
if mcp_pods.get('status') == 'success':
    pods = mcp_pods.get('data', {}).get('pods', [])
    if pods:
        print(f"\n✅ Found {len(pods)} pods in mcp-test-namespace-2!")
        
        # Check if the pod names match the expected format for mock data or real data
        mock_data = False
        for pod in pods:
            if pod.get('name').startswith('mcp-test-namespace-2-'):
                mock_data = True
                break
        
        if mock_data:
            print("\nℹ️ The server is returning mock data with namespace-prefixed pod names.")
        else:
            print("\nℹ️ The server might be returning real data from the Kubernetes API.")
    else:
        print("\n❌ No pods found in mcp-test-namespace-2.")
else:
    print(f"\n❌ Error getting pods: {mcp_pods.get('error')}")

print("\nNote: The MCP server is currently using mock data for Kubernetes resources.")
print("To get real data, the server would need to be configured with kubectl access to the EKS cluster.")

# Try to get real namespace data using kubectl directly
print("\n=== Comparing with kubectl output ===")
try:
    import subprocess
    result = subprocess.run(
        ["kubectl", "get", "namespaces"],
        capture_output=True,
        text=True,
        check=True
    )
    print("kubectl namespaces output:")
    print(result.stdout)
    
    result = subprocess.run(
        ["kubectl", "get", "pods", "-n", "mcp-test-namespace-2"],
        capture_output=True,
        text=True,
        check=True
    )
    print("\nkubectl pods output for mcp-test-namespace-2:")
    print(result.stdout)
except Exception as e:
    print(f"Error running kubectl: {str(e)}")
