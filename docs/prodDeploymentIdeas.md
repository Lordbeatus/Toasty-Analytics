# ToastyAnalytics Production Deployment Guide

Complete guide to deploy ToastyAnalytics to production on various cloud platforms.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Deployment Options](#deployment-options)
   - [Option A: AWS (Recommended)](#option-a-aws-recommended)
   - [Option B: Azure](#option-b-azure)
   - [Option C: Google Cloud Platform](#option-c-google-cloud-platform)
   - [Option D: DigitalOcean (Simplest)](#option-d-digitalocean-simplest)
4. [Post-Deployment Setup](#post-deployment-setup)
5. [Monitoring & Maintenance](#monitoring--maintenance)

---

## Prerequisites

### Required Tools
```bash
# Docker & Docker Compose
docker --version  # >= 20.10
docker-compose --version  # >= 2.0

# Kubernetes CLI (if using K8s)
kubectl version --client  # >= 1.25

# Cloud CLI (choose one based on provider)
aws --version        # AWS
az --version         # Azure
gcloud --version     # GCP
doctl --version      # DigitalOcean
```

### Required Accounts
- [ ] Cloud provider account (AWS/Azure/GCP/DO)
- [ ] Container registry access (Docker Hub, ECR, ACR, GCR, or DOCR)
- [ ] Domain name (optional but recommended)
- [ ] SSL certificate or Let's Encrypt setup

---

## Environment Setup

### 1. Create Production Environment File

Create `.env.production` in the root directory:

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/toastyanalytics
POSTGRES_USER=toasty_prod
POSTGRES_PASSWORD=<STRONG_PASSWORD_HERE>
POSTGRES_DB=toastyanalytics

# Redis
REDIS_URL=redis://redis-host:6379/0
REDIS_PASSWORD=<REDIS_PASSWORD_HERE>

# Celery
CELERY_BROKER_URL=redis://redis-host:6379/0
CELERY_RESULT_BACKEND=redis://redis-host:6379/1

# Security
SECRET_KEY=<GENERATE_STRONG_SECRET_KEY>
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Monitoring (Optional)
SENTRY_DSN=<YOUR_SENTRY_DSN>
PROMETHEUS_ENABLED=true

# OpenTelemetry (Optional)
OTEL_EXPORTER_JAEGER_ENDPOINT=http://jaeger:14268/api/traces
OTEL_SERVICE_NAME=toastyanalytics

# Feature Flags
ENABLE_NEURAL_GRADER=true
ENABLE_RATE_LIMITING=true
ENABLE_CACHING=true
```

### 2. Generate Secrets

```bash
# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(50))"

# Generate strong passwords
openssl rand -base64 32
```

---

## Deployment Options

## Option A: AWS (Recommended)

### Step 1: Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository
aws ecr create-repository --repository-name toastyanalytics --region us-east-1

# Build image
cd toastyanalytics
docker build -f deployment/docker/Dockerfile -t toastyanalytics:latest .

# Tag for ECR
docker tag toastyanalytics:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/toastyanalytics:latest

# Push to ECR
docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/toastyanalytics:latest
```

### Step 2: Set Up Infrastructure

#### Option A1: ECS Fargate (Simpler, Serverless)

```bash
# Install and configure ECS CLI
ecs-cli configure --cluster toastyanalytics --region us-east-1 --default-launch-type FARGATE

# Create cluster
ecs-cli up --cluster-config toastyanalytics --ecs-profile default

# Create RDS PostgreSQL
aws rds create-db-instance \
  --db-instance-identifier toastyanalytics-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username toasty_prod \
  --master-user-password <PASSWORD> \
  --allocated-storage 20 \
  --vpc-security-group-ids <SECURITY_GROUP_ID>

# Create ElastiCache Redis
aws elasticache create-cache-cluster \
  --cache-cluster-id toastyanalytics-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1

# Deploy with ECS
# Create task definition (see ecs-task-definition.json below)
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json

# Create service
aws ecs create-service \
  --cluster toastyanalytics \
  --service-name api-service \
  --task-definition toastyanalytics-task \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

#### Option A2: EKS (More Control, Scalable)

```bash
# Create EKS cluster
eksctl create cluster \
  --name toastyanalytics \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 4 \
  --managed

# Configure kubectl
aws eks update-kubeconfig --region us-east-1 --name toastyanalytics

# Create namespace
kubectl create namespace toastyanalytics

# Create secrets
kubectl create secret generic db-credentials \
  --from-literal=url="postgresql://user:pass@host:5432/db" \
  -n toastyanalytics

kubectl create secret generic redis-credentials \
  --from-literal=url="redis://host:6379/0" \
  -n toastyanalytics

# Deploy
kubectl apply -f deployment/kubernetes/deployments.yaml
```

### Step 3: Set Up Load Balancer

```bash
# Create Application Load Balancer
aws elbv2 create-load-balancer \
  --name toastyanalytics-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx

# Create target group
aws elbv2 create-target-group \
  --name toastyanalytics-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxx \
  --health-check-path /health

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn <ALB_ARN> \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=<ACM_CERT_ARN> \
  --default-actions Type=forward,TargetGroupArn=<TARGET_GROUP_ARN>
```

---

## Option B: Azure

### Step 1: Build and Push to ACR

```bash
# Login to Azure
az login

# Create resource group
az group create --name toastyanalytics-rg --location eastus

# Create container registry
az acr create --resource-group toastyanalytics-rg --name toastyanalyticsacr --sku Basic

# Login to ACR
az acr login --name toastyanalyticsacr

# Build and push
cd toastyanalytics
az acr build --registry toastyanalyticsacr --image toastyanalytics:latest -f deployment/docker/Dockerfile .
```

### Step 2: Deploy to Azure Container Apps (Simplest)

```bash
# Create Container App environment
az containerapp env create \
  --name toastyanalytics-env \
  --resource-group toastyanalytics-rg \
  --location eastus

# Create PostgreSQL
az postgres flexible-server create \
  --resource-group toastyanalytics-rg \
  --name toastyanalytics-db \
  --admin-user toasty_admin \
  --admin-password <PASSWORD> \
  --sku-name Standard_B1ms

# Create Redis
az redis create \
  --resource-group toastyanalytics-rg \
  --name toastyanalytics-redis \
  --location eastus \
  --sku Basic \
  --vm-size c0

# Deploy container app
az containerapp create \
  --name toastyanalytics-api \
  --resource-group toastyanalytics-rg \
  --environment toastyanalytics-env \
  --image toastyanalyticsacr.azurecr.io/toastyanalytics:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 2 \
  --max-replicas 10 \
  --env-vars DATABASE_URL=<DB_URL> REDIS_URL=<REDIS_URL>
```

### Step 3: Alternative - Azure Kubernetes Service (AKS)

```bash
# Create AKS cluster
az aks create \
  --resource-group toastyanalytics-rg \
  --name toastyanalytics-aks \
  --node-count 3 \
  --enable-managed-identity \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group toastyanalytics-rg --name toastyanalytics-aks

# Deploy
kubectl apply -f deployment/kubernetes/deployments.yaml
```

---

## Option C: Google Cloud Platform

### Step 1: Build and Push to GCR

```bash
# Set project
gcloud config set project <PROJECT_ID>

# Enable APIs
gcloud services enable container.googleapis.com
gcloud services enable sqladmin.googleapis.com

# Build and push
cd toastyanalytics
gcloud builds submit --tag gcr.io/<PROJECT_ID>/toastyanalytics -f deployment/docker/Dockerfile .
```

### Step 2: Deploy to Cloud Run (Simplest)

```bash
# Create Cloud SQL PostgreSQL
gcloud sql instances create toastyanalytics-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create toastyanalytics --instance=toastyanalytics-db

# Create user
gcloud sql users create toasty_prod --instance=toastyanalytics-db --password=<PASSWORD>

# Deploy to Cloud Run
gcloud run deploy toastyanalytics-api \
  --image gcr.io/<PROJECT_ID>/toastyanalytics \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=<DB_URL>,REDIS_URL=<REDIS_URL> \
  --min-instances 1 \
  --max-instances 10 \
  --memory 512Mi \
  --cpu 1
```

### Step 3: Alternative - GKE

```bash
# Create GKE cluster
gcloud container clusters create toastyanalytics \
  --num-nodes=3 \
  --machine-type=e2-medium \
  --region=us-central1

# Get credentials
gcloud container clusters get-credentials toastyanalytics --region=us-central1

# Deploy
kubectl apply -f deployment/kubernetes/deployments.yaml
```

---

## Option D: DigitalOcean (Simplest & Most Cost-Effective)

### Step 1: Set Up Infrastructure

```bash
# Install doctl
snap install doctl

# Authenticate
doctl auth init

# Create Kubernetes cluster
doctl kubernetes cluster create toastyanalytics \
  --region nyc1 \
  --node-pool "name=worker-pool;size=s-2vcpu-4gb;count=3"

# Save kubeconfig
doctl kubernetes cluster kubeconfig save toastyanalytics

# Create managed database
doctl databases create toastyanalytics-db \
  --engine pg \
  --region nyc1 \
  --size db-s-1vcpu-1gb \
  --version 15

# Create Redis
doctl databases create toastyanalytics-redis \
  --engine redis \
  --region nyc1 \
  --size db-s-1vcpu-1gb
```

### Step 2: Build and Deploy

```bash
# Create container registry
doctl registry create toastyanalytics

# Login
doctl registry login

# Build and push
cd toastyanalytics
docker build -f deployment/docker/Dockerfile -t registry.digitalocean.com/toastyanalytics/api:latest .
docker push registry.digitalocean.com/toastyanalytics/api:latest

# Update deployments.yaml with your registry URL
# Then deploy
kubectl apply -f deployment/kubernetes/deployments.yaml
```

### Step 3: Set Up Load Balancer

```bash
# DigitalOcean automatically creates a load balancer when you create a LoadBalancer service
# Get the external IP
kubectl get svc -n toastyanalytics

# Point your domain to the load balancer IP
```

---

## Post-Deployment Setup

### 1. Database Migration

```bash
# Run migrations in the container
kubectl exec -it deployment/toastyanalytics-api -n toastyanalytics -- alembic upgrade head

# Or for Docker
docker exec -it toasty-api alembic upgrade head
```

### 2. SSL Certificate

#### Using Let's Encrypt with cert-manager (Kubernetes)

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### 3. Set Up Domain

```bash
# Point your domain to the load balancer IP
# Create A record: api.yourdomain.com -> <LOAD_BALANCER_IP>

# For AWS Route53
aws route53 change-resource-record-sets \
  --hosted-zone-id <ZONE_ID> \
  --change-batch file://dns-change.json
```

### 4. Configure CI/CD Auto-Deploy

Update `.github/workflows/toastyanalytics-ci.yml`:

```yaml
  deploy-production:
    runs-on: ubuntu-latest
    needs: build-docker
    if: github.ref == 'refs/heads/master'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build, tag, and push image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        ECR_REPOSITORY: toastyanalytics
        IMAGE_TAG: ${{ github.sha }}
      run: |
        cd toastyanalytics
        docker build -f deployment/docker/Dockerfile -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
    
    - name: Deploy to ECS
      run: |
        aws ecs update-service --cluster toastyanalytics --service api-service --force-new-deployment
```

---

## Monitoring & Maintenance

### 1. Set Up Prometheus & Grafana

```bash
# Add Prometheus Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
# Default credentials: admin / prom-operator
```

### 2. Set Up Logging (ELK Stack or Loki)

```bash
# Install Loki
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack --namespace monitoring
```

### 3. Set Up Sentry Error Tracking

1. Create account at https://sentry.io
2. Create new project
3. Add DSN to environment variables
4. Errors will be automatically tracked

### 4. Health Checks

```bash
# Test health endpoint
curl https://api.yourdomain.com/health

# Expected response
{"status": "healthy", "timestamp": "2025-12-26T..."}
```

### 5. Scaling

#### Auto-scaling (Kubernetes)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: toastyanalytics
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: grading-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## Cost Estimates

### DigitalOcean (Most Affordable)
- Kubernetes (3 nodes, 2vCPU, 4GB): $48/month
- Managed PostgreSQL (1GB): $15/month
- Managed Redis (1GB): $15/month
- Load Balancer: $12/month
- **Total: ~$90/month**

### AWS (Production-Grade)
- ECS Fargate (2 tasks): ~$50/month
- RDS PostgreSQL (db.t3.micro): ~$15/month
- ElastiCache Redis (cache.t3.micro): ~$15/month
- ALB: ~$20/month
- Data transfer: ~$10/month
- **Total: ~$110/month**

### Azure Container Apps
- Container Apps (2 replicas): ~$60/month
- PostgreSQL Flexible Server: ~$20/month
- Redis: ~$15/month
- **Total: ~$95/month**

### GCP Cloud Run
- Cloud Run (with min instances): ~$40/month
- Cloud SQL PostgreSQL: ~$25/month
- Memorystore Redis: ~$25/month
- **Total: ~$90/month**

---

## Quick Start Commands

### For DigitalOcean (Recommended for Getting Started)

```bash
# 1. Install doctl
brew install doctl  # macOS
# or snap install doctl  # Linux

# 2. Authenticate
doctl auth init

# 3. Run deployment script
./scripts/deploy-digitalocean.sh
```

### For AWS

```bash
# 1. Configure AWS CLI
aws configure

# 2. Run deployment script
./scripts/deploy-aws.sh
```

---

## Troubleshooting

### Common Issues

**Database connection fails:**
```bash
# Check connection string
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL

# Check firewall rules
```

**Redis not connecting:**
```bash
# Test Redis connection
redis-cli -h <host> -p 6379 ping

# Check if Redis is running
kubectl get pods -n toastyanalytics | grep redis
```

**Pods not starting (Kubernetes):**
```bash
# Check pod status
kubectl describe pod <pod-name> -n toastyanalytics

# Check logs
kubectl logs <pod-name> -n toastyanalytics

# Check events
kubectl get events -n toastyanalytics --sort-by='.lastTimestamp'
```

---

## Next Steps

1. [ ] Choose cloud provider
2. [ ] Set up accounts and billing
3. [ ] Configure environment variables
4. [ ] Run deployment scripts
5. [ ] Set up domain and SSL
6. [ ] Configure monitoring
7. [ ] Test endpoints
8. [ ] Set up CI/CD auto-deployment
9. [ ] Configure backups
10. [ ] Document runbooks for your team


