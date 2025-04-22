"""
Kubernetes operations for the EKS MCP Server using AWS SDK
"""

import logging
import boto3
import base64
import json
import requests
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KubernetesOperationsSDK:
    """Class for Kubernetes operations using AWS SDK"""
    
    @staticmethod
    def get_cluster_info(cluster_name: str, region: str) -> Dict[str, Any]:
        """Get cluster information including endpoint and CA data"""
        try:
            eks_client = boto3.client('eks', region_name=region)
            response = eks_client.describe_cluster(name=cluster_name)
            return {
                'endpoint': response['cluster']['endpoint'],
                'ca_data': response['cluster']['certificateAuthority']['data']
            }
        except ClientError as e:
            logger.error(f"Error getting cluster info: {str(e)}")
            raise RuntimeError(f"Error getting cluster info: {str(e)}")
    
    @staticmethod
    def get_token(cluster_name: str, region: str) -> str:
        """Get a token for EKS authentication"""
        try:
            sts_client = boto3.client('sts', region_name=region)
            eks_client = boto3.client('eks', region_name=region)
            
            token = eks_client.get_token(clusterName=cluster_name)
            return token['token']
        except ClientError as e:
            logger.error(f"Error getting token: {str(e)}")
            raise RuntimeError(f"Error getting token: {str(e)}")
    
    @staticmethod
    def make_k8s_api_request(cluster_name: str, region: str, path: str, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Make a request to the Kubernetes API"""
        try:
            # Get cluster info
            cluster_info = KubernetesOperationsSDK.get_cluster_info(cluster_name, region)
            endpoint = cluster_info['endpoint']
            
            # Get token
            token = KubernetesOperationsSDK.get_token(cluster_name, region)
            
            # Build URL
            if namespace:
                url = f"{endpoint}/api/v1/namespaces/{namespace}/{path}"
            else:
                url = f"{endpoint}/api/v1/{path}"
            
            # Set headers
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            }
            
            # Make request
            logger.info(f"Making request to {url}")
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making Kubernetes API request: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise RuntimeError(f"Error making Kubernetes API request: {str(e)}")
    
    @staticmethod
    def get_namespaces(cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Get all namespaces in the cluster"""
        try:
            response = KubernetesOperationsSDK.make_k8s_api_request(cluster_name, region, "namespaces")
            
            namespaces = []
            for item in response.get("items", []):
                namespaces.append({
                    "name": item.get("metadata", {}).get("name"),
                    "status": item.get("status", {}).get("phase"),
                    "created": item.get("metadata", {}).get("creationTimestamp")
                })
                
            logger.info(f"Found {len(namespaces)} namespaces")
            return namespaces
        except Exception as e:
            logger.error(f"Error getting namespaces: {str(e)}")
            raise RuntimeError(f"Error getting namespaces: {str(e)}")
    
    @staticmethod
    def get_pods(cluster_name: str, namespace: str, region: str) -> List[Dict[str, Any]]:
        """Get all pods in a namespace"""
        try:
            response = KubernetesOperationsSDK.make_k8s_api_request(cluster_name, region, "pods", namespace)
            
            pods = []
            for item in response.get("items", []):
                pod_name = item.get("metadata", {}).get("name")
                pod_status = item.get("status", {}).get("phase")
                pod_ip = item.get("status", {}).get("podIP", "N/A")
                node_name = item.get("spec", {}).get("nodeName", "N/A")
                containers = len(item.get("spec", {}).get("containers", []))
                
                pods.append({
                    "name": pod_name,
                    "status": pod_status,
                    "node": node_name,
                    "ip": pod_ip,
                    "containers": containers
                })
                
            logger.info(f"Found {len(pods)} pods in namespace {namespace}")
            return pods
        except Exception as e:
            logger.error(f"Error getting pods: {str(e)}")
            raise RuntimeError(f"Error getting pods: {str(e)}")
    
    @staticmethod
    def describe_pod(cluster_name: str, namespace: str, pod_name: str, region: str) -> Dict[str, Any]:
        """Get detailed information about a pod"""
        try:
            response = KubernetesOperationsSDK.make_k8s_api_request(cluster_name, region, f"pods/{pod_name}", namespace)
            
            # Extract relevant information
            metadata = response.get("metadata", {})
            spec = response.get("spec", {})
            status = response.get("status", {})
            
            pod_info = {
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "uid": metadata.get("uid"),
                "creationTimestamp": metadata.get("creationTimestamp"),
                "labels": metadata.get("labels", {}),
                "nodeName": spec.get("nodeName"),
                "hostIP": status.get("hostIP"),
                "podIP": status.get("podIP"),
                "phase": status.get("phase"),
                "containers": []
            }
            
            # Extract container information
            for container in spec.get("containers", []):
                container_info = {
                    "name": container.get("name"),
                    "image": container.get("image"),
                    "ports": container.get("ports", []),
                    "resources": container.get("resources", {})
                }
                pod_info["containers"].append(container_info)
            
            logger.info(f"Retrieved details for pod {pod_name} in namespace {namespace}")
            return pod_info
        except Exception as e:
            logger.error(f"Error describing pod: {str(e)}")
            raise RuntimeError(f"Error describing pod: {str(e)}")
    
    @staticmethod
    def get_deployments(cluster_name: str, namespace: str, region: str) -> List[Dict[str, Any]]:
        """Get all deployments in a namespace"""
        try:
            # Deployments are in the apps/v1 API group
            cluster_info = KubernetesOperationsSDK.get_cluster_info(cluster_name, region)
            endpoint = cluster_info['endpoint']
            token = KubernetesOperationsSDK.get_token(cluster_name, region)
            
            url = f"{endpoint}/apis/apps/v1/namespaces/{namespace}/deployments"
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            }
            
            logger.info(f"Making request to {url}")
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            response_data = response.json()
            
            deployments = []
            for item in response_data.get("items", []):
                metadata = item.get("metadata", {})
                spec = item.get("spec", {})
                status = item.get("status", {})
                
                deployments.append({
                    "name": metadata.get("name"),
                    "namespace": metadata.get("namespace"),
                    "replicas": spec.get("replicas"),
                    "available": status.get("availableReplicas", 0),
                    "ready": status.get("readyReplicas", 0),
                    "updated": status.get("updatedReplicas", 0),
                    "created": metadata.get("creationTimestamp")
                })
                
            logger.info(f"Found {len(deployments)} deployments in namespace {namespace}")
            return deployments
        except Exception as e:
            logger.error(f"Error getting deployments: {str(e)}")
            raise RuntimeError(f"Error getting deployments: {str(e)}")
    
    @staticmethod
    def describe_deployment(cluster_name: str, namespace: str, deployment_name: str, region: str) -> Dict[str, Any]:
        """Get detailed information about a deployment"""
        try:
            # Deployments are in the apps/v1 API group
            cluster_info = KubernetesOperationsSDK.get_cluster_info(cluster_name, region)
            endpoint = cluster_info['endpoint']
            token = KubernetesOperationsSDK.get_token(cluster_name, region)
            
            url = f"{endpoint}/apis/apps/v1/namespaces/{namespace}/deployments/{deployment_name}"
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json'
            }
            
            logger.info(f"Making request to {url}")
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            response_data = response.json()
            
            # Extract relevant information
            metadata = response_data.get("metadata", {})
            spec = response_data.get("spec", {})
            status = response_data.get("status", {})
            
            deployment_info = {
                "name": metadata.get("name"),
                "namespace": metadata.get("namespace"),
                "uid": metadata.get("uid"),
                "creationTimestamp": metadata.get("creationTimestamp"),
                "labels": metadata.get("labels", {}),
                "replicas": spec.get("replicas"),
                "strategy": spec.get("strategy", {}).get("type"),
                "selector": spec.get("selector", {}).get("matchLabels", {}),
                "status": {
                    "availableReplicas": status.get("availableReplicas", 0),
                    "readyReplicas": status.get("readyReplicas", 0),
                    "updatedReplicas": status.get("updatedReplicas", 0),
                    "conditions": status.get("conditions", [])
                },
                "containers": []
            }
            
            # Extract container information from template
            template = spec.get("template", {}).get("spec", {})
            for container in template.get("containers", []):
                container_info = {
                    "name": container.get("name"),
                    "image": container.get("image"),
                    "ports": container.get("ports", []),
                    "resources": container.get("resources", {})
                }
                deployment_info["containers"].append(container_info)
            
            logger.info(f"Retrieved details for deployment {deployment_name} in namespace {namespace}")
            return deployment_info
        except Exception as e:
            logger.error(f"Error describing deployment: {str(e)}")
            raise RuntimeError(f"Error describing deployment: {str(e)}")
    
    @staticmethod
    def get_services(cluster_name: str, namespace: str, region: str) -> List[Dict[str, Any]]:
        """Get all services in a namespace"""
        try:
            response = KubernetesOperationsSDK.make_k8s_api_request(cluster_name, region, "services", namespace)
            
            services = []
            for item in response.get("items", []):
                metadata = item.get("metadata", {})
                spec = item.get("spec", {})
                
                services.append({
                    "name": metadata.get("name"),
                    "namespace": metadata.get("namespace"),
                    "type": spec.get("type"),
                    "clusterIP": spec.get("clusterIP"),
                    "externalIP": spec.get("externalIPs", ["None"])[0] if spec.get("externalIPs") else "None",
                    "ports": spec.get("ports", []),
                    "created": metadata.get("creationTimestamp")
                })
                
            logger.info(f"Found {len(services)} services in namespace {namespace}")
            return services
        except Exception as e:
            logger.error(f"Error getting services: {str(e)}")
            raise RuntimeError(f"Error getting services: {str(e)}")
    
    @staticmethod
    def get_pod_logs(cluster_name: str, namespace: str, pod_name: str, region: str, container: Optional[str] = None, tail: int = 100) -> str:
        """Get logs from a pod"""
        try:
            # Get cluster info
            cluster_info = KubernetesOperationsSDK.get_cluster_info(cluster_name, region)
            endpoint = cluster_info['endpoint']
            
            # Get token
            token = KubernetesOperationsSDK.get_token(cluster_name, region)
            
            # Build URL
            url = f"{endpoint}/api/v1/namespaces/{namespace}/pods/{pod_name}/log"
            
            # Add query parameters
            params = {'tailLines': str(tail)}
            if container:
                params['container'] = container
            
            # Set headers
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'text/plain'
            }
            
            # Make request
            logger.info(f"Making request to {url}")
            response = requests.get(url, headers=headers, params=params, verify=False)
            response.raise_for_status()
            
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting pod logs: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise RuntimeError(f"Error getting pod logs: {str(e)}")
