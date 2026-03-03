# Sandstone Phase 2 Deployment Guide

## Quick Start

1. Create AWS CodeStar Connection to GitHub in Console
2. Deploy stack: aws cloudformation deploy --template-file cloudformation/sandstone-stack.yaml --stack-name sandstone-production --capabilities CAPABILITY_NAMED_IAM
3. Push to main branch - CodePipeline auto-deploys
4. Verify: curl https://CLOUDFRONT_DOMAIN/api/health

## Routing

CloudFront /api/* -> EC2 nginx (strips /api prefix) -> Flask :5000

## Cost: ~60-65 USD/mo
