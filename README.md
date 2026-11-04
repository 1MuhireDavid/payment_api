# Loan Repayment API

A Django REST Framework backend for managing loan repayments through
mobile money providers, with an initial integration structure for MTN
Mobile Money and Airtel Money.

> **Implementation status:** This repository is a development
> foundation. Before production use, complete and verify
> provider-specific API authentication, callback signature verification,
> callback payload mapping, idempotency race handling, reconciliation,
> automated tests, and deployment security. The example provider
> adapters in this project must be checked against the exact MTN and
> Airtel developer documentation and credentials issued for your account
> and country.

------------------------------------------------------------------------

## Table of Contents

1.  [Project Overview](#project-overview)
2.  [System Requirements](#system-requirements)
3.  [Architecture](#architecture)
4.  [Payment Lifecycle](#payment-lifecycle)
5.  [Project Structure](#project-structure)
6.  [Getting Started](#getting-started)
7.  [Environment Configuration](#environment-configuration)
8.  [Database Models](#database-models)
9.  [API Reference](#api-reference)
10. [Example API Requests](#example-api-requests)
11. [Webhook Processing](#webhook-processing)
12. [Running the Project](#running-the-project)
13. [Testing](#testing)
14. [Security and Reliability](#security-and-reliability)
15. [Known Limitations and Next
    Steps](#known-limitations-and-next-steps)
16. [Troubleshooting](#troubleshooting)

------------------------------------------------------------------------

## 1. Project Overview

The Loan Repayment API provides backend endpoints for:

-   Receiving authenticated loan repayment requests.
-   Validating the requested loan, amount, mobile money provider, and
    phone number.
-   Creating and tracking payment records.
-   Initiating payment requests through a provider adapter.
-   Receiving provider callbacks (webhooks).
-   Recording successful repayments and reducing the outstanding loan
    balance.
-   Exposing payment and repayment history to the authenticated
    customer.

### Main technologies

  -----------------------------------------------------------------------
  Technology                          Purpose
  ----------------------------------- -----------------------------------
  Python                              Backend programming language

  Django                              Backend web framework

  Django REST Framework               REST API and request validation

  MySQL                               Relational database

  JWT                                 API authentication

  Requests                            Outbound HTTP requests to payment
                                      providers

  drf-spectacular                     OpenAPI schema and Swagger
                                      documentation

  Celery and Redis                    Optional background processing and
                                      retry infrastructure
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 2. System Requirements

Recommended development environment:

-   Python 3.11 or later (use a version supported by your installed
    Django release).
-   Django 5.2.
-   MySQL 8 or a compatible MySQL server.
-   pip and a Python virtual environment.
-   Git.
-   MTN and/or Airtel developer sandbox credentials for provider
    integration testing.
-   A public HTTPS callback URL for testing provider webhooks.

Check your installed versions:

``` bash
python --version
pip --version
mysql --version
```

------------------------------------------------------------------------

## 3. Architecture

### 3.1 High-level system architecture

The system uses a layered architecture. The client communicates with the
Django REST API. The API validates the request and coordinates database
operations and payment-provider communication. Providers send
asynchronous callbacks to the webhook endpoints after processing a
transaction.

``` mermaid
flowchart TB
    Client["Frontend / API Client"]
    API["Django REST API"]
    Auth["JWT Authentication"]
    Payments["Payments Application"]
    Loans["Loans Application"]
    DB[("MySQL Database")]
    Router["Provider Service Selector"]
    MTN["MTN Mobile Money API"]
    Airtel["Airtel Money API"]
    Webhooks["Webhook Endpoints"]
    Repayments["Repayment Records and Loan Balance Update"]

    Client -->|"HTTPS: POST /api/payments/"| API
    API --> Auth
    Auth --> Payments
    Payments <--> Loans
    Payments <--> DB
    Payments --> Router
    Router --> MTN
    Router --> Airtel
    MTN -->|"Asynchronous callback"| Webhooks
    Airtel -->|"Asynchronous callback"| Webhooks
    Webhooks -->|"Verify, validate and process"| Repayments
    Repayments <--> DB
    Client -->|"GET payment / history"| API
```

### 3.2 Architectural components

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  Client                              Sends repayment requests and checks
                                      payment status

  Django REST API                     Receives HTTP requests and returns
                                      JSON responses

  JWT Authentication                  Identifies the customer making an
                                      API request

  Loans app                           Stores loan information and
                                      outstanding balances

  Payments app                        Creates payments, tracks statuses,
                                      and exposes payment history

  Providers app                       Contains provider-specific adapters
                                      for MTN and Airtel

  Webhooks app                        Receives and processes asynchronous
                                      provider notifications

  MySQL                               Persistently stores users, loans,
                                      payments, events, and repayments
  -----------------------------------------------------------------------

### 3.3 Design principles

-   **Separation of concerns:** loan management, payment processing,
    provider communication, and callback handling are separated into
    Django apps.
-   **Provider abstraction:** a provider selector chooses the relevant
    adapter without placing provider-specific HTTP logic in the payment
    view.
-   **Traceability:** each payment has an internal reference that can be
    used to correlate provider activity.
-   **Idempotency:** clients and callback handlers should safely handle
    repeated requests and notifications.
-   **Data integrity:** database transactions and row-level locking help
    protect loan balances from concurrent updates.
-   **Authentication and ownership:** customers should only access their
    own loans and payment records.

------------------------------------------------------------------------

## 4. Payment Lifecycle

### 4.1 Successful repayment flow

``` mermaid
sequenceDiagram
    participant C as Client
    participant API as Django API
    participant DB as MySQL
    participant P as MTN / Airtel
    participant W as Webhook API

    C->>API: POST /api/payments/ + JWT + Idempotency-Key
    API->>API: Authenticate and validate request
    API->>DB: Check loan ownership and available balance
    API->>DB: Create PENDING payment
    API->>P: Initiate mobile money collection
    P-->>API: Initial acknowledgement
    API-->>C: 202 Accepted, payment reference and status
    P->>W: Asynchronous payment callback
    W->>W: Verify callback authenticity and map provider payload
    W->>DB: Record event and lock payment/loan
    W->>DB: Mark payment SUCCESS or FAILED
    alt Payment successful
        W->>DB: Create repayment record
        W->>DB: Reduce outstanding loan balance
    end
    W-->>P: Acknowledge callback
    C->>API: GET /api/payments/{id}/
    API-->>C: Latest payment status
```

### 4.2 Payment statuses

  -----------------------------------------------------------------------
  Status                              Meaning
  ----------------------------------- -----------------------------------
  `PENDING`                           The payment has been created and is
                                      awaiting a final provider result

  `SUCCESS`                           The provider has confirmed
                                      successful payment

  `FAILED`                            The provider has confirmed that the
                                      payment failed
  -----------------------------------------------------------------------

An HTTP acknowledgement from a provider is not necessarily proof that
the customer has paid. The final payment status should be based on an
authenticated provider callback or a trusted status-reconciliation
request.

------------------------------------------------------------------------

## 5. Project Structure

The project is organized into Django apps:

``` text
payment-api/
├── __init__.py
├── settings.py
├── urls.py
├── asgi.py
└── wsgi.py
│
├── loans/
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
│
├── payments/
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
│
├── providers/
│   └── services/
│       ├── __init__.py
│       ├── base.py
│       ├── mtn.py
│       └── airtel.py
│
├── webhooks/
│   ├── migrations/
│   ├── views.py
│   ├── urls.py
│   └── admin.py
│
├── manage.py
├── requirements.txt
├── .env
└── README.md
```

### App responsibilities

-   `loans`: loan model, loan serializer, and loan-related operations.
-   `payments`: payment and repayment models, request serializers,
    payment endpoints, and payment history.
-   `providers`: reusable provider interface and MTN/Airtel service
    adapters.
-   `webhooks`: provider callback endpoints and event processing.
-   `config`: Django settings and root URL configuration.

------------------------------------------------------------------------

## 6. Getting Started

### 6.1 Clone the repository

``` bash
git clone https://github.com/1MuhireDavid/payment_api.git
cd payment-api
```

If you have not created a remote repository yet, create the project
directory and enter it:

``` bash
mkdir payment-api
cd payment-api
```

### 6.2 Create and activate a virtual environment

Windows PowerShell:

``` powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Windows Command Prompt:

``` cmd
python -m venv venv
venv\Scripts\activate
```

Linux or macOS:

``` bash
python3 -m venv venv
source venv/bin/activate
```

### 6.3 Install dependencies

Create or update `requirements.txt` with the packages used by your
project. For example:

``` text
Django>=5.2,<5.3
djangorestframework
djangorestframework-simplejwt
mysqlclient
python-dotenv
requests
drf-spectacular
django-cors-headers
gunicorn
```

Install them:

``` bash
pip install -r requirements.txt
```

Celery and Redis can be added when background jobs and retry queues are
implemented.

### 6.4 Create the Django project and apps

If you are starting from an empty directory:

``` bash
django-admin startproject config .
python manage.py startapp loans
python manage.py startapp payments
python manage.py startapp providers
python manage.py startapp webhooks
```

If the project and apps already exist, do not run these commands again.

------------------------------------------------------------------------

## 7. Environment Configuration

### 7.1 Create the MySQL database

Log in to MySQL:

``` sql
CREATE DATABASE loan_payment_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

CREATE USER 'loan_api_user'@'localhost'
IDENTIFIED BY 'replace_with_a_strong_password';

GRANT ALL PRIVILEGES ON loan_payment_db.*
TO 'loan_api_user'@'localhost';

FLUSH PRIVILEGES;
```

Use a dedicated database account and a strong password. Adjust the host
and permissions to match your deployment environment.

### 7.2 Create `.env`

Create a `.env` file in the project root:

``` env
SECRET_KEY=replace_with_a_long_random_secret
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=loan_payment_db
DB_USER=loan_api_user
DB_PASSWORD=replace_with_a_strong_password
DB_HOST=127.0.0.1
DB_PORT=3306

# MTN sandbox settings: use values issued by the MTN developer portal
MTN_BASE_URL=https://sandbox.momodeveloper.mtn.com
MTN_SUBSCRIPTION_KEY=
MTN_API_USER=
MTN_API_KEY=
MTN_TARGET_ENVIRONMENT=sandbox
MTN_CALLBACK_URL=

# Airtel settings: use exact URLs and credentials issued for your account
AIRTEL_AUTH_URL=
AIRTEL_COLLECTION_URL=
AIRTEL_CLIENT_ID=
AIRTEL_CLIENT_SECRET=
AIRTEL_COUNTRY=RW
```

Create `.env.example` with the same variable names but no real secrets.
Commit `.env.example`, not `.env`.

Add these entries to `.gitignore`:

``` gitignore
venv/
.venv/
__pycache__/
*.py[cod]
.env
*.sqlite3
staticfiles/
media/
.pytest_cache/
.coverage
```

### 7.3 Configure Django settings

Ensure `config/settings.py` loads environment variables and includes the
required applications. A typical setup includes:

``` python
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",
    "loans",
    "payments",
    "providers",
    "webhooks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Loan Repayment API",
    "DESCRIPTION": "API for processing and tracking loan repayments.",
    "VERSION": "1.0.0",
}

MTN_BASE_URL = os.getenv("MTN_BASE_URL")
MTN_SUBSCRIPTION_KEY = os.getenv("MTN_SUBSCRIPTION_KEY")
MTN_API_USER = os.getenv("MTN_API_USER")
MTN_API_KEY = os.getenv("MTN_API_KEY")
MTN_TARGET_ENVIRONMENT = os.getenv("MTN_TARGET_ENVIRONMENT", "sandbox")
MTN_CALLBACK_URL = os.getenv("MTN_CALLBACK_URL")

AIRTEL_AUTH_URL = os.getenv("AIRTEL_AUTH_URL")
AIRTEL_COLLECTION_URL = os.getenv("AIRTEL_COLLECTION_URL")
AIRTEL_CLIENT_ID = os.getenv("AIRTEL_CLIENT_ID")
AIRTEL_CLIENT_SECRET = os.getenv("AIRTEL_CLIENT_SECRET")
AIRTEL_COUNTRY = os.getenv("AIRTEL_COUNTRY", "RW")
```

This is a configuration reference. Merge it into your existing settings
rather than replacing project-specific settings such as templates,
static files, password validators, and internationalization
configuration.

------------------------------------------------------------------------

## 8. Database Models

The main domain entities are:

### Loan

Represents a customer's loan.

Typical fields:

-   `customer`: owner of the loan.
-   `principal_amount`: original loan amount.
-   `outstanding_balance`: remaining amount to repay.
-   `currency`: currency code, such as `RWF`.
-   `status`: active, paid, or defaulted.

### Payment

Represents an attempt to make a repayment through a mobile money
provider.

Typical fields:

-   `loan`: loan being repaid.
-   `provider`: `MTN` or `AIRTEL`.
-   `amount` and `currency`.
-   `phone_number`.
-   `status`: pending, success, or failed.
-   `idempotency_key`: client-supplied unique request key.
-   `provider_reference`: internal reference used to correlate the
    provider transaction.
-   `provider_transaction_id`: provider's transaction identifier, when
    supplied.

### Repayment

Represents a confirmed repayment. A one-to-one relationship with
`Payment` prevents more than one repayment record from being created for
the same payment.

### ProviderEvent

Stores received provider callback events so duplicate notifications can
be detected and audited.

**Important:** A payment should only create a repayment record and
reduce the loan balance after an authenticated, validated success
confirmation. Never reduce the loan balance merely because the client
submitted a request or the provider acknowledged initiation.

------------------------------------------------------------------------

## 9. API Reference

The endpoints below assume the root URL configuration includes:

``` python
path("api/payments/", include("payments.urls")),
path("api/webhooks/", include("webhooks.urls")),
```

### 9.1 Authentication

If using Simple JWT, expose token endpoints in `config/urls.py`:

``` python
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns += [
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
```

  Method   Endpoint                     Purpose
  -------- ---------------------------- ----------------------------------
  POST     `/api/auth/token/`           Obtain access and refresh tokens
  POST     `/api/auth/token/refresh/`   Refresh an access token

### 9.2 Payment endpoints

  -----------------------------------------------------------------------------------
  Method            Endpoint                      Purpose           Authentication
  ----------------- ----------------------------- ----------------- -----------------
  POST              `/api/payments/`              Submit a loan     JWT required
                                                  repayment request 

  GET               `/api/payments/`              List the          JWT required
                                                  authenticated     
                                                  customer's        
                                                  payments          

  GET               `/api/payments/{id}/`         Retrieve a        JWT required
                                                  payment belonging 
                                                  to the customer   

  GET               `/api/payments/repayments/`   Retrieve          JWT required
                                                  confirmed         
                                                  repayment history 

  POST              `/api/webhooks/mtn/`          Receive MTN       Provider
                                                  provider callback verification
                                                                    required

  POST              `/api/webhooks/airtel/`       Receive Airtel    Provider
                                                  provider callback verification
                                                                    required
  -----------------------------------------------------------------------------------

The webhook endpoints are server-to-server endpoints. They should not
rely on customer JWT authentication; they must authenticate callbacks
using the provider's documented mechanism.

### 9.3 Create payment request

`POST /api/payments/`

Required headers:

``` http
Authorization: Bearer <access_token>
Content-Type: application/json
Idempotency-Key: <unique-uuid>
```

Request body:

``` json
{
  "loan_id": 1,
  "amount": "50000.00",
  "provider": "MTN",
  "phone_number": "+250788123456"
}
```

Example accepted response:

``` json
{
  "message": "Payment request submitted successfully",
  "payment": {
    "id": 12,
    "loan": 1,
    "provider": "MTN",
    "amount": "50000.00",
    "currency": "RWF",
    "phone_number": "+250788123456",
    "status": "PENDING",
    "provider_reference": "generated-reference",
    "created_at": "2026-01-01T10:00:00Z",
    "updated_at": "2026-01-01T10:00:00Z"
  }
}
```

The exact response fields depend on your serializer. The example is
illustrative.

### 9.4 Get payment status

`GET /api/payments/12/`

Headers:

``` http
Authorization: Bearer <access_token>
```

The API should return only payments associated with the authenticated
customer.

### 9.5 Get payment history

`GET /api/payments/`

Returns the authenticated customer's payment records, newest first.

### 9.6 Get repayment history

`GET /api/payments/repayments/`

Returns confirmed repayment records belonging to the authenticated
customer.

------------------------------------------------------------------------

## 10. Example API Requests

### 10.1 Obtain a JWT token

``` bash
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}'
```

Use the returned access token in subsequent authenticated requests.

### 10.2 Submit a repayment

``` bash
curl -X POST http://127.0.0.1:8000/api/payments/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -d '{
    "loan_id": 1,
    "amount": "50000.00",
    "provider": "MTN",
    "phone_number": "+250788123456"
  }'
```

For another distinct payment attempt, generate a new UUID idempotency
key. Reuse the same key only when retrying the exact same logical
request.

### 10.3 Check payment status

``` bash
curl -X GET http://127.0.0.1:8000/api/payments/12/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

------------------------------------------------------------------------

## 11. Webhook Processing

A webhook is an HTTP request sent by the payment provider to your
backend to report a transaction result.

### Expected processing sequence

1.  Receive the callback over HTTPS.
2.  Verify the callback using the provider's documented authentication
    or signature mechanism.
3.  Parse the provider-specific payload.
4.  Match the callback to the correct internal payment reference.
5.  Validate provider transaction ID, amount, currency, and final status
    where the provider supplies these fields.
6.  Deduplicate the event using the provider's event or transaction
    identifier.
7.  Lock the relevant payment and loan rows within a database
    transaction.
8.  If successful, mark the payment successful, create one repayment
    record, and reduce the outstanding balance once.
9.  If failed, mark the payment failed without changing the loan
    balance.
10. Return the acknowledgement expected by the provider.

### Webhook security warning

Do not accept a callback as genuine merely because it contains a known
payment reference. Anyone who can reach a public endpoint could
otherwise attempt to forge a success notification.

The callback authentication, event ID, status mapping, and payload
fields must be implemented separately for MTN and Airtel based on their
official documentation. The generic webhook example is not a substitute
for those checks.

### Local webhook testing

A provider cannot normally call `localhost` directly. Use a secure
tunnelling service or a deployed HTTPS development environment to expose
your local callback endpoint. Configure the resulting public HTTPS URL
in the provider sandbox portal and your environment variables.

------------------------------------------------------------------------

## 12. Running the Project

Apply migrations:

``` bash
python manage.py makemigrations
python manage.py migrate
```

Create an administrator:

``` bash
python manage.py createsuperuser
```

Start the development server:

``` bash
python manage.py runserver
```

The API will normally be available at:

``` text
http://127.0.0.1:8000/
```

Django admin:

``` text
http://127.0.0.1:8000/admin/
```

Create a test customer and loan using your configured user model and
admin interface before testing a repayment request.

------------------------------------------------------------------------

## 13. Testing

Run the Django test suite:

``` bash
python manage.py test
```

At minimum, implement automated tests for:

### Request validation

-   Missing required fields.
-   Invalid loan ID.
-   Invalid provider.
-   Invalid phone number.
-   Zero or negative payment amount.
-   Missing or malformed idempotency key.

### Authorization

-   Unauthenticated customer cannot create a payment.
-   Customer cannot pay another customer's loan.
-   Customer cannot retrieve another customer's payment or repayment
    history.

### Payment processing

-   Valid request creates a pending payment.
-   Payment amount cannot exceed the available outstanding balance.
-   Repeated request with the same idempotency key does not create a
    second payment.
-   Reusing an idempotency key with different request data is rejected.
-   Provider rejection and network timeout are handled safely.

### Webhooks and data integrity

-   Invalid callback authentication is rejected.
-   Duplicate callback does not create a second repayment.
-   Successful callback reduces the loan balance exactly once.
-   Failed callback does not reduce the loan balance.
-   Concurrent payment requests cannot reserve more than the available
    balance.
-   Provider transaction IDs cannot be applied to multiple payments.

Use mocked provider HTTP requests in automated tests. Do not depend on
live mobile money services for normal unit tests.

------------------------------------------------------------------------

## 14. Security and Reliability

Before deployment:

-   Set `DEBUG=False`.
-   Use a strong, private `SECRET_KEY`.
-   Keep provider credentials and database passwords out of source
    control.
-   Enforce HTTPS.
-   Configure `ALLOWED_HOSTS` and CORS for trusted origins only.
-   Verify provider callbacks using the official provider mechanism.
-   Validate callback amount, currency, transaction reference, and
    status.
-   Apply ownership checks to every customer-facing payment and loan
    query.
-   Use database transactions and appropriate row locking for balance
    updates.
-   Handle duplicate client requests and provider callbacks.
-   Do not log access tokens, API keys, secrets, or unnecessary personal
    data.
-   Configure request timeouts for outbound provider calls.
-   Add reconciliation for payments whose provider result is uncertain.
-   Use background jobs for retryable provider calls and reconciliation
    where appropriate.
-   Back up the database and monitor failed transactions.

A network timeout is an **uncertain outcome**, not proof of failure. Do
not automatically create a new charge after a timeout. First check the
original transaction with the provider or through a reconciliation
process.

------------------------------------------------------------------------

## 15. Known Limitations and Next Steps

The architecture and starter implementation provide a foundation, but
the following work must be completed and verified:

1.  **Provider API integration:** verify MTN and Airtel authentication,
    endpoints, payloads, and response handling against the credentials
    and documentation for the target environment.
2.  **Provider callback verification:** implement the actual
    authentication/signature validation for each provider.
3.  **Provider-specific callback parsers:** map each provider's real
    payload and status codes to the internal payment lifecycle.
4.  **Idempotency race handling:** handle simultaneous requests using
    the same idempotency key, including database uniqueness conflicts.
5.  **Payment reconciliation:** query the provider when initiation or
    callback outcomes are uncertain.
6.  **Automated tests:** cover permissions, balances, concurrency,
    retries, and duplicate callbacks.
7.  **API documentation:** expose and maintain an OpenAPI/Swagger
    schema.
8.  **Deployment:** configure HTTPS, production database credentials,
    logging, monitoring, backups, and secure secret management.

Do not describe the system as production-ready until these items have
been implemented and tested.

------------------------------------------------------------------------

## 16. Troubleshooting

### MySQL connection error

Check that:

-   MySQL is running.
-   The database exists.
-   The database username and password are correct.
-   The host and port match your MySQL configuration.
-   The database user has permissions on the project database.
-   The `mysqlclient` package is installed correctly.

### `401 Unauthorized`

Check that:

-   You obtained a valid JWT access token.
-   The request includes `Authorization: Bearer <access_token>`.
-   The token has not expired.

### `404 Loan not found or not active`

Check that:

-   The loan exists.
-   The loan belongs to the authenticated user.
-   The loan status is `ACTIVE`.

### Provider request fails

Check that:

-   The sandbox credentials are valid.
-   The configured base URL and endpoint are correct.
-   The provider environment matches the credentials.
-   The request payload follows the provider's current documentation.
-   Your server can reach the provider endpoint.

Do not mark an uncertain transaction as failed until its status has been
confirmed or reconciled.

### Webhook is not received

Check that:

-   The callback URL is publicly reachable over HTTPS.
-   The callback URL is registered in the provider environment.
-   Your development tunnel is still running, if one is being used.
-   The provider has been configured to send the relevant event.
-   Your server logs show incoming callback requests.

------------------------------------------------------------------------

## License

Add the license required by your organization or assessment
instructions.
