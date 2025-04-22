#!/usr/bin/env python3
"""
Test script for MCP operations with the new namespace
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

# Check if mcp-test-namespace is in the response
found_namespace = False
if mcp_namespaces.get('status') == 'success':
    namespaces = mcp_namespaces.get('data', {}).get('namespaces', [])
    for ns in namespaces:
        if ns.get('name') == 'mcp-test-namespace':
            found_namespace = True
            print("\n✅ mcp-test-namespace found in MCP response!")
            break

if not found_namespace:
    print("\n❌ mcp-test-namespace NOT found in MCP response.")
    print("Note: The MCP server is currently using mock data for Kubernetes resources.")

# Test list_pods with the new namespace
print('\n=== Testing list_pods (mcp-test-namespace) ===')
mcp_pods = call_mcp('list_pods', {'cluster_name': 'sample-eks-cluster', 'namespace': 'mcp-test-namespace', 'region': 'us-east-1'})
print('MCP response:', json.dumps(mcp_pods, indent=2))

# Check if pods are returned
if mcp_pods.get('status') == 'success':
    pods = mcp_pods.get('data', {}).get('pods', [])
    if pods:
        print(f"\n✅ Found {len(pods)} pods in mcp-test-namespace!")
    else:
        print("\n❌ No pods found in mcp-test-namespace.")
else:
    print(f"\n❌ Error getting pods: {mcp_pods.get('error')}")

print("\nNote: The MCP server is currently using mock data for Kubernetes resources.")
print("To get real data, the server would need to be configured with kubectl access to the EKS cluster.")
