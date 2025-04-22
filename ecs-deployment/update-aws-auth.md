# Updating the aws-auth ConfigMap

To allow the ECS task to access the EKS cluster, you need to add the ECS task role to the aws-auth ConfigMap in the EKS cluster.

## 1. Get the ECS task role ARN

```bash
TASK_ROLE_ARN=$(aws ecs describe-task-definition --task-definition eks-mcp-server-new:4 --query "taskDefinition.taskRoleArn" --output text)
echo $TASK_ROLE_ARN
```

## 2. Edit the aws-auth ConfigMap

```bash
kubectl edit configmap aws-auth -n kube-system
```

Add the following entry to the `mapRoles` section:

```yaml
- rolearn: <TASK_ROLE_ARN>
  username: eks-mcp-server
  groups:
    - system:masters
```

Replace `<TASK_ROLE_ARN>` with the actual task role ARN.

## 3. Verify the update

```bash
kubectl describe configmap aws-auth -n kube-system
```

## 4. Test the access

```bash
aws eks update-kubeconfig --name sample-eks-cluster --region us-east-1
kubectl get namespaces
```
