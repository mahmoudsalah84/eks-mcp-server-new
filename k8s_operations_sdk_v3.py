"""
Kubernetes operations for the EKS MCP Server using AWS SDK - Version 3
Direct API calls to Kubernetes API server without kubectl
"""

import logging
import boto3
import base64
import json
import requests
import tempfile
import os
import time
import subprocess
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KubernetesOperationsSDKV3:
    """Class for Kubernetes operations using AWS SDK with direct API calls"""
    
    @staticmethod
    def get_eks_token(cluster_name: str, region: str) -> str:
        """Get a token for EKS authentication using AWS CLI"""
        try:
            # Use AWS CLI to get the token - this is more reliable than using boto3 directly
            cmd = f"aws eks get-token --cluster-name {cluster_name} --region {region}"
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            token_data = json.loads(result.stdout)
            return token_data['status']['token']
        except Exception as e:
            logger.error(f"Error getting EKS token via CLI: {str(e)}")
            
            # Fall back to using boto3 directly
            try:
                # Create a STS client
                sts_client = boto3.client('sts', region_name=region)
                
                # Get caller identity to verify permissions
                identity = sts_client.get_caller_identity()
                logger.info(f"Current identity: {identity['Arn']}")
                
                # Create a presigned URL for EKS authentication
                eks_client = boto3.client('eks', region_name=region)
                presigned_url = eks_client.meta.client.generate_presigned_url(
                    'get_token',
                    Params={'cluster_name': cluster_name},
                    ExpiresIn=60
                )
                
                # Extract token from presigned URL
                token = presigned_url.split('?')[1]
                
                return token
            except Exception as fallback_error:
                logger.error(f"Error getting EKS token via boto3 fallback: {str(fallback_error)}")
                raise RuntimeError(f"Error getting EKS token: {str(fallback_error)}")
    
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
        except Exception as e:
            logger.error(f"Error getting cluster info: {str(e)}")
            raise RuntimeError(f"Error getting cluster info: {str(e)}")
    
    @staticmethod
    def make_k8s_api_call(cluster_name: str, region: str, api_path: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a direct API call to the Kubernetes API server"""
        try:
            # Get cluster info
            cluster_info = KubernetesOperationsSDKV3.get_cluster_info(cluster_name, region)
            endpoint = cluster_info['endpoint']
            ca_data = cluster_info['ca_data']
            
            # Get token
            token = KubernetesOperationsSDKV3.get_eks_token(cluster_name, region)
            
            # Build URL
            url = f"{endpoint}{api_path}"
            
            # Set headers
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            # Create a temporary CA file
            ca_file = None
            try:
                fd, ca_file = tempfile.mkstemp(prefix='eks-ca-', suffix='.crt')
                with os.fdopen(fd, 'w') as f:
                    f.write(base64.b64decode(ca_data).decode('utf-8'))
                
                # Make request
                if method == 'GET':
                    response = requests.get(url, headers=headers, verify=ca_file)
                elif method == 'POST':
                    response = requests.post(url, headers=headers, json=data, verify=ca_file)
                elif method == 'PUT':
                    response = requests.put(url, headers=headers, json=data, verify=ca_file)
                elif method == 'DELETE':
                    response = requests.delete(url, headers=headers, verify=ca_file)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                return response.json()
            finally:
                # Clean up
                if ca_file and os.path.exists(ca_file):
                    os.remove(ca_file)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making Kubernetes API call: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise RuntimeError(f"Error making Kubernetes API call: {str(e)}")
        except Exception as e:
            logger.error(f"Error in make_k8s_api_call: {str(e)}")
            raise RuntimeError(f"Error in make_k8s_api_call: {str(e)}")
    
    @staticmethod
    def get_namespaces(cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Get all namespaces in the cluster"""
        try:
            # Make API call
            response = KubernetesOperationsSDKV3.make_k8s_api_call(
                cluster_name, 
                region, 
                '/api/v1/namespaces'
            )
            
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
            # Make API call
            response = KubernetesOperationsSDKV3.make_k8s_api_call(
                cluster_name, 
                region, 
                f'/api/v1/namespaces/{namespace}/pods'
            )
            
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
            # Make API call
            response = KubernetesOperationsSDKV3.make_k8s_api_call(
                cluster_name, 
                region, 
                f'/api/v1/namespaces/{namespace}/pods/{pod_name}'
            )
            
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
            # Make API call
            response = KubernetesOperationsSDKV3.make_k8s_api_call(
                cluster_name, 
                region, 
                f'/apis/apps/v1/namespaces/{namespace}/deployments'
            )
            
            deployments = []
            for item in response.get("items", []):
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
            # Make API call
            response = KubernetesOperationsSDKV3.make_k8s_api_call(
                cluster_name, 
                region, 
                f'/apis/apps/v1/namespaces/{namespace}/deployments/{deployment_name}'
            )
            
            # Extract relevant information
            metadata = response.get("metadata", {})
            spec = response.get("spec", {})
            status = response.get("status", {})
            
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
            # Make API call
            response = KubernetesOperationsSDKV3.make_k8s_api_call(
                cluster_name, 
                region, 
                f'/api/v1/namespaces/{namespace}/services'
            )
            
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
            # Build API path
            api_path = f'/api/v1/namespaces/{namespace}/pods/{pod_name}/log?tailLines={tail}'
            if container:
                api_path += f'&container={container}'
            
            # Get cluster info
            cluster_info = KubernetesOperationsSDKV3.get_cluster_info(cluster_name, region)
            endpoint = cluster_info['endpoint']
            ca_data = cluster_info['ca_data']
            
            # Get token
            token = KubernetesOperationsSDKV3.get_eks_token(cluster_name, region)
            
            # Build URL
            url = f"{endpoint}{api_path}"
            
            # Set headers
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'text/plain'
            }
            
            # Create a temporary CA file
            ca_file = None
            try:
                fd, ca_file = tempfile.mkstemp(prefix='eks-ca-', suffix='.crt')
                with os.fdopen(fd, 'w') as f:
                    f.write(base64.b64decode(ca_data).decode('utf-8'))
                
                # Make request
                response = requests.get(url, headers=headers, verify=ca_file)
                response.raise_for_status()
                return response.text
            finally:
                # Clean up
                if ca_file and os.path.exists(ca_file):
                    os.remove(ca_file)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting pod logs: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise RuntimeError(f"Error getting pod logs: {str(e)}")
        except Exception as e:
            logger.error(f"Error in get_pod_logs: {str(e)}")
            raise RuntimeError(f"Error in get_pod_logs: {str(e)}")
    
    @staticmethod
    def list_nodegroups(cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """List all nodegroups in an EKS cluster"""
        try:
            eks_client = boto3.client('eks', region_name=region)
            response = eks_client.list_nodegroups(clusterName=cluster_name)
            
            nodegroups = []
            for nodegroup_name in response.get('nodegroups', []):
                nodegroup_info = eks_client.describe_nodegroup(
                    clusterName=cluster_name,
                    nodegroupName=nodegroup_name
                )
                
                nodegroups.append({
                    "name": nodegroup_name,
                    "status": nodegroup_info.get('nodegroup', {}).get('status'),
                    "instanceType": nodegroup_info.get('nodegroup', {}).get('instanceTypes', ['unknown'])[0],
                    "capacityType": nodegroup_info.get('nodegroup', {}).get('capacityType', 'unknown'),
                    "desiredSize": nodegroup_info.get('nodegroup', {}).get('scalingConfig', {}).get('desiredSize'),
                    "minSize": nodegroup_info.get('nodegroup', {}).get('scalingConfig', {}).get('minSize'),
                    "maxSize": nodegroup_info.get('nodegroup', {}).get('scalingConfig', {}).get('maxSize'),
                    "createdAt": nodegroup_info.get('nodegroup', {}).get('createdAt')
                })
            
            logger.info(f"Found {len(nodegroups)} nodegroups in cluster {cluster_name}")
            return nodegroups
        except Exception as e:
            logger.error(f"Error listing nodegroups: {str(e)}")
            raise RuntimeError(f"Error listing nodegroups: {str(e)}")
    
    @staticmethod
    def describe_nodegroup(cluster_name: str, nodegroup_name: str, region: str) -> Dict[str, Any]:
        """Get detailed information about a nodegroup"""
        try:
            eks_client = boto3.client('eks', region_name=region)
            response = eks_client.describe_nodegroup(
                clusterName=cluster_name,
                nodegroupName=nodegroup_name
            )
            
            nodegroup = response.get('nodegroup', {})
            
            nodegroup_info = {
                "name": nodegroup.get('nodegroupName'),
                "status": nodegroup.get('status'),
                "instanceTypes": nodegroup.get('instanceTypes', []),
                "capacityType": nodegroup.get('capacityType'),
                "diskSize": nodegroup.get('diskSize'),
                "subnets": nodegroup.get('subnets', []),
                "amiType": nodegroup.get('amiType'),
                "remoteAccess": nodegroup.get('remoteAccess'),
                "scalingConfig": nodegroup.get('scalingConfig', {}),
                "labels": nodegroup.get('labels', {}),
                "taints": nodegroup.get('taints', []),
                "resources": nodegroup.get('resources', {}),
                "health": nodegroup.get('health', {}),
                "createdAt": nodegroup.get('createdAt'),
                "modifiedAt": nodegroup.get('modifiedAt')
            }
            
            logger.info(f"Retrieved details for nodegroup {nodegroup_name} in cluster {cluster_name}")
            return nodegroup_info
        except Exception as e:
            logger.error(f"Error describing nodegroup: {str(e)}")
            raise RuntimeError(f"Error describing nodegroup: {str(e)}")
