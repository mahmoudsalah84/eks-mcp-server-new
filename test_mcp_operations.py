#!/usr/bin/env python3
"""
Test script for MCP operations
This script tests all MCP operations and compares them with AWS CLI output
"""

import requests
import json
import subprocess
import sys
import time

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

# Function to run AWS CLI command
def run_aws_cli(command):
    try:
        print(f"Running AWS CLI command: {command}")
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        return {'error': e.stderr}
    except json.JSONDecodeError:
        return {'error': 'Invalid JSON in AWS CLI output'}

# Test list_clusters
print('\n=== Testing list_clusters ===')
mcp_clusters = call_mcp('list_clusters', {'region': 'us-east-1'})
print('MCP response:', json.dumps(mcp_clusters, indent=2))

aws_clusters = run_aws_cli('aws eks list-clusters --region us-east-1')
print('AWS CLI response:', json.dumps(aws_clusters, indent=2))

# Get first cluster name if available
cluster_name = None
if mcp_clusters.get('status') == 'success' and mcp_clusters.get('data', {}).get('clusters'):
    cluster_name = mcp_clusters['data']['clusters'][0]
elif aws_clusters.get('clusters'):
    cluster_name = aws_clusters['clusters'][0]

if not cluster_name:
    print('No clusters found to test with')
    sys.exit(0)

print(f'\nUsing cluster: {cluster_name} for further tests')

# Test describe_cluster
print('\n=== Testing describe_cluster ===')
mcp_cluster = call_mcp('describe_cluster', {'cluster_name': cluster_name, 'region': 'us-east-1'})
print('MCP response:', json.dumps(mcp_cluster, indent=2))

aws_cluster = run_aws_cli(f'aws eks describe-cluster --name {cluster_name} --region us-east-1')
print('AWS CLI response:', json.dumps(aws_cluster, indent=2))

# Test list_namespaces
print('\n=== Testing list_namespaces ===')
mcp_namespaces = call_mcp('list_namespaces', {'cluster_name': cluster_name, 'region': 'us-east-1'})
print('MCP response:', json.dumps(mcp_namespaces, indent=2))

# Test list_nodegroups
print('\n=== Testing list_nodegroups ===')
mcp_nodegroups = call_mcp('list_nodegroups', {'cluster_name': cluster_name, 'region': 'us-east-1'})
print('MCP response:', json.dumps(mcp_nodegroups, indent=2))

aws_nodegroups = run_aws_cli(f'aws eks list-nodegroups --cluster-name {cluster_name} --region us-east-1')
print('AWS CLI response:', json.dumps(aws_nodegroups, indent=2))

# Get first nodegroup name if available
nodegroup_name = None
if mcp_nodegroups.get('status') == 'success' and mcp_nodegroups.get('data', {}).get('nodegroups'):
    nodegroup_name = mcp_nodegroups['data']['nodegroups'][0]
elif aws_nodegroups.get('nodegroups'):
    nodegroup_name = aws_nodegroups['nodegroups'][0]

# Test describe_nodegroup if we have a nodegroup
if nodegroup_name:
    print(f'\nUsing nodegroup: {nodegroup_name} for further tests')
    print('\n=== Testing describe_nodegroup ===')
    mcp_nodegroup = call_mcp('describe_nodegroup', 
                           {'cluster_name': cluster_name, 'nodegroup_name': nodegroup_name, 'region': 'us-east-1'})
    print('MCP response:', json.dumps(mcp_nodegroup, indent=2))

    aws_nodegroup = run_aws_cli(f'aws eks describe-nodegroup --cluster-name {cluster_name} --nodegroup-name {nodegroup_name} --region us-east-1')
    print('AWS CLI response:', json.dumps(aws_nodegroup, indent=2))

# Test list_pods with default namespace
print('\n=== Testing list_pods (default namespace) ===')
mcp_pods_default = call_mcp('list_pods', {'cluster_name': cluster_name, 'namespace': 'default', 'region': 'us-east-1'})
print('MCP response:', json.dumps(mcp_pods_default, indent=2))

# Test list_pods with kube-system namespace
print('\n=== Testing list_pods (kube-system namespace) ===')
mcp_pods_system = call_mcp('list_pods', {'cluster_name': cluster_name, 'namespace': 'kube-system', 'region': 'us-east-1'})
print('MCP response:', json.dumps(mcp_pods_system, indent=2))

# Test list_pods with a custom namespace
print('\n=== Testing list_pods (custom namespace) ===')
mcp_pods_custom = call_mcp('list_pods', {'cluster_name': cluster_name, 'namespace': 'custom-ns', 'region': 'us-east-1'})
print('MCP response:', json.dumps(mcp_pods_custom, indent=2))
