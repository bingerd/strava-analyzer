# Strava Analytics Platform (Near-Zero Cost)

This document describes an end-to-end architecture to ingest, store, query, and expose **Strava activity data** using Google Cloud. The design prioritizes:

* Near-zero monthly cost
* Clean separation of concerns
* SQL-first analytics
* Easy extension to APIs and dashboards

The target user is **a single athlete / personal analytics project**, but the architecture scales cleanly.

---

## High-Level Architecture

```
Strava API & Webhooks
        |
        v
Cloud Run (Webhook + API)
        |
        v
Pub/Sub (event buffer)
        |
        v
GCS (Raw JSON data lake)
        |
        v
BigQuery (External → Native tables)
        |
        v
SQL Views (Semantic layer)
        |
        +--> Streamlit dashboards
        +--> REST API on your domain
```

---

## 1. Ingestion Layer

### 1.1 Full Historical Load (One-Time / Backfills)

**Goal:** Load all historical Strava data into a raw data lake.

**How:**

* Use a Cloud Run job or local script
* Authenticate with Strava OAuth
* Pull paginated data via Strava REST API:

  * Activities
  * Activity streams
  * Athlete profile
  * Gear

**Output:**

* Write raw JSON files to GCS
* Do not transform data at this stage

**Example GCS layout:**

```
gs://strava-raw/
  activities/
    year=2026/month=01/day=06/
      activity_123456.json
  streams/
  athletes/
  gear/
```

This creates an **immutable, replayable source of truth**.

---

### 1.2 Incremental Ingestion (Webhooks)

Strava webhooks only send **event notifications**, not full activity payloads.

**Flow:**

1. Strava sends webhook → Cloud Run endpoint
2. Validate webhook signature
3. Publish event to Pub/Sub
4. Worker pulls event:

   * Calls Strava API for full activity
   * Writes raw JSON to GCS

**Why Pub/Sub?**

* Retry safety
* Loose coupling
* Easy to add more consumers later

---

## 2. Storage Layer

### 2.1 Raw Data Lake (GCS)

* Stores raw Strava JSON
* Very cheap (pennies per month)
* Supports schema evolution and reprocessing

This layer is **append-only** and never updated.

---

### 2.2 Analytics Warehouse (BigQuery)

#### Phase 1: External Tables

* Create BigQuery external tables pointing to GCS JSON
* Enables immediate querying
* Zero storage cost

Good for prototyping and validation.

#### Phase 2: Native BigQuery Tables (Recommended)

* Transform raw data into structured tables
* Partition by activity start date
* Cluster by athlete_id / sport_type

**Example tables:**

* `activities_fact`
* `activity_streams`
* `athletes_dim`
* `gear_dim`

Benefits:

* Faster queries
* Lower query cost
* Cleaner schemas

---

## 3. Semantic (SQL) Layer

Before building APIs or dashboards, define a **semantic layer** using SQL views.

**Example view:**

```sql
CREATE VIEW v_activity_summary AS
SELECT
  activity_id,
  start_date,
  sport_type,
  distance_m / 1000 AS distance_km,
  moving_time_sec / 60 AS moving_time_min
FROM activities_fact;
```

**Example metric query:**

```sql
SELECT MIN(start_date)
FROM v_activity_summary
WHERE sport_type = 'Run'
  AND distance_km >= 10;
```

This prevents metric drift and duplicated logic.

---

## 4. API Layer (Attach to Your Domain)

Deploy a **thin API** on Cloud Run:

* Framework: FastAPI or Flask
* Auth: API key / JWT / OAuth (as needed)
* Executes parameterized BigQuery SQL

**Example endpoints:**

```
GET /metrics/first-10k
GET /activities?from=2024-01-01
GET /stats/weekly-mileage
```

Why not expose BigQuery directly?

* Security
* Cost control
* Input validation
* Future caching

---

## 5. Visualization Layer

### Streamlit

* Connects directly to BigQuery
* Reads from semantic views
* Zero backend logic

**Hosting:**

* Run Streamlit on Cloud Run
* Single user = free tier
* Optional IAP / OAuth protection

Perfect for personal dashboards and exploration.

---

## 6. Cost Expectations

For a single athlete:

| Service   | Expected Monthly Cost |
| --------- | --------------------- |
| Cloud Run | $0.00                 |
| Pub/Sub   | $0.00                 |
| GCS       | ~$0.02                |
| BigQuery  | $0.00                 |
| Streamlit | $0.00                 |
| **Total** | **$0.00–$0.10**       |

Most months will show **$0.00**.

---

## 7. Guardrails to Stay in Free Tier

### Do

* Partition BigQuery tables by date
* Use views for all analytics
* Limit Streamlit auto-refresh
* Set Cloud Run CPU only during requests
* Configure GCP budget alerts

### Avoid

* Unpartitioned BigQuery tables
* `SELECT *` scans
* BigQuery streaming inserts
* Continuous polling jobs
* Public high-traffic dashboards

---

## 8. Minimal Implementation Order

1. Cloud Run webhook → Pub/Sub → GCS
2. Full historical loader → GCS
3. BigQuery external tables
4. Native BigQuery tables + views
5. Streamlit dashboard
6. Public API (optional)

---

## 9. Why This Architecture Works

* Near-zero cost
* Production-grade
* SQL-first
* Easy to reprocess data
* Scales without redesign

This setup lets you answer questions like:

> "When did I run my first 10K?"

…and later add APIs, dashboards, or more athletes with minimal effort.
