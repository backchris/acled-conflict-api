<div align="center">
  <img src="https://public.flourish.studio/uploads/1125160/8f5d756a-56f6-4d8f-a450-67c757d5e242.png" alt="ACLED Logo" width="180">
</div>

# ACLED Conflict API Exercise
Christopher Back 11/12/25

REST API for querying Armed Conflict Location & Event Data (ACLED) ready for use by analysts tracking geopolitical violence.

Contains JWT authentication, interactive API documentation, and comprehensive testing.

## Overview

This API provides endpoints to:
- **Query conflict data** by country with pagination and filtering by list of countries
- **Calculate average risk scores** for a country, across its multiple admin1 regions with caching
- **Submit user text feedback** on conflict regions (authenticated)
- **Manage conflict records** (admin-only deletion)
- **Interactive Swagger documentation** at `/apidocs/`

**Tech stack used**: Flask, SQLAlchemy, PostgreSQL, JWT, Pydantic, Flasgger

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Example curl or Postman Requests](#example-curl-or-postman-requests)
3. [Project Structure](#project-structure)
4. [Design Decisions & Tradeoffs Notes](#design-decisions--tradeoffs-notes)
5. [Testing](#testing--run-all-tests)
6. [Docker Setup](#docker-containers---services)
7. [Troubleshooting](#troubleshooting)
8. [Support & Questions](#support--questions)

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OR optionally to run manually: Python 3.11+, PostgreSQL 15, Redis 7

### Option 1: Docker (Recommended - easiest 1 step setup)

```bash
# Clone and navigate to project
git clone https://github.com/backchris/acled-conflict-api.git
cd acled-conflict-api

# Build and start containers
docker-compose up -d --build

# Verify API is running (optional - containers are already healthy due to healthcheck)
curl http://localhost:5001/health
# Expected: {"status": "ok"}

# To restart app/database, run the following then run docker-compose up -d --build again: 
docker-compose down
```

**Access the API**:
- **API Base URL**: `http://localhost:5001`
- **OpenAPI Swagger UI Documentation**: `http://localhost:5001/apidocs/`
- **Health Check**: `http://localhost:5001/health`
- **Postman Collection**: (`ACLED_API_Postman_Collection.json`)

### [Optional] Option 2: Local Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your database credentials

# Create database and import sample data
python3 scripts/import_csv.py data/acled_sample_conflict_data.csv

# Run Flask app
python3 run.py
```

---

## Example curl or Postman Requests

**Quick start**: Download the **Postman collection** file (`ACLED_API_Postman_Collection.json`) included in this repository for pre-configured requests.
- **NOTE**: Postman cannot designate a user and return an admin_token. If you want to test admin functions (delete endpoint) follow instructions on using curl commands! More notes on authentication are documented on [Notes on Authentication](#notes-on-authentication)

**[Optional] Alternatively if you wanted to use curl commands**:

```bash
# Health Check
curl -X GET http://localhost:5001/health

# Authentication - Admin Setup Flow
# 1. Register admin user
curl -X POST http://localhost:5001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin#password123"}'

# 2. Promote user to admin via database (MANUAL STEP)
docker-compose exec db psql -U acled_user -d acled_db -c \
  "UPDATE users SET is_admin = true WHERE username = 'admin';"

# 3. Login as admin
ADMIN_TOKEN=$(curl -s -X POST http://localhost:5001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin#password123"}' \
  | jq -r '.access_token')

# Authentication - Regular User Setup
# 4. Register regular user
curl -X POST http://localhost:5001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "test#password123"}'

# 5. Login as regular user
USER_TOKEN=$(curl -s -X POST http://localhost:5001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "test#password123"}' \
  | jq -r '.access_token')

# Conflict Data Endpoints - Read Operations
# 6. Get all conflicts (paginated)
curl -X GET "http://localhost:5001/conflictdata?page=1&per_page=10" \
  -H "Authorization: Bearer $USER_TOKEN"

# 7. Search by country
curl -X GET http://localhost:5001/conflictdata/Sudan \
  -H "Authorization: Bearer $USER_TOKEN"

# 8. Get risk score for a country
curl -X GET http://localhost:5001/conflictdata/Sudan/riskscore \
  -H "Authorization: Bearer $USER_TOKEN"

# Conflict Data Endpoints - Write Operations
# 9. Post user feedback (authenticated user)
curl -X POST http://localhost:5001/conflictdata/Khartoum/userfeedback \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Situation escalated significantly in this region"}'

# If you're logged in as an admin - use $ADMIN_TOKEN instead:
curl -X POST http://localhost:5001/conflictdata/Khartoum/userfeedback \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "Situation escalated significantly in this region"}'

# 10. Delete conflict data (admin only)
curl -X DELETE http://localhost:5001/conflictdata \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"country": "Nigeria", "admin1": "Adamawa"}'
```
### Notes on Authentication

**Note**: Admin role assignment requires direct database access (via `psql` or Docker). There is no API endpoint for this as secutiy best practice — admin roles should only be assigned by database administrators, not through the API.

**To promote a user to admin** (one-time setup):
```bash
docker-compose exec postgres psql -U postgres -d acled_conflict_api -c \
  "UPDATE users SET is_admin = true WHERE username = 'admin';"
```
Endpoint documentation are all here: **interactive Swagger UI** at `http://localhost:5001/apidocs/`.

### Password Requirements

Passwords must meet these requirements:
- **Minimum 8 characters**
- **Must include special character '#'**

**Valid examples**:
- `secure#password123`
- `test#Password1`
- `my#super#secure#pwd`

**Invalid examples**:
- `password123` (missing #)
- `pwd#1` (too short)
---
---

## Project Structure

```
acled-conflict-api/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── config.py                # Configuration classes
│   ├── extensions.py            # SQLAlchemy, JWT initialization
│   ├── models.py                # Database models
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── auth_utils.py            # Password hashing, JWT decorators
│   ├── routes/
│   │   ├── auth.py              # Authentication endpoints
│   │   └── conflict.py          # Conflict data endpoints
│   └── specs/                   # OpenAPI YAML specifications
│       ├── auth_register.yaml
│       ├── auth_login.yaml
│       ├── conflict_get_all.yaml
│       ├── conflict_get_country.yaml
│       ├── conflict_riskscore.yaml
│       ├── conflict_feedback.yaml
│       ├── conflict_delete.yaml
│       └── health.yaml
├── scripts/
│   └── import_csv.py            # CSV data import script
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_auth_routes.py
│   ├── test_auth_utils.py
│   ├── test_conflict_routes.py
│   ├── test_models.py
│   └── test_schemas.py
├── data/
│   └── acled_sample_conflict_data.csv  # 3,528 conflict records
├── run.py                       # Flask entry point
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container image
├── docker-compose.yml           # Multi-container setup
└── README.md                    # This file
```

---

## Design Decisions & Tradeoffs Notes

### Database Schema & Entities

For this project I choose to use four tables:

1. **users** — Stores user accounts and authentication
   - `id` (primary key)
   - `username` (unique, indexed)
   - `password_hash` (bcrypt algorithm)
   - `is_admin` (boolean)
   - `created_at` (timestamp)

2. **conflict_data** — Stores raw conflict records - given from requirements (all 3,528 imported from original csv file)
   - `id` (primary key)
   - `country` (str, indexed)
   - `admin1` (str)
   - `population` (nullable)
   - `events` (numeric)
   - `score` (numeric)
   - Unique constraint on (country, admin1) which enables safe CSV re-import 

3. **feedback** — User feedback on regions
   - `id` (primary key)
   - `user_id` (foreign key → users)
   - `country` (indexed)
   - `admin1` (indexed with country)
   - `text` (10- 500 char max)
   - `created_at` (indexed)

4. **risk_cache** — Pre-computed average risk scores
   - `id` (primary key)
   - `country` (unique, indexed)
   - `avg_score` (float)
   - `computed_at` (timestamp)

### Key Features


**JWT Authentication**
 As per requirements used JWT Auth which features secure bcrypt password hashing. Uses JWT tokens with identity + admin claims.


**Data Validation**
- Pydantic schemas for all requests/responses which automatically validates datatypes for both requests and responses with bodies

**API Documentation**
- Interactive Swagger UI at `http://localhost:5001/apidocs/`
- 8 external YAML specification files separated under app/specs/
- Postman collection you can import for testing

**Error Handling**
- Use standard HTTP status codes (201, 400, 403, 404, 409, 500). 
These are documented more in depth in the YAML spec files, and in Swagger UI

**Performance Optimizations**
- Risk score caching (avoid repeated aggregations)
- Pagination for large result sets (memory-efficient)
- Strategic database indexing

## Security Measures

### SQL Injection Prevention

2 design decisions which prevents SQL injection:
**1. SQLAlchemy ORM with Parameterized Queries**
All database queries use SQLAlchemy's parameterized query API, which separates SQL code from data, as opposed to executing queries directly using db.session.execute. Example:
```python
ConflictData.query.filter(ConflictData.country.in_(country_list))
```
**2. URL Parameter Validation**
Input validation on all URL path parameters to reject suspicious characters, which validates that country only contains alphanumeric, spaces, commas:
```python
if not all(c.isalnum() or c in ' ,' for c in country):
    return {'error': 'Invalid characters'}, 400
```

## Performance/Optimization Notes Including Tradeoffs

1. **Country lookups** are indexed on conflict_data.country
    - **Tradeoffs**:
        - index at idx_country` works at (O(log n)). Slower writes, minimal impact on write volume 

2. **Risk scores**: cached in risk_cache table
   - First request: computes average via SQL aggregation + caches
   - Subsequent requests: instant O(1) lookup
   - **Tradeoffs**:
      - Cache table lookup (O(1)) after first computation leads to ,memory cost of about 5KB per country, in exchange for huge latency savings 

   - **Tradeoffs**:
      - **Redis/Celery implementation**: I thought of opting for Redis/Celery implementation of handling average risk score calculation as a true 'background job' by handling 
    calculations asynchronously, caching them, and returning them to users much closer to instantaneously on their second request for the same query.

    However, I've opted not to since it may have been scope creep and too complex for the assignment.
    It would also require the user to always submit two GET requests for every riskscore request. 

3. **Feedback queries**: composite index on (country, admin1)
   - Efficient region-specific feedback lookup, prevents full table scan
   - **Tradeoffs**:
      - Indexing with a composite `(country, admin1)` index leads to slightly slower writes, in exchange for faster reads

4. **Pagination**: limit/offset with ordering
   - Avoids loading entire dataset into memory
   - **Tradeoffs**:
      - LIMIT/OFFSET with ordering is standard approach, works well for result sets


**Overall Tradeoff decision**: Prioritized read performance over write speed. APIs are typically read-heavy (100:1 ratio), and geopolitical data changes infrequently, relative to highly dynamic user-based social media data (Twitter).

---

##  Other Useful Tech Specs

###  Data Import

Sample conflict data is automatically imported with Docker on container startup (3,528 records).

**To re-import manually**:
```bash
# Via Docker
docker-compose exec api python3 scripts/import_csv.py data/acled_sample_conflict_data.csv

# Via local setup
python3 scripts/import_csv.py data/acled_sample_conflict_data.csv
```

---

### Testing- Run All Tests

```bash
# Via Docker
docker-compose exec api pytest -v

# Via local setup
pytest -v
```

### Test Coverage

**50 tests across**:
- Authentication (register, login, password validation)
- Conflict data endpoints (list, filter, risk score)
- User feedback (authenticated, text length validation)
- Admin deletion (authorization checks)
- Error handling (404, 403, 400, 409)
- Database transactions and rollback

**Coverage**: 95%+ of code

---

### Docker Containers - Services

**postgres** — PostgreSQL 15 database
- Port: 5432
- Credentials: postgres/postgres
- Database: acled_conflict_api

**api** — Flask REST API
- Port: 5001
- Auto-imports sample data on startup
- Debug mode enabled

### Useful Docker Commands

```bash
# View logs
docker-compose logs api       # API logs
docker-compose logs postgres  # Database logs

# Access database
docker-compose exec postgres psql -U postgres -d acled_conflict_api

# Restart containers
docker-compose restart

# Stop containers
docker-compose down

# Stop and remove volumes
docker-compose down -v
```
## Troubleshooting

### API won't start

**Check logs**:
```bash
docker-compose logs api | tail -50
```

**Common issues**:
- Port 5001 already in use: `lsof -i :5001` and kill process
- Database not ready: Wait 15 seconds after `docker-compose up`
- Permission denied: Run with `sudo` or fix Docker socket permissions

### Database connection error

```bash
# Verify PostgreSQL is healthy
docker-compose ps

# Check database credentials in docker-compose.yml
# Ensure DATABASE_URL in .env matches

# Reset database
docker-compose down -v
docker-compose up -d --build
```

### JWT token expired

- Tokens expire after 1 hour (configurable in `app/config.py`)
- Login again to get a new token

### Admin user can't delete records

- Ensure user has `is_admin = True` in database
- Check Authorization header: `Authorization: Bearer <TOKEN>`

---

### Support & Questions

If you encounter more issues

1. Check the **Swagger UI** at `/apidocs/` for endpoint documentation
2. Review **test files** for usage examples
3. Check **docker-compose logs** for error messages
4. Verify **database schema** with: 
   ```bash
   docker-compose exec postgres psql -U postgres -d acled_conflict_api -c "\dt"
   ```
