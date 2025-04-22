#!/usr/bin/env python3
"""
EKS MCP Client - A client library for interacting with the EKS MCP Server
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List, Union


class MCPClient:
    """
    Client for interacting with the EKS MCP Server API
    """

    def __init__(self, server_url: str = None, api_key: str = None, config_file: str = None):
        """
        Initialize the MCP Client
        
        Args:
            server_url: URL of the MCP server
            api_key: API key for authentication
            config_file: Path to a JSON config file containing server_url and api_key
        """
        self.server_url = server_url
        self.api_key = api_key
        
        # If config file is provided, load configuration from it
        if config_file:
            self._load_config(config_file)
        # If no config file but environment variables exist, use them
        elif not server_url or not api_key:
            self._load_from_env()
            
        # If still no configuration, try to load from default locations
        if not self.server_url or not self.api_key:
            default_config_paths = [
                os.path.join(os.getcwd(), 'client_config.json'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'client_config.json'),
                os.path.expanduser('~/.eks-mcp/config.json')
            ]
            
            for path in default_config_paths:
                if os.path.exists(path):
                    self._load_config(path)
                    break
        
        if not self.server_url:
            raise ValueError("MCP server URL not provided. Set it via constructor, config file, or MCP_SERVER_URL environment variable.")
        
        if not self.api_key:
            raise ValueError("MCP API key not provided. Set it via constructor, config file, or MCP_API_KEY environment variable.")
    
    def _load_config(self, config_file: str) -> None:
        """
        Load configuration from a JSON file
        
        Args:
            config_file: Path to the JSON config file
        """
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            self.server_url = config.get('mcp_server_url', self.server_url)
            self.api_key = config.get('mcp_api_key', self.api_key)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading config file: {e}")
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables"""
        if not self.server_url:
            self.server_url = os.environ.get('MCP_SERVER_URL')
        
        if not self.api_key:
            self.api_key = os.environ.get('MCP_API_KEY')
    
    def _make_request(self, operation: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make a request to the MCP server
        
        Args:
            operation: The operation to perform
            parameters: Parameters for the operation
            
        Returns:
            The response from the server
        """
        if parameters is None:
            parameters = {}
            
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key
        }
        
        payload = {
            'operation': operation,
            'parameters': parameters
        }
        
        try:
            response = requests.post(
                f"{self.server_url}/mcp/v1/query",
                headers=headers,
                json=payload
            )
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'data': None,
                'error': str(e),
                'error_code': 'REQUEST_ERROR'
            }
    
    def list_operations(self) -> Dict[str, Any]:
        """
        List all available operations
        
        Returns:
            A dictionary containing the available operations
        """
        headers = {
            'X-API-Key': self.api_key
        }
        
        try:
            response = requests.get(
                f"{self.server_url}/mcp/v1/operations",
                headers=headers
            )
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'data': None,
                'error': str(e),
                'error_code': 'REQUEST_ERROR'
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the MCP server
        
        Returns:
            A dictionary containing the health status
        """
        try:
            response = requests.get(f"{self.server_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                'status': 'error',
                'data': None,
                'error': str(e),
                'error_code': 'REQUEST_ERROR'
            }
    
    def list_clusters(self, region: str = 'us-east-1') -> Dict[str, Any]:
        """
        List all EKS clusters in a region
        
        Args:
            region: AWS region
            
        Returns:
            A dictionary containing the clusters
        """
        return self._make_request('list_clusters', {'region': region})
    
    def describe_cluster(self, cluster_name: str, region: str = 'us-east-1') -> Dict[str, Any]:
        """
        Get detailed information about an EKS cluster
        
        Args:
            cluster_name: Name of the EKS cluster
            region: AWS region
            
        Returns:
            A dictionary containing the cluster details
        """
        return self._make_request('describe_cluster', {
            'cluster_name': cluster_name,
            'region': region
        })
    
    def list_namespaces(self, cluster_name: str, region: str = 'us-east-1') -> Dict[str, Any]:
        """
        List all Kubernetes namespaces in an EKS cluster
        
        Args:
            cluster_name: Name of the EKS cluster
            region: AWS region
            
        Returns:
            A dictionary containing the namespaces
        """
        return self._make_request('list_namespaces', {
            'cluster_name': cluster_name,
            'region': region
        })
        
    def list_nodegroups(self, cluster_name: str, region: str = 'us-east-1') -> Dict[str, Any]:
        """
        List all nodegroups in an EKS cluster
        
        Args:
            cluster_name: Name of the EKS cluster
            region: AWS region
            
        Returns:
            A dictionary containing the nodegroups
        """
        return self._make_request('list_nodegroups', {
            'cluster_name': cluster_name,
            'region': region
        })
        
    def describe_nodegroup(self, cluster_name: str, nodegroup_name: str, region: str = 'us-east-1') -> Dict[str, Any]:
        """
        Get detailed information about a nodegroup in an EKS cluster
        
        Args:
            cluster_name: Name of the EKS cluster
            nodegroup_name: Name of the nodegroup
            region: AWS region
            
        Returns:
            A dictionary containing the nodegroup details
        """
        return self._make_request('describe_nodegroup', {
            'cluster_name': cluster_name,
            'nodegroup_name': nodegroup_name,
            'region': region
        })
        
    def list_pods(self, cluster_name: str, namespace: str, region: str = 'us-east-1') -> Dict[str, Any]:
        """
        List all pods in a namespace
        
        Args:
            cluster_name: Name of the EKS cluster
            namespace: Kubernetes namespace
            region: AWS region
            
        Returns:
            A dictionary containing the pods
        """
        return self._make_request('list_pods', {
            'cluster_name': cluster_name,
            'namespace': namespace,
            'region': region
        })
        
    def list_nodegroups(self, cluster_name: str, region: str = 'us-east-1') -> Dict[str, Any]:
        """
        List all nodegroups in an EKS cluster
        
        Args:
            cluster_name: Name of the EKS cluster
            region: AWS region
            
        Returns:
            A dictionary containing the nodegroups
        """
        return self._make_request('list_nodegroups', {
            'cluster_name': cluster_name,
            'region': region
        })
        
    def describe_nodegroup(self, cluster_name: str, nodegroup_name: str, region: str = 'us-east-1') -> Dict[str, Any]:
        """
        Get detailed information about a nodegroup in an EKS cluster
        
        Args:
            cluster_name: Name of the EKS cluster
            nodegroup_name: Name of the nodegroup
            region: AWS region
            
        Returns:
            A dictionary containing the nodegroup details
        """
        return self._make_request('describe_nodegroup', {
            'cluster_name': cluster_name,
            'nodegroup_name': nodegroup_name,
            'region': region
        })
        
    def list_pods(self, cluster_name: str, namespace: str, region: str = 'us-east-1') -> Dict[str, Any]:
        """
        List all pods in a namespace
        
        Args:
            cluster_name: Name of the EKS cluster
            namespace: Kubernetes namespace
            region: AWS region
            
        Returns:
            A dictionary containing the pods
        """
        return self._make_request('list_pods', {
            'cluster_name': cluster_name,
            'namespace': namespace,
            'region': region
        })
