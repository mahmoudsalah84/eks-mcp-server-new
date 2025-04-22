#!/usr/bin/env python3
"""
EKS MCP CLI - Command Line Interface for the EKS MCP Client
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, Optional, List
from client.mcp_client import MCPClient


def format_output(data: Dict[str, Any], output_format: str = 'json') -> str:
    """
    Format the output data
    
    Args:
        data: The data to format
        output_format: The format to use (json or table)
        
    Returns:
        The formatted output
    """
    if output_format == 'json':
        return json.dumps(data, indent=2)
    else:
        # Simple table format for now
        if data.get('status') == 'error':
            return f"ERROR: {data.get('error', 'Unknown error')}"
        
        result = []
        if data.get('data'):
            if 'clusters' in data['data']:
                result.append("CLUSTERS:")
                for cluster in data['data']['clusters']:
                    result.append(f"  - {cluster}")
            
            elif 'cluster' in data['data']:
                cluster = data['data']['cluster']
                result.append(f"CLUSTER: {cluster.get('name', 'Unknown')}")
                result.append(f"  Status: {cluster.get('status', 'Unknown')}")
                result.append(f"  Version: {cluster.get('version', 'Unknown')}")
                result.append(f"  Created: {cluster.get('createdAt', 'Unknown')}")
                result.append(f"  Endpoint: {cluster.get('endpoint', 'Unknown')}")
            
            elif 'namespaces' in data['data']:
                result.append("NAMESPACES:")
                for ns in data['data']['namespaces']:
                    result.append(f"  - {ns.get('name', 'Unknown')} ({ns.get('status', 'Unknown')})")
            
            elif 'operations' in data['data']:
                result.append("AVAILABLE OPERATIONS:")
                for op in data['data']['operations']:
                    params = ", ".join([f"{p['name']}" + (" (required)" if p.get('required') else "") for p in op.get('parameters', [])])
                    result.append(f"  - {op['name']}: {op.get('description', '')}")
                    result.append(f"    Parameters: {params}")
        
        return "\n".join(result)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='EKS MCP CLI')
    parser.add_argument('--server', '-s', help='MCP server URL')
    parser.add_argument('--api-key', '-k', help='MCP API key')
    parser.add_argument('--config', '-c', help='Path to config file')
    parser.add_argument('--output', '-o', choices=['json', 'table'], default='json', help='Output format')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Health check command
    health_parser = subparsers.add_parser('health', help='Check server health')
    
    # List operations command
    ops_parser = subparsers.add_parser('operations', help='List available operations')
    
    # List clusters command
    clusters_parser = subparsers.add_parser('list-clusters', help='List EKS clusters')
    clusters_parser.add_argument('--region', '-r', default='us-east-1', help='AWS region')
    
    # Describe cluster command
    describe_parser = subparsers.add_parser('describe-cluster', help='Describe an EKS cluster')
    describe_parser.add_argument('cluster_name', help='Name of the EKS cluster')
    describe_parser.add_argument('--region', '-r', default='us-east-1', help='AWS region')
    
    # List namespaces command
    ns_parser = subparsers.add_parser('list-namespaces', help='List Kubernetes namespaces')
    ns_parser.add_argument('cluster_name', help='Name of the EKS cluster')
    ns_parser.add_argument('--region', '-r', default='us-east-1', help='AWS region')
    
    args = parser.parse_args()
    
    # If no command is provided, show help
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        # Initialize the client
        client = MCPClient(
            server_url=args.server,
            api_key=args.api_key,
            config_file=args.config
        )
        
        # Execute the command
        if args.command == 'health':
            result = client.health_check()
        elif args.command == 'operations':
            result = client.list_operations()
        elif args.command == 'list-clusters':
            result = client.list_clusters(region=args.region)
        elif args.command == 'describe-cluster':
            result = client.describe_cluster(cluster_name=args.cluster_name, region=args.region)
        elif args.command == 'list-namespaces':
            result = client.list_namespaces(cluster_name=args.cluster_name, region=args.region)
        else:
            print(f"Unknown command: {args.command}")
            sys.exit(1)
        
        # Format and print the output
        print(format_output(result, args.output))
        
        # Exit with error code if the request failed
        if result.get('status') == 'error':
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
