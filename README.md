# Yo Programmer Email Subscriber (AWS SAM)

This project creates a serverless backend for your landing page:

- Save an email subscriber to DynamoDB
- Fetch all subscribers as a list response
- Send SNS email notification when a new subscriber is saved
- Expose a single API Gateway HTTP API endpoint with throttling

## Prerequisites

- AWS CLI configured
- AWS SAM CLI installed
- Python 3.12

## Deploy

```bash
sam build
sam deploy --guided
```

During guided deploy, provide:

- `NotificationEmail` (email that receives SNS notifications)
- `AllowedOrigin` (for example, your Vercel domain)
- API throttling values if you want to override defaults

After deploy, confirm the SNS email subscription from your inbox.

## API usage

Use stack outputs:

- `SubscribersApiBaseUrl`
- `SubscribersApiPath` (`/subscribers`)

### Save subscriber

```bash
curl -X POST "$API_BASE/subscribers" \
  -H "Content-Type: application/json" \
  -d '{"email":"someone@example.com","name":"Someone","source":"landing-page"}'
```

### List subscribers

```bash
curl "$API_BASE/subscribers"
```
