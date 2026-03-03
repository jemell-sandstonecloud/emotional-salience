#!/bin/bash
# ============================================================================
# Sandstone AWS Infrastructure Setup — Phase 2
# Idempotent — safe to re-run.
# Replace REPLACE_WITH_KEY and REPLACE_WITH_PASSWORD before first run.
# ============================================================================
set -e

echo "=== Sandstone Phase 2 — AWS Infrastructure Setup ==="

# ── Step A: Prerequisites Check ──
echo ""
echo "--- Step A: Prerequisites ---"
aws sts get-caller-identity || { echo "ERROR: AWS credentials not configured"; exit 1; }
echo "AWS credentials confirmed"

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
REGION="us-east-1"
echo "Account: $ACCOUNT_ID | VPC: $VPC_ID | Region: $REGION"

SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text)
echo "Subnets: $SUBNET_IDS"

# ── Step B: Secrets Manager ──
echo ""
echo "--- Step B: Secrets Manager ---"
aws secretsmanager create-secret \
  --name 'sandstone/anthropic-api-key' \
  --secret-string 'REPLACE_WITH_KEY' \
  --region $REGION 2>/dev/null || echo "Secret sandstone/anthropic-api-key already exists"

aws secretsmanager create-secret \
  --name 'sandstone/db-password' \
  --secret-string 'REPLACE_WITH_PASSWORD' \
  --region $REGION 2>/dev/null || echo "Secret sandstone/db-password already exists"

DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id sandstone/db-password --query SecretString --output text --region $REGION)

# ── Step C: IAM Role (updated for Phase 2) ──
echo ""
echo "--- Step C: IAM Role ---"
cat > /tmp/sandstone-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": ["ec2.amazonaws.com", "lambda.amazonaws.com"]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name SandstoneEC2Role \
  --assume-role-policy-document file:///tmp/sandstone-trust-policy.json \
  2>/dev/null || echo "Role SandstoneEC2Role already exists"

cat > /tmp/sandstone-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::sandstone-memory-archive-${ACCOUNT_ID}",
        "arn:aws:s3:::sandstone-memory-archive-${ACCOUNT_ID}/*",
        "arn:aws:s3:::sandstone-frontend-${ACCOUNT_ID}",
        "arn:aws:s3:::sandstone-frontend-${ACCOUNT_ID}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:sandstone/*"
    },
    {
      "Effect": "Allow",
      "Action": [ "rds-db:connect" ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:${REGION}:${ACCOUNT_ID}:*"
    },
    {
      "Effect": "Allow",
      "Action": [ "lambda:InvokeFunction" ],
      "Resource": "arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:sandstone-*"
    },
    {
      "Sid": "BedrockAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CognitoAccess",
      "Effect": "Allow",
      "Action": [
        "cognito-idp:AdminCreateUser",
        "cognito-idp:AdminGetUser",
        "cognito-idp:AdminInitiateAuth",
        "cognito-idp:ListUsers",
        "cognito-idp:DescribeUserPool"
      ],
      "Resource": "arn:aws:cognito-idp:${REGION}:${ACCOUNT_ID}:userpool/*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name SandstoneEC2Role \
  --policy-name SandstonePolicy \
  --policy-document file:///tmp/sandstone-policy.json

aws iam create-instance-profile \
  --instance-profile-name SandstoneInstanceProfile \
  2>/dev/null || echo "Instance profile already exists"

aws iam add-role-to-instance-profile \
  --instance-profile-name SandstoneInstanceProfile \
  --role-name SandstoneEC2Role \
  2>/dev/null || echo "Role already attached to instance profile"

echo "IAM role configured (includes Bedrock + Cognito permissions)"

# ── Step D: Security Groups ──
echo ""
echo "--- Step D: Security Groups ---"

EC2_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=sandstone-ec2-sg" "Name=vpc-id,Values=$VPC_ID" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)
if [ "$EC2_SG_ID" = "None" ] || [ -z "$EC2_SG_ID" ]; then
  EC2_SG_ID=$(aws ec2 create-security-group --group-name sandstone-ec2-sg --description "Sandstone EC2" --vpc-id $VPC_ID --query 'GroupId' --output text)
  aws ec2 authorize-security-group-ingress --group-id $EC2_SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0
  aws ec2 authorize-security-group-ingress --group-id $EC2_SG_ID --protocol tcp --port 5000 --cidr 0.0.0.0/0
  aws ec2 authorize-security-group-ingress --group-id $EC2_SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0
  echo "Created EC2 SG: $EC2_SG_ID"
else
  echo "EC2 SG exists: $EC2_SG_ID"
fi

DB_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=sandstone-db-sg" "Name=vpc-id,Values=$VPC_ID" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)
if [ "$DB_SG_ID" = "None" ] || [ -z "$DB_SG_ID" ]; then
  DB_SG_ID=$(aws ec2 create-security-group --group-name sandstone-db-sg --description "Sandstone DB" --vpc-id $VPC_ID --query 'GroupId' --output text)
  aws ec2 authorize-security-group-ingress --group-id $DB_SG_ID --protocol tcp --port 5432 --source-group $EC2_SG_ID
  echo "Created DB SG: $DB_SG_ID"
else
  echo "DB SG exists: $DB_SG_ID"
fi

REDIS_SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=sandstone-redis-sg" "Name=vpc-id,Values=$VPC_ID" --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)
if [ "$REDIS_SG_ID" = "None" ] || [ -z "$REDIS_SG_ID" ]; then
  REDIS_SG_ID=$(aws ec2 create-security-group --group-name sandstone-redis-sg --description "Sandstone Redis" --vpc-id $VPC_ID --query 'GroupId' --output text)
  aws ec2 authorize-security-group-ingress --group-id $REDIS_SG_ID --protocol tcp --port 6379 --source-group $EC2_SG_ID
  echo "Created Redis SG: $REDIS_SG_ID"
else
  echo "Redis SG exists: $REDIS_SG_ID"
fi

# ── Step E: RDS PostgreSQL ──
echo ""
echo "--- Step E: RDS PostgreSQL ---"

aws rds create-db-subnet-group \
  --db-subnet-group-name sandstone-subnet-group \
  --db-subnet-group-description "Sandstone DB Subnets" \
  --subnet-ids $SUBNET_IDS \
  --region $REGION 2>/dev/null || echo "DB subnet group already exists"

aws rds create-db-instance \
  --db-instance-identifier sandstone-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username sandstone_admin \
  --master-user-password "$DB_PASSWORD" \
  --allocated-storage 20 \
  --db-name sandstone \
  --vpc-security-group-ids $DB_SG_ID \
  --db-subnet-group-name sandstone-subnet-group \
  --backup-retention-period 7 \
  --storage-encrypted \
  --no-publicly-accessible \
  --region $REGION 2>/dev/null || echo "RDS instance already exists"

echo "Waiting for RDS to become available..."
aws rds wait db-instance-available --db-instance-identifier sandstone-db --region $REGION 2>/dev/null || echo "RDS may still be starting"

DB_HOST=$(aws rds describe-db-instances --db-instance-identifier sandstone-db --query 'DBInstances[0].Endpoint.Address' --output text --region $REGION 2>/dev/null || echo "pending")
echo "RDS endpoint: $DB_HOST"

# ── Step F: ElastiCache Redis ──
echo ""
echo "--- Step F: ElastiCache Redis ---"
aws elasticache create-cache-cluster \
  --cache-cluster-id sandstone-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --engine-version 7.0 \
  --num-cache-nodes 1 \
  --security-group-ids $REDIS_SG_ID \
  --region $REGION 2>/dev/null || echo "Redis cluster already exists"

echo "Waiting for Redis..."
aws elasticache wait cache-cluster-available --cache-cluster-id sandstone-redis --region $REGION 2>/dev/null || echo "Redis may still be starting"

REDIS_HOST=$(aws elasticache describe-cache-clusters --cache-cluster-id sandstone-redis --show-cache-node-info --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' --output text --region $REGION 2>/dev/null || echo "pending")
echo "Redis endpoint: $REDIS_HOST"

# ── Step G: S3 Cold Storage ──
echo ""
echo "--- Step G: S3 Cold Storage ---"
BUCKET_NAME="sandstone-memory-archive-${ACCOUNT_ID}"

aws s3 mb "s3://${BUCKET_NAME}" --region $REGION 2>/dev/null || echo "Bucket already exists"

aws s3api put-bucket-encryption \
  --bucket "$BUCKET_NAME" \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

echo "S3 bucket configured: $BUCKET_NAME"

# ── Step H: EC2 Instance ──
echo ""
echo "--- Step H: EC2 Instance ---"

aws ec2 create-key-pair \
  --key-name sandstone-key \
  --query 'KeyMaterial' \
  --output text > sandstone-key.pem 2>/dev/null || echo "Key pair already exists"
chmod 400 sandstone-key.pem 2>/dev/null || true

AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-2023*-x86_64" "Name=state,Values=available" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
  --output text --region $REGION)

cat > /tmp/sandstone-userdata.sh << 'USERDATA'
#!/bin/bash
dnf update -y
dnf install -y python3 python3-pip git
cd /home/ec2-user
git clone https://github.com/YOUR_REPO/sandstone.git || echo "Clone manually"
cd sandstone
pip3 install -r requirements.txt
pip3 install gunicorn

cat > /etc/systemd/system/sandstone.service << 'SERVICE'
[Unit]
Description=Sandstone Memory Middleware
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/sandstone
Environment=USE_POSTGRES=true
Environment=REDIS_ENABLED=true
ExecStart=/usr/local/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable sandstone
USERDATA

aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.medium \
  --key-name sandstone-key \
  --security-group-ids $EC2_SG_ID \
  --iam-instance-profile Name=SandstoneInstanceProfile \
  --user-data file:///tmp/sandstone-userdata.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=sandstone-server}]' \
  --region $REGION \
  --query 'Instances[0].InstanceId' \
  --output text 2>/dev/null && echo "EC2 instance launched" || echo "EC2 launch skipped (may already exist)"

sleep 10
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=sandstone-server" "Name=instance-state-name,Values=running" \
  --query 'Reservations[0].Instances[0].InstanceId' --output text --region $REGION 2>/dev/null)
PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region $REGION 2>/dev/null || echo "pending")

echo "EC2 Instance: $INSTANCE_ID | Public IP: $PUBLIC_IP"

# ── Step I: Lambda Decay Engine ──
echo ""
echo "--- Step I: Lambda Decay Engine ---"

cd infra/lambda_decay
mkdir -p package
pip3 install -r requirements.txt -t package/ 2>/dev/null || echo "Install deps locally for packaging"
cp -r ../../db ../../core ../../config.py package/
cd package && zip -r ../decay_lambda.zip . > /dev/null 2>&1
cd ..

aws lambda create-function \
  --function-name sandstone-decay-engine \
  --runtime python3.11 \
  --handler lambda_handler.handler \
  --zip-file fileb://decay_lambda.zip \
  --role "arn:aws:iam::${ACCOUNT_ID}:role/SandstoneEC2Role" \
  --environment "Variables={DB_HOST=${DB_HOST},REDIS_HOST=${REDIS_HOST},USE_POSTGRES=true,AWS_DEFAULT_REGION=${REGION}}" \
  --timeout 300 \
  --memory-size 512 \
  --region $REGION 2>/dev/null || echo "Lambda function already exists"

aws events put-rule \
  --name sandstone-decay-schedule \
  --schedule-expression 'rate(24 hours)' \
  --state ENABLED \
  --region $REGION 2>/dev/null || echo "EventBridge rule already exists"

LAMBDA_ARN=$(aws lambda get-function --function-name sandstone-decay-engine \
  --query 'Configuration.FunctionArn' --output text --region $REGION 2>/dev/null || echo "pending")

aws events put-targets --rule sandstone-decay-schedule \
  --targets "Id=1,Arn=$LAMBDA_ARN" \
  --region $REGION 2>/dev/null || echo "Target already set"

aws lambda add-permission \
  --function-name sandstone-decay-engine \
  --statement-id eventbridge-decay \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --region $REGION 2>/dev/null || echo "Permission already granted"

echo "Lambda decay engine deployed"

# ── Step J: CloudWatch Logging ──
echo ""
echo "--- Step J: CloudWatch ---"
aws logs create-log-group --log-group-name /sandstone/api --region $REGION 2>/dev/null || echo "Log group exists"
aws logs create-log-group --log-group-name /sandstone/decay --region $REGION 2>/dev/null || echo "Log group exists"
echo "CloudWatch log groups created"

# ── Step K: Cognito User Pool (Phase 2) ──
echo ""
echo "--- Step K: Cognito User Pool ---"

POOL_ID=$(aws cognito-idp list-user-pools --max-results 10 --query "UserPools[?Name=='sandstone-study-users'].Id" --output text --region $REGION 2>/dev/null)

if [ -z "$POOL_ID" ] || [ "$POOL_ID" = "None" ]; then
  POOL_ID=$(aws cognito-idp create-user-pool \
    --pool-name sandstone-study-users \
    --auto-verified-attributes email \
    --username-attributes email \
    --policies '{"PasswordPolicy":{"MinimumLength":8,"RequireLowercase":true,"RequireNumbers":true,"RequireUppercase":false,"RequireSymbols":false}}' \
    --schema '[{"Name":"email","Required":true,"Mutable":true}]' \
    --query 'UserPool.Id' --output text --region $REGION)
  echo "Created Cognito User Pool: $POOL_ID"
else
  echo "Cognito User Pool exists: $POOL_ID"
fi

CLIENT_ID=$(aws cognito-idp list-user-pool-clients --user-pool-id $POOL_ID --query "UserPoolClients[?ClientName=='sandstone-web'].ClientId" --output text --region $REGION 2>/dev/null)

if [ -z "$CLIENT_ID" ] || [ "$CLIENT_ID" = "None" ]; then
  CLIENT_ID=$(aws cognito-idp create-user-pool-client \
    --user-pool-id $POOL_ID \
    --client-name sandstone-web \
    --no-generate-secret \
    --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH \
    --query 'UserPoolClient.ClientId' --output text --region $REGION)
  echo "Created Cognito App Client: $CLIENT_ID"
else
  echo "Cognito App Client exists: $CLIENT_ID"
fi

echo "Cognito User Pool ID: $POOL_ID"
echo "Cognito App Client ID: $CLIENT_ID"

# ── Step L: Bedrock Model Access ──
echo ""
echo "--- Step L: Bedrock Model Access ---"
echo "NOTE: Bedrock model access must be enabled manually in the AWS Console."
echo "Go to: Amazon Bedrock → Model access → Enable access for:"
echo "  - Anthropic Claude Sonnet 4.5"
echo "  - Anthropic Claude Haiku 4.5"
echo "  - Anthropic Claude Opus 4"
echo "  - Meta Llama 3.1 70B Instruct"
echo "  - Mistral Large"
echo "  - Amazon Titan Text Premier"
echo "IAM permissions for Bedrock already added in Step C."

# ── Step M: S3 Web Hosting Bucket (Phase 2 Frontend) ──
echo ""
echo "--- Step M: S3 Web Hosting ---"
FRONTEND_BUCKET="sandstone-frontend-${ACCOUNT_ID}"

aws s3 mb "s3://${FRONTEND_BUCKET}" --region $REGION 2>/dev/null || echo "Frontend bucket already exists"

aws s3 website "s3://${FRONTEND_BUCKET}" \
  --index-document index.html \
  --error-document index.html 2>/dev/null

echo "Frontend bucket configured: $FRONTEND_BUCKET"
echo "To deploy frontend: cd frontend && npm run build && aws s3 sync dist/ s3://${FRONTEND_BUCKET}/"

# ── Step N: CloudFront Distribution (Phase 2 CDN) ──
echo ""
echo "--- Step N: CloudFront Distribution ---"

DIST_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='Sandstone Frontend'].Id" --output text 2>/dev/null)

if [ -z "$DIST_ID" ] || [ "$DIST_ID" = "None" ]; then
  cat > /tmp/cf-config.json << CFEOF
{
  "CallerReference": "sandstone-$(date +%s)",
  "Comment": "Sandstone Frontend",
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-${FRONTEND_BUCKET}",
    "ViewerProtocolPolicy": "redirect-to-https",
    "ForwardedValues": { "QueryString": false, "Cookies": { "Forward": "none" } },
    "MinTTL": 0,
    "DefaultTTL": 86400,
    "MaxTTL": 31536000
  },
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "S3-${FRONTEND_BUCKET}",
        "DomainName": "${FRONTEND_BUCKET}.s3.amazonaws.com",
        "S3OriginConfig": { "OriginAccessIdentity": "" }
      }
    ]
  },
  "Enabled": true,
  "DefaultRootObject": "index.html",
  "CustomErrorResponses": {
    "Quantity": 1,
    "Items": [
      {
        "ErrorCode": 404,
        "ResponseCode": "200",
        "ResponsePagePath": "/index.html",
        "ErrorCachingMinTTL": 300
      }
    ]
  }
}
CFEOF

  DIST_ID=$(aws cloudfront create-distribution \
    --distribution-config file:///tmp/cf-config.json \
    --query 'Distribution.Id' --output text 2>/dev/null || echo "failed")
  echo "Created CloudFront distribution: $DIST_ID"
else
  echo "CloudFront distribution exists: $DIST_ID"
fi

CF_DOMAIN=$(aws cloudfront get-distribution --id $DIST_ID --query 'Distribution.DomainName' --output text 2>/dev/null || echo "pending")
echo "CloudFront domain: $CF_DOMAIN"

# ── Step O: Summary ──
echo ""
echo "=============================================="
echo "  SANDSTONE PHASE 2 — INFRASTRUCTURE COMPLETE"
echo "=============================================="
echo "  Account:         $ACCOUNT_ID"
echo "  Region:          $REGION"
echo "  EC2 IP:          $PUBLIC_IP"
echo "  DB Host:         $DB_HOST"
echo "  Redis Host:      $REDIS_HOST"
echo "  S3 Archive:      $BUCKET_NAME"
echo "  S3 Frontend:     $FRONTEND_BUCKET"
echo "  CloudFront:      $CF_DOMAIN"
echo "  Cognito Pool:    $POOL_ID"
echo "  Cognito Client:  $CLIENT_ID"
echo ""
echo "  SSH:  ssh -i sandstone-key.pem ec2-user@$PUBLIC_IP"
echo ""
echo "  After SSH:"
echo "    cd sandstone"
echo "    export DB_HOST=$DB_HOST"
echo "    export REDIS_HOST=$REDIS_HOST"
echo "    export USE_POSTGRES=true"
echo "    export REDIS_ENABLED=true"
echo "    export COGNITO_USER_POOL_ID=$POOL_ID"
echo "    export COGNITO_APP_CLIENT_ID=$CLIENT_ID"
echo "    python3 -c 'from db.database import init_db; init_db()'"
echo "    gunicorn -w 4 -b 0.0.0.0:5000 app:app"
echo ""
echo "  Frontend deploy:"
echo "    cd frontend && npm install && npm run build"
echo "    aws s3 sync dist/ s3://$FRONTEND_BUCKET/"
echo ""
echo "  Smoke test:"
echo "    curl http://$PUBLIC_IP:5000/health"
echo "    curl https://$CF_DOMAIN"
echo "=============================================="
