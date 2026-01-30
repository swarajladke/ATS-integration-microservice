# API Contract Documentation

This document provides the complete API specification for the ATS Integration Microservice.

## Base URL

- **Local Development**: `http://localhost:3000`
- **Production**: `https://{api-id}.execute-api.{region}.amazonaws.com`

## Authentication

All requests to the external ATS are authenticated using the configured `ATS_API_KEY`. Client requests to this microservice do not require authentication by default (configure API Gateway authorizers for production).

---

## Endpoints

### GET /jobs

Retrieve all jobs from the configured ATS.

#### Request

```http
GET /jobs HTTP/1.1
Host: localhost:3000
```

#### Query Parameters

| Parameter | Type   | Required | Description                              |
|-----------|--------|----------|------------------------------------------|
| status    | string | No       | Filter by status: `OPEN`, `CLOSED`, `DRAFT` |

#### Response

**Status: 200 OK**

```json
{
  "jobs": [
    {
      "id": "string",
      "title": "string",
      "location": "string",
      "status": "OPEN | CLOSED | DRAFT",
      "external_url": "string"
    }
  ],
  "total_count": 0
}
```

#### Example

```bash
# Get all jobs
curl http://localhost:3000/jobs

# Get only open jobs
curl "http://localhost:3000/jobs?status=OPEN"
```

---

### POST /candidates

Create a new candidate and attach them to a job.

#### Request

```http
POST /candidates HTTP/1.1
Host: localhost:3000
Content-Type: application/json

{
  "name": "string",
  "email": "string",
  "phone": "string",
  "resume_url": "string",
  "job_id": "string"
}
```

#### Request Body Schema

| Field      | Type   | Required | Constraints        | Description              |
|------------|--------|----------|--------------------|--------------------------|
| name       | string | Yes      | 1-255 characters   | Candidate's full name    |
| email      | string | Yes      | Valid email format | Candidate's email        |
| phone      | string | No       | Max 50 characters  | Phone number             |
| resume_url | string | No       | Valid URL          | URL to resume file       |
| job_id     | string | Yes      | Non-empty          | Job ID to apply for      |

#### Response

**Status: 201 Created**

```json
{
  "candidate_id": "string",
  "application_id": "string",
  "name": "string",
  "email": "string",
  "job_id": "string",
  "status": "APPLIED"
}
```

#### Example

```bash
curl -X POST http://localhost:3000/candidates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Smith",
    "email": "jane.smith@example.com",
    "phone": "+1-555-987-6543",
    "resume_url": "https://example.com/resumes/jane-smith.pdf",
    "job_id": "456789"
  }'
```

---

### GET /applications

Retrieve applications for a specific job.

#### Request

```http
GET /applications?job_id={job_id} HTTP/1.1
Host: localhost:3000
```

#### Query Parameters

| Parameter | Type   | Required | Description                    |
|-----------|--------|----------|--------------------------------|
| job_id    | string | Yes      | Job ID to fetch applications for |

#### Response

**Status: 200 OK**

```json
{
  "applications": [
    {
      "id": "string",
      "candidate_name": "string",
      "email": "string",
      "status": "APPLIED | SCREENING | REJECTED | HIRED"
    }
  ],
  "job_id": "string",
  "total_count": 0
}
```

#### Example

```bash
curl "http://localhost:3000/applications?job_id=456789"
```

---

## Error Responses

All endpoints return errors in a consistent format.

### Error Response Schema

```json
{
  "error": "string",
  "message": "string",
  "retryable": false,
  "details": {}
}
```

### Error Codes

| Error Code                | HTTP Status | Description                        | Retryable |
|---------------------------|-------------|------------------------------------|-----------|
| VALIDATION_ERROR          | 400         | Request validation failed          | No        |
| ATS_AUTHENTICATION_ERROR  | 401         | Invalid ATS credentials            | No        |
| ATS_NOT_FOUND             | 404         | Resource not found in ATS          | No        |
| ATS_RATE_LIMIT_ERROR      | 429         | ATS rate limit exceeded            | Yes       |
| ATS_SERVICE_ERROR         | 500         | ATS returned an error              | Maybe     |
| ATS_CONNECTION_ERROR      | 503         | Cannot connect to ATS              | Yes       |
| INTERNAL_ERROR            | 500         | Unexpected server error            | No        |

### Error Examples

**Validation Error (400)**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Validation failed",
  "retryable": false,
  "details": {
    "email": "field required",
    "job_id": "field required"
  }
}
```

**Authentication Error (401)**
```json
{
  "error": "ATS_AUTHENTICATION_ERROR",
  "message": "Invalid API credentials",
  "retryable": false
}
```

**Rate Limit Error (429)**
```json
{
  "error": "ATS_RATE_LIMIT_ERROR",
  "message": "ATS rate limit exceeded",
  "retryable": true
}
```

---

## Status Values

### Job Status

| Value   | Description                    |
|---------|--------------------------------|
| OPEN    | Job is accepting applications  |
| CLOSED  | Job is no longer accepting     |
| DRAFT   | Job is not published           |

### Application Status

| Value     | Description                            |
|-----------|----------------------------------------|
| APPLIED   | Initial application submitted          |
| SCREENING | Under review or in interview process   |
| REJECTED  | Application rejected                   |
| HIRED     | Candidate hired                        |

---

## Postman Collection

Import the following collection for easy testing:

```json
{
  "info": {
    "name": "ATS Integration API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "baseUrl",
      "value": "http://localhost:3000"
    }
  ],
  "item": [
    {
      "name": "Get Jobs",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/jobs"
      }
    },
    {
      "name": "Create Candidate",
      "request": {
        "method": "POST",
        "url": "{{baseUrl}}/candidates",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"name\": \"Test User\",\n  \"email\": \"test@example.com\",\n  \"job_id\": \"123456\"\n}"
        }
      }
    },
    {
      "name": "Get Applications",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/applications?job_id=123456"
      }
    }
  ]
}
```
