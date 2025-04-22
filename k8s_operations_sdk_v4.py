"""
Kubernetes operations for the EKS MCP Server using AWS SDK - Version 4
Direct API calls to Kubernetes API server using DirectK8sClient
"""

import logging
import boto3
from typing import Dict, List, Any, Optional
from direct_k8s_client import DirectK8sClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KubernetesOperationsSDKV4:
    """Class for Kubernetes operations using AWS SDK with direct API calls"""
    
    @staticmethod
    def get_namespaces(cluster_name: str, region: str) -> List[Dict[str, Any]]:
        """Get all namespaces in the cluster"""
        try:
            client = DirectK8sClient(cluster_name, region)
            namespaces = client.get_namespaces()
            logger.info(f"Found {len(namespaces)} namespaces")
            return namespaces
        except Exception as e:
            logger.error(f"Error getting namespaces: {str(e)}")
            raise RuntimeError(f"Error getting namespaces: {str(e)}")
    
    @staticmethod
    def get_pods(cluster_name: str, namespace: str, region: str) -> List[Dict[str, Any]]:
        """Get all pods in a namespace"""
        try:
            client = DirectK8sClient(cluster_name, region)
            pods = client.get_pods(namespace)
            logger.info(f"Found {len(pods)} pods in namespace {namespace}")
            return pods
        except Exception as e:
            logger.error(f"Error getting pods: {str(e)}")
            raise RuntimeError(f"Error getting pods: {str(e)}")
    
    @staticmethod
    def describe_pod(cluster_name: str, namespace: str, pod_name: str, region: str) -> Dict[str, Any]:
        """Get detailed information about a pod"""
        try:
            client = DirectK8sClient(cluster_name, region)
            pod_info = client.describe_pod(namespace, pod_name)
            logger.info(f"Retrieved details for pod {pod_name} in namespace {namespace}")
            return pod_info
        except Exception as e:
            logger.error(f"Error describing pod: {str(e)}")
            raise RuntimeError(f"Error describing pod: {str(e)}")
    
    @staticmethod
    def get_deployments(cluster_name: str, namespace: str, region: str) -> List[Dict[str, Any]]:
        """Get all deployments in a namespace"""
        try:
            client = DirectK8sClient(cluster_name, region)
            deployments = client.get_deployments(namespace)
            logger.info(f"Found {len(deployments)} deployments in namespace {namespace}")
            return deployments
        except Exception as e:
            logger.error(f"Error getting deployments: {str(e)}")
            raise RuntimeError(f"Error getting deployments: {str(e)}")
    
    @staticmethod
    def describe_deployment(cluster_name: str, namespace: str, deployment_name: str, region: str) -> Dict[str, Any]:
        """Get detailed information about a deployment"""
        try:
            client = DirectK8sClient(cluster_name, region)
            deployment_info = client.describe_deployment(namespace, deployment_name)
            logger.info(f"Retrieved details for deployment {deployment_name} in namespace {namespace}")
            return deployment_info
        except Exception as e:
            logger.error(f"Error describing deployment: {str(e)}")
            raise RuntimeError(f"Error describing deployment: {str(e)}")
    
    @staticmethod
    def get_services(cluster_name: str, namespace: str, region: str) -> List[Dict[str, Any]]:
        """Get all services in a namespace"""
        try:
            client = DirectK8sClient(cluster_name, region)
            services = client.get_services(namespace)
            logger.info(f"Found {len(services)} services in namespace {namespace}")
            return services
        except Exception as e:
            logger.error(f"Error getting services: {str(e)}")
            raise RuntimeError(f"Error getting services: {str(e)}")
    
    @staticmethod
    def get_pod_logs(cluster_name: str, namespace: str, pod_name: str, region: str, container: Optional[str] = None, tail: int = 100) -> str:
        """Get logs from a pod"""
        try:
            client = DirectK8sClient(cluster_name, region)
            logs = client.get_pod_logs(namespace, pod_name, container, tail)
            logger.info(f"Retrieved logs for pod {pod_name} in namespace {namespace}")
            return logs
        except Exception as e:
            logger.error(f"Error getting pod logs: {str(e)}")
            raise RuntimeError(f"Error getting pod logs: {str(e)}")
    
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
                "clusterName": nodegroup.get('clusterName'),
                "instanceType": nodegroup.get('instanceTypes', ['unknown'])[0] if nodegroup.get('instanceTypes') else 'unknown',
                "desiredSize": nodegroup.get('scalingConfig', {}).get('desiredSize'),
                "minSize": nodegroup.get('scalingConfig', {}).get('minSize'),
                "maxSize": nodegroup.get('scalingConfig', {}).get('maxSize'),
                "created": nodegroup.get('createdAt'),
                "amiType": nodegroup.get('amiType'),
                "diskSize": nodegroup.get('diskSize'),
                "subnets": nodegroup.get('subnets', []),
                "remoteAccess": nodegroup.get('remoteAccess', {}),
                "tags": nodegroup.get('tags', {}),
                "health": nodegroup.get('health', {})
            }
            
            logger.info(f"Retrieved details for nodegroup {nodegroup_name} in cluster {cluster_name}")
            return nodegroup_info
        except Exception as e:
            logger.error(f"Error describing nodegroup: {str(e)}")
            raise RuntimeError(f"Error describing nodegroup: {str(e)}")
