#!/bin/bash
# AWS Deployment Script for ToastyAnalytics
# This script automates the deployment to AWS ECS Fargate

set -e  # Exit on error

echo "🚀 ToastyAnalytics AWS Deployment Script"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
CLUSTER_NAME="toastyanalytics"
SERVICE_NAME="toastyanalytics-api"
TASK_FAMILY="toastyanalytics-task"
ECR_REPO_NAME="toastyanalytics"

# Get AWS Account ID
echo -e "\n${YELLOW}📋 Getting AWS Account ID...${NC}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account ID: $AWS_ACCOUNT_ID${NC}"

ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME"

# Step 1: Create ECR Repository
echo -e "\n${YELLOW}📦 Creating ECR Repository...${NC}"
if aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $AWS_REGION 2>/dev/null; then
    echo -e "${GREEN}✓ ECR repository already exists${NC}"
else
    aws ecr create-repository \
        --repository-name $ECR_REPO_NAME \
        --region $AWS_REGION \
        --image-scanning-configuration scanOnPush=true
    echo -e "${GREEN}✓ ECR repository created${NC}"
fi

# Step 2: Build and Push Docker Image
echo -e "\n${YELLOW}🐳 Building Docker image...${NC}"
cd "$(dirname "$0")/.."
docker build -f deployment/docker/Dockerfile -t $ECR_REPO_NAME:latest .
echo -e "${GREEN}✓ Docker image built${NC}"

echo -e "\n${YELLOW}🔐 Logging into ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_URI

echo -e "\n${YELLOW}⬆️  Pushing image to ECR...${NC}"
docker tag $ECR_REPO_NAME:latest $ECR_URI:latest
docker tag $ECR_REPO_NAME:latest $ECR_URI:$(git rev-parse --short HEAD)
docker push $ECR_URI:latest
docker push $ECR_URI:$(git rev-parse --short HEAD)
echo -e "${GREEN}✓ Image pushed to ECR${NC}"

# Step 3: Create VPC (if needed)
echo -e "\n${YELLOW}🌐 Setting up VPC...${NC}"
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=toastyanalytics-vpc" --query "Vpcs[0].VpcId" --output text --region $AWS_REGION 2>/dev/null || echo "None")

if [ "$VPC_ID" == "None" ]; then
    echo -e "${YELLOW}Creating new VPC...${NC}"
    VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --region $AWS_REGION --query 'Vpc.VpcId' --output text)
    aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=toastyanalytics-vpc --region $AWS_REGION
    aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-support --region $AWS_REGION
    aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames --region $AWS_REGION
    echo -e "${GREEN}✓ VPC created: $VPC_ID${NC}"
else
    echo -e "${GREEN}✓ Using existing VPC: $VPC_ID${NC}"
fi

# Create Internet Gateway
IGW_ID=$(aws ec2 describe-internet-gateways --filters "Name=tag:Name,Values=toastyanalytics-igw" --query "InternetGateways[0].InternetGatewayId" --output text --region $AWS_REGION 2>/dev/null || echo "None")
if [ "$IGW_ID" == "None" ]; then
    IGW_ID=$(aws ec2 create-internet-gateway --region $AWS_REGION --query 'InternetGateway.InternetGatewayId' --output text)
    aws ec2 create-tags --resources $IGW_ID --tags Key=Name,Value=toastyanalytics-igw --region $AWS_REGION
    aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID --region $AWS_REGION
    echo -e "${GREEN}✓ Internet Gateway created${NC}"
fi

# Create Subnets
echo -e "\n${YELLOW}📡 Creating subnets...${NC}"
SUBNET_1=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone ${AWS_REGION}a --region $AWS_REGION --query 'Subnet.SubnetId' --output text 2>/dev/null || \
    aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=cidr-block,Values=10.0.1.0/24" --query "Subnets[0].SubnetId" --output text --region $AWS_REGION)
SUBNET_2=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24 --availability-zone ${AWS_REGION}b --region $AWS_REGION --query 'Subnet.SubnetId' --output text 2>/dev/null || \
    aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=cidr-block,Values=10.0.2.0/24" --query "Subnets[0].SubnetId" --output text --region $AWS_REGION)

aws ec2 modify-subnet-attribute --subnet-id $SUBNET_1 --map-public-ip-on-launch --region $AWS_REGION
aws ec2 modify-subnet-attribute --subnet-id $SUBNET_2 --map-public-ip-on-launch --region $AWS_REGION
echo -e "${GREEN}✓ Subnets created${NC}"

# Create Route Table
ROUTE_TABLE_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --region $AWS_REGION --query 'RouteTable.RouteTableId' --output text 2>/dev/null || \
    aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC_ID" --query "RouteTables[0].RouteTableId" --output text --region $AWS_REGION)
aws ec2 create-route --route-table-id $ROUTE_TABLE_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID --region $AWS_REGION 2>/dev/null || true
aws ec2 associate-route-table --subnet-id $SUBNET_1 --route-table-id $ROUTE_TABLE_ID --region $AWS_REGION 2>/dev/null || true
aws ec2 associate-route-table --subnet-id $SUBNET_2 --route-table-id $ROUTE_TABLE_ID --region $AWS_REGION 2>/dev/null || true

# Create Security Group
echo -e "\n${YELLOW}🔒 Creating security group...${NC}"
SG_ID=$(aws ec2 describe-security-groups --filters "Name=tag:Name,Values=toastyanalytics-sg" "Name=vpc-id,Values=$VPC_ID" --query "SecurityGroups[0].GroupId" --output text --region $AWS_REGION 2>/dev/null || echo "None")
if [ "$SG_ID" == "None" ]; then
    SG_ID=$(aws ec2 create-security-group \
        --group-name toastyanalytics-sg \
        --description "Security group for ToastyAnalytics" \
        --vpc-id $VPC_ID \
        --region $AWS_REGION \
        --query 'GroupId' \
        --output text)
    aws ec2 create-tags --resources $SG_ID --tags Key=Name,Value=toastyanalytics-sg --region $AWS_REGION
    
    # Allow HTTP (80) and HTTPS (443)
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $AWS_REGION
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0 --region $AWS_REGION
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0 --region $AWS_REGION
    echo -e "${GREEN}✓ Security group created${NC}"
else
    echo -e "${GREEN}✓ Using existing security group: $SG_ID${NC}"
fi

# Step 4: Create RDS PostgreSQL Database
echo -e "\n${YELLOW}🗄️  Setting up RDS PostgreSQL...${NC}"
DB_INSTANCE_ID="toastyanalytics-db"
DB_EXISTS=$(aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_ID --region $AWS_REGION 2>/dev/null || echo "None")

if [ "$DB_EXISTS" == "None" ]; then
    echo -e "${YELLOW}Creating RDS instance (this takes ~5-10 minutes)...${NC}"
    
    # Create DB subnet group
    aws rds create-db-subnet-group \
        --db-subnet-group-name toastyanalytics-subnet-group \
        --db-subnet-group-description "Subnet group for ToastyAnalytics" \
        --subnet-ids $SUBNET_1 $SUBNET_2 \
        --region $AWS_REGION 2>/dev/null || true
    
    # Generate random password
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "/@\"'\\" | head -c 32)
    
    aws rds create-db-instance \
        --db-instance-identifier $DB_INSTANCE_ID \
        --db-instance-class db.t3.micro \
        --engine postgres \
        --engine-version 15.4 \
        --master-username toasty_admin \
        --master-user-password "$DB_PASSWORD" \
        --allocated-storage 20 \
        --vpc-security-group-ids $SG_ID \
        --db-subnet-group-name toastyanalytics-subnet-group \
        --backup-retention-period 7 \
        --preferred-backup-window "03:00-04:00" \
        --preferred-maintenance-window "mon:04:00-mon:05:00" \
        --publicly-accessible \
        --storage-encrypted \
        --region $AWS_REGION
    
    # Save password to AWS Secrets Manager
    aws secretsmanager create-secret \
        --name toastyanalytics/db-password \
        --description "Database password for ToastyAnalytics" \
        --secret-string "$DB_PASSWORD" \
        --region $AWS_REGION 2>/dev/null || \
    aws secretsmanager update-secret \
        --secret-id toastyanalytics/db-password \
        --secret-string "$DB_PASSWORD" \
        --region $AWS_REGION
    
    echo -e "${GREEN}✓ RDS instance creation initiated${NC}"
    echo -e "${YELLOW}⏳ Waiting for RDS to be available...${NC}"
    aws rds wait db-instance-available --db-instance-identifier $DB_INSTANCE_ID --region $AWS_REGION
    echo -e "${GREEN}✓ RDS instance is available${NC}"
else
    echo -e "${GREEN}✓ RDS instance already exists${NC}"
fi

# Get RDS endpoint
DB_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier $DB_INSTANCE_ID --query 'DBInstances[0].Endpoint.Address' --output text --region $AWS_REGION)
echo -e "${GREEN}✓ Database endpoint: $DB_ENDPOINT${NC}"

# Step 5: Create ElastiCache Redis
echo -e "\n${YELLOW}💾 Setting up ElastiCache Redis...${NC}"
REDIS_CLUSTER_ID="toastyanalytics-redis"
REDIS_EXISTS=$(aws elasticache describe-cache-clusters --cache-cluster-id $REDIS_CLUSTER_ID --region $AWS_REGION 2>/dev/null || echo "None")

if [ "$REDIS_EXISTS" == "None" ]; then
    # Create cache subnet group
    aws elasticache create-cache-subnet-group \
        --cache-subnet-group-name toastyanalytics-cache-subnet \
        --cache-subnet-group-description "Cache subnet for ToastyAnalytics" \
        --subnet-ids $SUBNET_1 $SUBNET_2 \
        --region $AWS_REGION 2>/dev/null || true
    
    aws elasticache create-cache-cluster \
        --cache-cluster-id $REDIS_CLUSTER_ID \
        --cache-node-type cache.t3.micro \
        --engine redis \
        --num-cache-nodes 1 \
        --cache-subnet-group-name toastyanalytics-cache-subnet \
        --security-group-ids $SG_ID \
        --region $AWS_REGION
    
    echo -e "${GREEN}✓ Redis cluster creation initiated${NC}"
    echo -e "${YELLOW}⏳ Waiting for Redis to be available...${NC}"
    aws elasticache wait cache-cluster-available --cache-cluster-id $REDIS_CLUSTER_ID --region $AWS_REGION
else
    echo -e "${GREEN}✓ Redis cluster already exists${NC}"
fi

# Get Redis endpoint
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters --cache-cluster-id $REDIS_CLUSTER_ID --show-cache-node-info --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' --output text --region $AWS_REGION)
echo -e "${GREEN}✓ Redis endpoint: $REDIS_ENDPOINT${NC}"

# Step 6: Create ECS Cluster
echo -e "\n${YELLOW}🎯 Creating ECS Cluster...${NC}"
CLUSTER_EXISTS=$(aws ecs describe-clusters --clusters $CLUSTER_NAME --region $AWS_REGION --query 'clusters[0].status' --output text 2>/dev/null || echo "INACTIVE")
if [ "$CLUSTER_EXISTS" != "ACTIVE" ]; then
    aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $AWS_REGION
    echo -e "${GREEN}✓ ECS cluster created${NC}"
else
    echo -e "${GREEN}✓ ECS cluster already exists${NC}"
fi

# Step 7: Create IAM Role for ECS Tasks
echo -e "\n${YELLOW}🔑 Creating IAM roles...${NC}"
TASK_ROLE_NAME="toastyanalyticsTaskRole"
EXECUTION_ROLE_NAME="toastyanalyticsExecutionRole"

# Task Role
if ! aws iam get-role --role-name $TASK_ROLE_NAME --region $AWS_REGION 2>/dev/null; then
    aws iam create-role \
        --role-name $TASK_ROLE_NAME \
        --assume-role-policy-document file://$(dirname "$0")/ecs-task-trust-policy.json \
        --region $AWS_REGION 2>/dev/null || true
    
    aws iam attach-role-policy \
        --role-name $TASK_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess \
        --region $AWS_REGION
fi

# Execution Role
if ! aws iam get-role --role-name $EXECUTION_ROLE_NAME --region $AWS_REGION 2>/dev/null; then
    aws iam create-role \
        --role-name $EXECUTION_ROLE_NAME \
        --assume-role-policy-document file://$(dirname "$0")/ecs-task-trust-policy.json \
        --region $AWS_REGION 2>/dev/null || true
    
    aws iam attach-role-policy \
        --role-name $EXECUTION_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
        --region $AWS_REGION
    
    aws iam attach-role-policy \
        --role-name $EXECUTION_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite \
        --region $AWS_REGION
fi

echo -e "${GREEN}✓ IAM roles configured${NC}"

# Step 8: Register Task Definition
echo -e "\n${YELLOW}📝 Registering ECS task definition...${NC}"

# Get DB password from Secrets Manager
DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id toastyanalytics/db-password --query SecretString --output text --region $AWS_REGION)
DATABASE_URL="postgresql://toasty_admin:${DB_PASSWORD}@${DB_ENDPOINT}:5432/postgres"
REDIS_URL="redis://${REDIS_ENDPOINT}:6379/0"

# Create task definition JSON
cat > /tmp/task-definition.json <<EOF
{
  "family": "$TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/${EXECUTION_ROLE_NAME}",
  "taskRoleArn": "arn:aws:iam::${AWS_ACCOUNT_ID}:role/${TASK_ROLE_NAME}",
  "containerDefinitions": [
    {
      "name": "toastyanalytics-api",
      "image": "${ECR_URI}:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "DATABASE_URL", "value": "$DATABASE_URL"},
        {"name": "REDIS_URL", "value": "$REDIS_URL"},
        {"name": "CELERY_BROKER_URL", "value": "$REDIS_URL"},
        {"name": "CELERY_RESULT_BACKEND", "value": "$REDIS_URL"},
        {"name": "ENABLE_NEURAL_GRADER", "value": "true"},
        {"name": "ENABLE_RATE_LIMITING", "value": "true"},
        {"name": "ENABLE_CACHING", "value": "true"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/toastyanalytics",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "python -c 'import requests; requests.get(\"http://localhost:8000/health\")' || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

aws ecs register-task-definition --cli-input-json file:///tmp/task-definition.json --region $AWS_REGION
echo -e "${GREEN}✓ Task definition registered${NC}"

# Step 9: Create Application Load Balancer
echo -e "\n${YELLOW}⚖️  Creating Application Load Balancer...${NC}"
ALB_NAME="toastyanalytics-alb"
ALB_EXISTS=$(aws elbv2 describe-load-balancers --names $ALB_NAME --region $AWS_REGION 2>/dev/null || echo "None")

if [ "$ALB_EXISTS" == "None" ]; then
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name $ALB_NAME \
        --subnets $SUBNET_1 $SUBNET_2 \
        --security-groups $SG_ID \
        --scheme internet-facing \
        --type application \
        --region $AWS_REGION \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text)
    echo -e "${GREEN}✓ ALB created${NC}"
else
    ALB_ARN=$(aws elbv2 describe-load-balancers --names $ALB_NAME --query 'LoadBalancers[0].LoadBalancerArn' --output text --region $AWS_REGION)
    echo -e "${GREEN}✓ Using existing ALB${NC}"
fi

# Create Target Group
TG_NAME="toastyanalytics-tg"
TG_EXISTS=$(aws elbv2 describe-target-groups --names $TG_NAME --region $AWS_REGION 2>/dev/null || echo "None")

if [ "$TG_EXISTS" == "None" ]; then
    TG_ARN=$(aws elbv2 create-target-group \
        --name $TG_NAME \
        --protocol HTTP \
        --port 8000 \
        --vpc-id $VPC_ID \
        --target-type ip \
        --health-check-path /health \
        --health-check-interval-seconds 30 \
        --health-check-timeout-seconds 5 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 3 \
        --region $AWS_REGION \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text)
    echo -e "${GREEN}✓ Target group created${NC}"
else
    TG_ARN=$(aws elbv2 describe-target-groups --names $TG_NAME --query 'TargetGroups[0].TargetGroupArn' --output text --region $AWS_REGION)
    echo -e "${GREEN}✓ Using existing target group${NC}"
fi

# Create Listener
LISTENER_EXISTS=$(aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN --region $AWS_REGION --query 'Listeners[0].ListenerArn' --output text 2>/dev/null || echo "None")
if [ "$LISTENER_EXISTS" == "None" ]; then
    aws elbv2 create-listener \
        --load-balancer-arn $ALB_ARN \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn=$TG_ARN \
        --region $AWS_REGION
    echo -e "${GREEN}✓ Listener created${NC}"
fi

# Step 10: Create ECS Service
echo -e "\n${YELLOW}🚢 Creating ECS Service...${NC}"
SERVICE_EXISTS=$(aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION --query 'services[0].status' --output text 2>/dev/null || echo "INACTIVE")

if [ "$SERVICE_EXISTS" != "ACTIVE" ]; then
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --task-definition $TASK_FAMILY \
        --desired-count 2 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
        --load-balancers "targetGroupArn=$TG_ARN,containerName=toastyanalytics-api,containerPort=8000" \
        --health-check-grace-period-seconds 60 \
        --region $AWS_REGION
    echo -e "${GREEN}✓ ECS service created${NC}"
else
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition $TASK_FAMILY \
        --force-new-deployment \
        --region $AWS_REGION
    echo -e "${GREEN}✓ ECS service updated${NC}"
fi

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --query 'LoadBalancers[0].DNSName' --output text --region $AWS_REGION)

echo -e "\n${GREEN}=========================================${NC}"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo -e "\n${YELLOW}📊 Deployment Details:${NC}"
echo -e "  • Load Balancer URL: ${GREEN}http://$ALB_DNS${NC}"
echo -e "  • Health Check: ${GREEN}http://$ALB_DNS/health${NC}"
echo -e "  • API Docs: ${GREEN}http://$ALB_DNS/docs${NC}"
echo -e "  • Database Endpoint: ${GREEN}$DB_ENDPOINT${NC}"
echo -e "  • Redis Endpoint: ${GREEN}$REDIS_ENDPOINT${NC}"
echo -e "  • ECS Cluster: ${GREEN}$CLUSTER_NAME${NC}"
echo -e "  • Region: ${GREEN}$AWS_REGION${NC}"
echo -e "\n${YELLOW}🔍 Useful Commands:${NC}"
echo -e "  • View logs: ${GREEN}aws ecs logs tail --cluster $CLUSTER_NAME --task <task-id> --follow${NC}"
echo -e "  • Check service: ${GREEN}aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME${NC}"
echo -e "  • List tasks: ${GREEN}aws ecs list-tasks --cluster $CLUSTER_NAME${NC}"
echo -e "\n${YELLOW}⏳ Note: It may take 2-3 minutes for the service to be fully available${NC}"
echo -e "\n${GREEN}🎉 Your ToastyAnalytics API is now live on AWS!${NC}\n"
