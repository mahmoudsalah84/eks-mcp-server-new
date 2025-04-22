# EKS Model Context Protocol (MCP) Server

A lightweight, efficient server that implements the Model Context Protocol for EKS operations. This server provides a standardized interface for GenAI agents to interact with EKS clusters.

## Features

- Fast response times with proper timeout handling
- Comprehensive EKS operations support
- Kubernetes resource management (pods, services, deployments, etc.)
- Multiple authentication methods for EKS clusters
- Robust error handling and logging
- Docker containerization for easy deployment
- ECS deployment support

## Project Structure

- `main.py`: Main server implementation with FastAPI
- `eks_operations.py`: EKS API operations implementation
- `k8s_operations.py`: Kubernetes API operations implementation
- `k8s_operations_sdk_v4.py`: SDK-based Kubernetes operations implementation
- `k8s_operations_kubectl.py`: Kubectl-based Kubernetes operations with proper authentication
- `k8s_auth_config.py`: Authentication configuration for Kubernetes
- `direct_k8s_client.py`: Direct Kubernetes API client implementation
- `test_*.py`: Various test scripts for different implementations
- `Dockerfile` and `Dockerfile.amd64`: Docker configuration files
- `docker-compose.yml`: Docker Compose configuration
- `requirements.txt`: Python dependencies
- `client/`: Client implementation directory ([Client README](client/README.md))
- `ecs-deployment/`: ECS deployment scripts and configuration ([ECS Deployment README](ecs-deployment/README.md))

## API Endpoints

- `GET /health` - Health check endpoint
- `GET /mcp/v1/operations` - List available operations
- `POST /mcp/v1/query` - Execute MCP operations

## Supported Operations

### EKS Cluster Operations
- `list_clusters` - List EKS clusters in a region
- `describe_cluster` - Get detailed information about a cluster
- `list_nodegroups` - List nodegroups for a cluster
- `describe_nodegroup` - Get detailed information about a nodegroup

### Kubernetes Operations
- `list_namespaces` - List Kubernetes namespaces
- `list_pods` - List pods in a namespace
- `describe_pod` - Get detailed information about a pod
- `get_deployments` - List deployments in a namespace
- `describe_deployment` - Get detailed information about a deployment
- `get_services` - List services in a namespace
- `describe_service` - Get detailed information about a service
- `get_pod_logs` - Get logs from a pod

## Authentication Methods

The server supports multiple authentication methods for EKS clusters:

1. **AWS SDK Authentication**: Uses the AWS SDK to authenticate with EKS and get cluster information
2. **Kubectl with Generated Kubeconfig**: Creates a temporary kubeconfig file and uses kubectl
3. **Direct Kubernetes API Calls**: Makes direct API calls to the Kubernetes API server

The current implementation uses the Kubectl method with proper authentication, which provides the most reliable results.

## Getting Started

### Prerequisites

- Docker
- AWS credentials (for production use)
- Python 3.8+ (for local development)

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python main.py
```

### Running with Docker

```bash
# Build the Docker image
docker build -t eks-mcp-server .

# Run the container
docker run -d -p 8000:8000 --name mcp-server eks-mcp-server
```

### Running with Docker Compose

```bash
# Start the server
docker-compose up -d

# Stop the server
docker-compose down
```

### Deploying to ECS

See the [ECS Deployment README](ecs-deployment/README.md) for detailed instructions.

```bash
# Deploy to ECS
cd ecs-deployment
./deploy.sh

# Update existing ECS deployment
./update-service.sh
```

## Testing

Use the included test scripts to verify the server is working correctly:

```bash
# Basic tests
python test_mcp.py

# Comprehensive operation tests
python test_mcp_operations.py

# Test namespace integration
python test_mcp_namespace.py
python test_mcp_namespace_2.py

# Test kubectl integration
python test_kubectl_operations.py

# Test SDK v3 operations
python test_v3_operations.py

# Test SDK v4 operations
python test_v4_operations.py
```

## Client Usage

The project includes a client implementation that uses Amazon Bedrock for conversational interaction with the MCP server. See the [Client README](client/README.md) for details.

```bash
# Run the client
cd client
python mcp_chat_client_v6.py
```

## Example Requests

### List Clusters

```bash
curl -X POST http://localhost:8000/mcp/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "operation": "list_clusters",
    "parameters": {
      "region": "us-east-1"
    }
  }'
```

### List Pods

```bash
curl -X POST http://localhost:8000/mcp/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "operation": "list_pods",
    "parameters": {
      "cluster_name": "my-cluster",
      "namespace": "default",
      "region": "us-east-1"
    }
  }'
```

## Architecture

The server is built with FastAPI and uses a combination of synchronous and asynchronous operations for improved performance. It includes:

- Timeout handling for AWS API calls
- Multiple authentication methods for EKS clusters
- Comprehensive logging
- Response time tracking
- Error handling with detailed error codes

## EKS Authentication

For the server to authenticate with EKS clusters, the ECS task role needs to be added to the EKS cluster's aws-auth ConfigMap. See the [ECS Deployment README](ecs-deployment/README.md) for detailed instructions.

## Current Deployment

The server is currently deployed to ECS and accessible at:
- Endpoint: http://3.90.45.69:8000
- Health check: http://3.90.45.69:8000/health
- Operations discovery: http://3.90.45.69:8000/mcp/v1/operations

## Test Namespaces

The project includes test namespaces in the EKS cluster:
- `mcp-test-namespace`: Contains a deployment with 2 nginx pods
- `mcp-test-namespace-2`: Contains a deployment with 3 nginx pods

## License

MIT
