#!/bin/bash

# SonarQube Deployment Script for EKS
set -e

echo "=== SonarQube Deployment on EKS cluster: eks-poc ==="

# Set the cluster context
echo "Setting kubectl context to eks-poc cluster..."
kubectl config use-context arn:aws:eks:$(aws configure get region):$(aws sts get-caller-identity --query Account --output text):cluster/eks-poc

# Create namespace
echo "Creating Securitytool namespace..."
kubectl apply -f namespace.yaml

# Create EBS GP3 storage class
echo "Creating EBS GP3 storage class..."
kubectl apply -f ebs-gp3-storageclass.yaml

# Verify storage class
echo "Verifying storage class..."
kubectl get storageclass ebs-gp3-sc

# Add SonarQube Helm repository
echo "Adding SonarQube Helm repository..."
helm repo add sonarqube https://SonarSource.github.io/helm-chart-sonarqube
helm repo update

# Install SonarQube using Helm
echo "Installing SonarQube with Helm..."
helm upgrade --install sonarqube sonarqube/sonarqube \
  --namespace securitytool \
  --values sonarqube-values.yaml \
  --wait \
  --timeout 10m

# Check deployment status
echo "Checking deployment status..."
kubectl get pods -n securitytool
kubectl get svc -n securitytool
kubectl get pvc -n securitytool

# Get SonarQube service details
echo ""
echo "=== SonarQube Service Information ==="
kubectl get svc sonarqube-sonarqube -n securitytool

echo ""
echo "=== Deployment Complete ==="
echo "SonarQube is being deployed. It may take a few minutes to be fully ready."
echo "You can check the status with: kubectl get pods -n securitytool"
echo ""
echo "To get the LoadBalancer URL:"
echo "kubectl get svc sonarqube-sonarqube -n securitytool -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'"
echo ""
echo "Default login credentials:"
echo "Username: admin"
echo "Password: admin (you'll be prompted to change this on first login)" 
