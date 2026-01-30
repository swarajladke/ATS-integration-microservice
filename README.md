# ATS Integration Microservice

A production-ready, serverless microservice that provides a unified REST API for integrating with Applicant Tracking Systems (ATS). Built with Python on AWS Lambda using the Serverless Framework.

![Architecture](docs/architecture-diagram.png)

## 🌟 Features

- **Unified API**: Single interface for multiple ATS providers
- **Serverless Architecture**: Scales automatically, pay only for what you use
- **Provider Abstraction**: Easy to swap ATS providers without API changes
- **Robust Error Handling**: Normalized error responses, automatic retries
- **Pagination Support**: Handles large datasets transparently
- **Rate Limiting**: Respects ATS API limits with exponential backoff

## 📋 Table of Contents

- [ATS Setup Guide](#ats-setup-guide)
- [Local Development](#local-development)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Architecture](#architecture)
- [Extending the Service](#extending-the-service)

---

## 🔧 ATS Setup Guide

This service currently supports **Greenhouse** as the ATS provider.

### Greenhouse Setup
1. Log in to [app.greenhouse.io](https://app.greenhouse.io).
2. Go to **Configure** -> **Dev Center** -> **API Credentials**.
3. Create a new **Harvest** API key.
4. Copy the key and set `ATS_API_KEY` in your `.env`.

### Workable Setup
1. Log in to [workable.com](https://www.workable.com/).
2. Go to **Settings** -> **Integrations** -> **Apps**.
3. Generate a new token with `r_jobs`, `r_candidates`, and `w_candidates` scopes.
4. Copy the key and set `WORKABLE_API_KEY` and your `WORKABLE_SUBDOMAIN` in your `.env`.
5. See `WORKABLE_SETUP.md` for full details.

### Zoho Recruit Setup
1. Create account: [zoho.in/recruit](https://www.zoho.in/recruit/).
2. Setup OAuth in [api-console.zoho.in](https://api-console.zoho.in/):
   - Create **Server-based Application**.
   - Get **Client ID** and **Client Secret**.
   - Use **Self Client** tab to generate **Authorization Code**.
   - Exchange code for **Refresh Token** (see `ZOHO_SETUP.md`).
3. Set `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN`, and `ZOHO_REGION=in` in your `.env`.

---

## 💻 Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Serverless Framework)
- npm or yarn

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ats-integration-microservice
   ```

2. **Install Node.js dependencies**
   ```bash
   npm install
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env with your credentials
   notepad .env  # Windows
   # or
   nano .env     # Linux/Mac
   ```

   Update the following values:
   ```env
   ATS_PROVIDER=greenhouse
   # ... or ...
   ATS_PROVIDER=zoho_recruit
   ATS_API_KEY=your_greenhouse_api_key_here
   ATS_BASE_URL=https://harvest.greenhouse.io/v1
   LOG_LEVEL=DEBUG
   ```

### Running Locally

Start the local development server:

```bash
# Load environment variables and start server
npm run start
```

Or directly with serverless:

```bash
npx serverless offline
```

The API will be available at `http://localhost:3000`

---

## 📚 API Reference

### GET /jobs

Fetch all jobs from the ATS.

**Request:**
```bash
curl http://localhost:3000/jobs
```

**Optional Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter by status: `OPEN`, `CLOSED`, `DRAFT` |

**Response:**
```json
{
  "jobs": [
    {
      "id": "123456",
      "title": "Senior Software Engineer",
      "location": "San Francisco, CA",
      "status": "OPEN",
      "external_url": "https://boards.greenhouse.io/company/jobs/123456"
    }
  ],
  "total_count": 1
}
```

---

### POST /candidates

Create a new candidate and attach them to a job.

**Request:**
```bash
curl -X POST http://localhost:3000/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "+1-555-123-4567",
    "resume_url": "https://example.com/resume.pdf",
    "job_id": "123456"
  }'
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Candidate's full name |
| email | string | Yes | Candidate's email address |
| phone | string | No | Phone number |
| resume_url | string | No | URL to resume file |
| job_id | string | Yes | Job ID to apply for |

**Response:**
```json
{
  "candidate_id": "789012",
  "application_id": "345678",
  "name": "John Doe",
  "email": "john.doe@example.com",
  "job_id": "123456",
  "status": "APPLIED"
}
```

---

### GET /applications

Fetch applications for a specific job.

**Request:**
```bash
curl "http://localhost:3000/applications?job_id=123456"
```

**Required Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| job_id | string | Job ID to fetch applications for |

**Response:**
```json
{
  "applications": [
    {
      "id": "345678",
      "candidate_name": "John Doe",
      "email": "john.doe@example.com",
      "status": "SCREENING"
    }
  ],
  "job_id": "123456",
  "total_count": 1
}
```

---

### Error Responses

All endpoints return standardized error responses:

```json
{
  "error": "VALIDATION_ERROR",
  "message": "job_id query parameter is required",
  "retryable": false
}
```

**Error Codes:**
| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Invalid request data |
| ATS_AUTHENTICATION_ERROR | 401 | Invalid API credentials |
| ATS_NOT_FOUND | 404 | Resource not found |
| ATS_RATE_LIMIT_ERROR | 429 | Rate limit exceeded |
| ATS_CONNECTION_ERROR | 503 | Cannot connect to ATS |
| ATS_SERVICE_ERROR | 500 | ATS returned an error |
| INTERNAL_ERROR | 500 | Unexpected server error |

---

## 🚀 Deployment

### Deploy to AWS

1. **Configure AWS credentials**
   ```bash
   aws configure
   ```

2. **Deploy to development**
   ```bash
   npm run deploy
   ```

3. **Deploy to production**
   ```bash
   npm run deploy:prod
   ```

### Environment Variables in AWS

Set environment variables in AWS Lambda or use AWS Secrets Manager:

```bash
# Using serverless deploy with env vars
serverless deploy --stage prod \
  --param="ATS_API_KEY=your_key" \
  --param="ATS_BASE_URL=https://harvest.greenhouse.io/v1"
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                             │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────────┐
│  GET /jobs    │   │POST /candidates│  │ GET /applications │
│   Lambda      │   │    Lambda      │   │     Lambda        │
└───────────────┘   └───────────────┘   └───────────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
              ┌─────────────────────────┐
              │    Adapter Factory      │
              │  (Provider Selection)   │
              └─────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
    ┌───────────────────┐         ┌───────────────────┐
    │ Greenhouse Adapter│         │  Future Adapters  │
    │  (Harvest API)    │         │ (Lever, Workday)  │
    └───────────────────┘         └───────────────────┘
              │
              ▼
    ┌───────────────────┐
    │    HTTP Client    │
    │ (Retry, Auth,     │
    │  Rate Limiting)   │
    └───────────────────┘
              │
              ▼
    ┌───────────────────┐
    │   Greenhouse API  │
    └───────────────────┘
```

### Design Decisions

- **Unified API Layer**: Handles HTTP requests/responses and standardizes data models.
- **ATS Adapter Layer**: Provider-specific logic for Greenhouse and **Zoho Recruit**.
- **Integration Layer**: Manages authentication (Basic Auth & OAuth 2.0), retries, and pagination.
- **Transparent Pagination**: The client layer handles pagination internally, abstracting complexity.
- **Retry Logic**: Exponential backoff for transient failures improves reliability.

---

## 🔌 Extending the Service

### Adding a New ATS Provider

1. **Create adapter file** at `src/adapters/{provider}.py`

2. **Implement the BaseATSAdapter interface**:
   ```python
   from .base import BaseATSAdapter
   
   class LeverAdapter(BaseATSAdapter):
       def get_jobs(self, status_filter=None):
           # Implementation
           pass
       
       def create_candidate(self, candidate):
           # Implementation
           pass
       
       def get_applications(self, job_id):
           # Implementation
           pass
       
       def health_check(self):
           # Implementation
           pass
   ```

3. **Register the adapter** in `src/adapters/factory.py`:
   ```python
   from .lever import LeverAdapter
   
   ADAPTER_REGISTRY = {
       "greenhouse": GreenhouseAdapter,
       "lever": LeverAdapter,  # Add new adapter
   }
   ```

4. **Update environment variables**:
   ```env
   ATS_PROVIDER=lever
   ATS_API_KEY=your_lever_api_key
   ATS_BASE_URL=https://api.lever.co/v1
   ```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📧 Support

For support or questions, please open an issue on GitHub.
