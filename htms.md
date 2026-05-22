Here are tailored project examples specifically for the **Medical/Healthcare** and **Personal Banking** domains.

Because Floci uses real container engines under the hood, these projects focus on simulating complex, high-security, and data-heavy workflows entirely on your laptop.

---

### Domain 1: Personal Banking & Fintech

#### 1. Real-Time Transaction Fraud Detection Engine

* **The Architecture:** `API Gateway` ➜ `SQS` ➜ `Lambda` ➜ `ElastiCache (Redis)` + `DynamoDB`
* **The Project:** A high-throughput backend that processes swiped debit/credit card transactions. A transaction request hits the **API Gateway** and is pushed to an **SQS** queue. A **Lambda** function pulls the message and runs a fast compliance check: it queries a **Redis (ElastiCache)** cluster to check the user's velocity limits (e.g., *has this card been used 3 times in the last 60 seconds?*) and reads historical ledger data from **DynamoDB**. If it passes, the transaction is written to the ledger; if it fails, a fraud flag is raised.
* **Why Floci Adds Value:** In banking, transaction latency must be sub-millisecond. Testing Redis cache-eviction policies, SQS message visibility timeouts, and DynamoDB conditional writes locally allows you to stress-test your concurrency logic without incurring high cloud costs or risking real ledger pollution.

#### 2. The Open Banking Financial Analytics Engine

* **The Architecture:** `S3` ➜ `Glue Catalog` ➜ `Athena (via DuckDB sidecar)`
* **The Project:** An internal engine that ingests thousands of raw transaction logs (CSV/Parquet format) from third-party banking APIs into an **S3** bucket. It uses a **Glue Data Catalog** to define the schema, and an analytical service runs **Athena** SQL queries to calculate monthly spending trends, merchant categories, and average balances for personalized user dashboards.
* **Why Floci Adds Value:** Financial data processing requires heavy SQL analytical querying. Floci's native **DuckDB-powered Athena sidecar** allows you to test complex window functions and financial aggregation queries locally on your hard drive, scanning gigabytes of mock financial records instantly and for free.

---

### Domain 2: Medical & Healthcare IT

#### 1. Automated Patient Health Record (PHR) Ingestion Pipeline

* **The Architecture:** `S3` ➜ `Lambda` ➜ `RDS (PostgreSQL)`
* **The Project:** A HIPAA-compliant data pipeline that automatically processes electronic health records (EHR) when uploaded by clinics. When a standardized medical document (like an HL7 or FHIR JSON file) is dropped into an **S3** bucket, an **S3 Event Notification** triggers a **Lambda** function. The Lambda parses the clinical data, validates the patient ID, and securely writes the diagnostic codes and lab results into a relational database (**RDS PostgreSQL**).
* **Why Floci Adds Value:** Handling Protected Health Information (PHI) requires robust schema validation and relational data integrity. Because Floci runs a *real* PostgreSQL instance rather than a basic text mock, you can test complex database migrations, foreign key constraints on medical codes, and file parsing logic entirely offline.

#### 2. Secure Patient Portal Authentication & Audit Logger

* **The Architecture:** `Cognito` ➜ `API Gateway` ➜ `DynamoDB Streams` ➜ `Lambda` ➜ `S3`
* **The Project:** A secure authentication system for a patient portal. Patients log in via **Amazon Cognito User Pools**. Upon successful authentication, they request their medical history via **API Gateway**, which logs a row in a **DynamoDB** audit table. A **DynamoDB Stream** immediately captures this access log and triggers a **Lambda** function to archive the immutable access log into a write-once **S3** bucket for strict compliance auditing.
* **Why Floci Adds Value:** Security and audit trails are paramount in medical tech. Getting Cognito, API Gateway tokens, and DynamoDB Streams to play nicely together is traditionally difficult to orchestrate without a live AWS environment. Floci allows you to test the end-to-end security handshake and verify that the immutable audit trail fires flawlessly before writing a single line of production infrastructure code.
