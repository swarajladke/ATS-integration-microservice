# Architecture Documentation

This document describes the architecture, design patterns, and key decisions for the ATS Integration Microservice.

## Overview

The ATS Integration Microservice is a serverless backend service that provides a unified REST API for integrating with Applicant Tracking Systems (ATS). It abstracts vendor-specific complexity and returns normalized, clean JSON responses.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Clients                                    │
│              (Web Apps, Mobile Apps, Internal Tools)                 │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AWS API Gateway                                 │
│                   (HTTP API, CORS, Routing)                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
┌─────────────────────┐ ┌─────────────────────┐ ┌─────────────────────┐
│   GET /jobs         │ │  POST /candidates   │ │  GET /applications  │
│   Lambda Function   │ │   Lambda Function   │ │   Lambda Function   │
└─────────────────────┘ └─────────────────────┘ └─────────────────────┘
            │                       │                       │
            └───────────────────────┼───────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Adapter Layer                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │  Adapter        │  │   Greenhouse    │  │    Future       │     │
│  │  Factory        │──│   Adapter       │  │   Adapters      │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Integration Layer                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │
│  │   HTTP Client   │  │   Pagination    │  │   Rate Limit    │     │
│  │   (Retries)     │  │   Handler       │  │   Handler       │     │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    External ATS APIs                                 │
│           (Greenhouse Harvest API, Lever, Workday, etc.)            │
└─────────────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### 1. Unified API Layer (Lambda Handlers)

**Location**: `src/handlers/`

Responsibilities:
- Handle HTTP requests from API Gateway
- Parse and validate request parameters
- Invoke the appropriate adapter methods
- Format responses in a consistent JSON structure
- Handle errors and return standardized error responses

**Key Files**:
- `jobs.py` - GET /jobs endpoint
- `candidates.py` - POST /candidates endpoint
- `applications.py` - GET /applications endpoint

### 2. Adapter Layer

**Location**: `src/adapters/`

Responsibilities:
- Abstract ATS-specific API differences
- Map vendor data formats to unified models
- Normalize status values and field names
- Enable provider swapping without API changes

**Key Components**:
- `BaseATSAdapter` - Abstract interface all adapters implement
- `GreenhouseAdapter` - Greenhouse Harvest API implementation
- `AdapterFactory` - Creates appropriate adapter based on config

**Adding New Adapters**:
```python
# 1. Create adapter class
class LeverAdapter(BaseATSAdapter):
    # Implement all abstract methods
    pass

# 2. Register in factory
ADAPTER_REGISTRY["lever"] = LeverAdapter

# 3. Configure environment
ATS_PROVIDER=lever
```

### 3. Integration Layer

**Location**: `src/client/`

Responsibilities:
- Make HTTP requests to external APIs
- Handle authentication (Basic Auth, OAuth, etc.)
- Implement retry logic with exponential backoff
- Handle rate limiting (429 responses)
- Manage pagination across all pages

**Key Components**:
- `HTTPClient` - Robust HTTP client with retry logic
- `PaginationHandler` - Handles Link-header and cursor pagination

### 4. Data Models

**Location**: `src/models/`

Unified data models using Pydantic:
- `Job` - Normalized job posting
- `CandidateCreate` / `CandidateResponse` - Candidate data
- `Application` - Normalized job application

**Status Normalization**:
```
Greenhouse Status → Unified Status
─────────────────────────────────
open             → OPEN
closed           → CLOSED
draft            → DRAFT
application      → APPLIED
phone screen     → SCREENING
rejected         → REJECTED
hired            → HIRED
```

## Design Patterns

### Adapter Pattern

The adapter pattern abstracts ATS-specific implementations behind a common interface. This allows:
- Easy addition of new ATS providers
- Swapping providers without code changes
- Testing with mock adapters

```python
class BaseATSAdapter(ABC):
    @abstractmethod
    def get_jobs(self) -> List[Job]: ...
    
    @abstractmethod
    def create_candidate(self, data: CandidateCreate) -> CandidateResponse: ...
    
    @abstractmethod
    def get_applications(self, job_id: str) -> List[Application]: ...
```

### Factory Pattern

The adapter factory selects and instantiates the appropriate adapter:

```python
def get_adapter() -> BaseATSAdapter:
    provider = config.ats_provider
    adapter_class = ADAPTER_REGISTRY[provider]
    return adapter_class()
```

### Retry Pattern

Transient failures are handled with exponential backoff:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RetryableError)
)
def _make_request(self, ...):
    # Request logic
```

## Error Handling Strategy

### Error Classification

| Error Type | Retryable | Action |
|------------|-----------|--------|
| Connection Error | Yes | Retry with backoff |
| Rate Limit (429) | Yes | Retry after delay |
| Server Error (5xx) | Yes | Retry with backoff |
| Auth Error (401) | No | Return error immediately |
| Validation Error | No | Return error with details |
| Not Found (404) | No | Return error immediately |

### Error Abstraction

Vendor-specific errors are abstracted to hide implementation details:

```python
# Greenhouse error
{"status": 401, "message": "Invalid Harvest API key"}

# Becomes unified error
{
  "error": "ATS_AUTHENTICATION_ERROR",
  "message": "ATS authentication failed",
  "retryable": false
}
```

## Pagination Strategy

The service handles ATS pagination transparently:

1. **Link Header Pagination** (Greenhouse)
   - Parses `Link` header for `rel="next"`
   - Follows links until no more pages

2. **Offset Pagination** (Some providers)
   - Increments offset by page size
   - Stops when items < page size

3. **Cursor Pagination** (Future)
   - Tracks cursor from response
   - Passes cursor to next request

## Security Considerations

1. **Credential Management**
   - API keys stored in environment variables
   - Never logged or included in error responses
   - Use AWS Secrets Manager in production

2. **Error Sanitization**
   - Vendor error details hidden from clients
   - Stack traces only in debug mode
   - Generic messages for internal errors

3. **Input Validation**
   - Pydantic models validate all input
   - Type checking and constraint enforcement
   - SQL injection not applicable (no database)

## Performance Optimizations

1. **Connection Pooling**: HTTP session reuse
2. **Caching**: LRU cache for config loading
3. **Pagination Limits**: Max pages to prevent runaway requests
4. **Timeout Configuration**: 30-second request timeout

## Interview Talking Points

Key design decisions to discuss:

1. **Why Adapter Pattern?**
   - Enables multi-vendor support
   - Isolates vendor-specific code
   - Facilitates testing with mocks

2. **Why Serverless?**
   - Cost-effective for variable load
   - No infrastructure management
   - Automatic scaling

3. **How is reliability achieved?**
   - Retry with exponential backoff
   - Rate limit handling
   - Timeout configuration

4. **How to add a new ATS?**
   - Implement BaseATSAdapter
   - Register in factory
   - Configure environment

5. **Security best practices**
   - Environment variables for secrets
   - Error sanitization
   - Input validation
