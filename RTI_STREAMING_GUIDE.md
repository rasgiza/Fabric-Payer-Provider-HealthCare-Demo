# Real-Time Intelligence (RTI) Streaming Guide

## Overview

This guide covers the Real-Time Intelligence (RTI) streaming pipeline in the Healthcare Demo. 
It explains the two Eventstream ingestion modes, their trade-offs, known Fabric API limitations, 
and the exact steps a new user needs after cloning the repo.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Cell 12 (Healthcare_Launcher) — ONE-TIME SETUP                    │
│  • Creates Eventhouse + KQL DB + Eventstream                       │
│  • Wires Eventstream topology (source → destinations) via API      │
│  • Prints 3 steps:                                                 │
│    Step A: Enable OneLake Availability on KQL DB (portal)          │
│    Step B: Copy Eventstream connection string (portal)             │
│    Step C: (Optional) Switch to Direct Ingestion (portal)          │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Cell 13 (Healthcare_Launcher) — RUN THE PIPELINE                  │
│  1. Creates OneLake shortcuts in lh_gold_curated:                  │
│     rti_claims_events → KQL claims_events                          │
│     rti_adt_events    → KQL adt_events                             │
│     rti_rx_events     → KQL rx_events                              │
│  2. Triggers PL_Healthcare_RTI pipeline                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PL_Healthcare_RTI Pipeline                                        │
│                                                                    │
│  ┌──────────────────────────────────┐                              │
│  │  NB_RTI_Event_Simulator          │                              │
│  │  • Reads dims from lh_gold_curated (patients, providers, etc)   │
│  │  • Generates 10 batches × 500 claims + 250 ADT + 166 Rx        │
│  │  • Pushes JSON events → Eventstream Custom Endpoint             │
│  │  • Each event tagged with _table field for routing              │
│  └──────────────┬───────────────────┘                              │
│                 ▼                                                   │
│  ┌──────────────────────────────────────────────────┐              │
│  │  Eventstream (Healthcare_RTI_Eventstream)        │              │
│  │  All events land in rti_all_events (single table)│              │
│  │  KQL update policies split into typed tables:    │              │
│  │  ├─→ claims_events (via ExtractClaimsEvents())   │              │
│  │  ├─→ adt_events    (via ExtractAdtEvents())      │              │
│  │  └─→ rx_events     (via ExtractRxEvents())       │              │
│  └──────────────┬───────────────────────────────────┘              │
│                 ▼                                                   │
│  ╔══════════════════════════════════════════════════╗               │
│  ║  OneLake Availability (enabled on KQL DB)        ║               │
│  ║  KQL tables → Delta Parquet files in OneLake     ║               │
│  ║  (adaptive batching, ~5 min with mirroring policy)║              │
│  ╚══════════════╤═══════════════════════════════════╝               │
│                 ▼                                                   │
│  ╔══════════════════════════════════════════════════╗               │
│  ║  OneLake Shortcuts (in lh_gold_curated)          ║               │
│  ║  rti_claims_events → KQL claims_events           ║               │
│  ║  rti_adt_events    → KQL adt_events              ║               │
│  ║  rti_rx_events     → KQL rx_events               ║               │
│  ╚══════════════╤═══════════════════════════════════╝               │
│                 ▼                                                   │
│  ┌────────────────────┐ ┌────────────────────┐ ┌────────────────┐  │
│  │ NB_RTI_Fraud_      │ │ NB_RTI_Care_Gap_   │ │ NB_RTI_High    │  │
│  │ Detection          │ │ Alerts             │ │ Cost_Trajectory│  │
│  │ (parallel)         │ │ (parallel)         │ │ (parallel)     │  │
│  │                    │ │                    │ │                │  │
│  │ READ:              │ │ READ:              │ │ READ:          │  │
│  │ rti_claims_events  │ │ rti_adt_events     │ │ rti_claims     │  │
│  │ dim_provider       │ │ care_gaps          │ │ rti_adt        │  │
│  │ fact_claim (hist)  │ │ hedis_measures     │ │ dim_patient    │  │
│  │                    │ │                    │ │                │  │
│  │ WRITE:             │ │ WRITE:             │ │ WRITE:         │  │
│  │ rti_fraud_scores   │ │ rti_care_gap_alerts│ │ rti_highcost_  │  │
│  │ (Delta + KQL)      │ │ (Delta + KQL)      │ │ alerts         │  │
│  └────────────────────┘ └────────────────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Eventstream Ingestion Modes (Critical Concept)

The Eventstream → Eventhouse destination supports two ingestion modes. Understanding 
the difference is essential for this demo to work correctly.

### Processed Ingestion (default — deployed by API)

| Property | Value |
|----------|-------|
| Internal name | `KustoPushMode` |
| How it works | Events route through Azure Stream Analytics (ASA) before landing in KQL |
| Latency | 30–120 seconds |
| Update policies | ❌ **NOT triggered** — data lands in `rti_all_events` but does NOT auto-route to `claims_events`, `adt_events`, `rx_events` |
| Connection required | No — the API can deploy this without any Kusto connection |
| Column mapping | Auto-maps JSON fields to table columns |

**Why the API uses this mode:** The Fabric REST API cannot create the Kusto OAuth2 
connection required for Direct Ingestion. Processed Ingestion is the only mode 
that can be fully deployed programmatically (zero portal clicks for the Eventstream wiring itself).

**How scoring notebooks handle this:** Each scoring notebook includes a 3-step 
backfill pattern:
1. Wait for `rti_all_events` to have data (polls every 30s, up to 3 min)
2. Run the Extract function (e.g., `ExtractClaimsEvents()`) directly as a query 
   to backfill the typed table
3. Confirm data is present, then proceed with scoring

This means **the demo works with Processed Ingestion** — just with slightly more 
latency and the backfill step.

### Direct Ingestion (recommended — requires portal step)

| Property | Value |
|----------|-------|
| Internal name | `KustoPullMode` |
| How it works | Events stream directly into the KQL engine (no ASA intermediary) |
| Latency | Sub-second |
| Update policies | ✅ **Triggered automatically** — data in `rti_all_events` is instantly routed to typed tables |
| Connection required | Yes — a Kusto-type connection (OAuth2) must exist |
| Column mapping | Uses the JSON ingestion mapping defined on the table |

**Why this is better for production:** Update policies fire on every ingestion batch, 
so `claims_events`, `adt_events`, and `rx_events` populate within seconds of events 
arriving. Scoring notebooks find data already present and skip the backfill.

**How to switch (one-time portal step):**
1. Open Healthcare_RTI_Eventstream in the Fabric portal
2. Click the **HealthcareEventhouse** destination node → **Delete** it
3. Click **Add destination** → **Eventhouse**
4. Select **Healthcare_RTI_DB** → table `rti_all_events`
5. Choose **Direct Ingestion** → **Publish**

Fabric auto-creates and attaches the required Kusto connection. No manual 
connection configuration needed.

> **Why can't this be automated?** The Fabric REST API does not support creating 
> Kusto-type (OAuth2) connections programmatically. The `connectionName` field 
> in the topology definition requires a pre-existing connection that can only 
> be created through the Fabric Portal UI. Additionally, you cannot change a 
> destination's ingestion mode in-place — you must delete and recreate the node.

---

## Known Fabric API Limitations (as of April 2026)

| Limitation | Impact | Workaround |
|-----------|--------|-----------|
| Cannot create Kusto OAuth2 connections via REST API | Direct Ingestion cannot be deployed programmatically | Use Processed Ingestion via API + manual portal switch |
| Cannot change ingestion mode on existing destination node | Attempting `KustoPushMode → KustoPullMode` returns error | Delete old node, create new one |
| Custom Endpoint connection string not exposed via API | Simulator needs it but API doesn't return it | User copies from portal |
| OneLake Availability has no public API to enable | KQL → Delta mirroring requires portal toggle | One-time manual step |
| `connectionName: null` causes Warning status on DirectIngestion nodes | Node appears unhealthy even if topology is pushed | Must have valid connection (portal-created) |

---

## Data Flow Summary

| Step | Source | Destination | Mechanism |
|------|--------|-------------|-----------|
| Simulator → Eventstream | Generated events | Eventstream Custom Endpoint | EventHub SDK (`azure-eventhub`) |
| Eventstream → KQL | Eventstream | `rti_all_events` (landing table) | Eventstream destination (Processed or Direct) |
| Update policies → typed tables | `rti_all_events` | `claims_events`, `adt_events`, `rx_events` | KQL update policies (auto with Direct; backfill with Processed) |
| KQL → OneLake | KQL tables | Delta Parquet files in OneLake | OneLake Availability (mirroring policy, ~5 min) |
| OneLake → lh_gold_curated | OneLake Delta files | `rti_claims_events`, `rti_adt_events`, `rti_rx_events` | OneLake Shortcuts (created by Cell 13) |
| Scoring notebooks READ | `lh_gold_curated.rti_*` | Spark DataFrames | `spark.table()` reads shortcut as Delta |
| Scoring notebooks WRITE | Scored results | `lh_gold_curated.rti_fraud_scores` (Delta) + `fraud_scores` (KQL) | `saveAsTable` + Kusto SDK ingestion |

---

## Setup Steps (New User After Cloning)

### Prerequisites
- Healthcare_Launcher Cell 1–11 completed (lakehouses, notebooks, data deployed)
- `DEPLOY_STREAMING = True` in the Configuration cell
- An **active Fabric F capacity**. F8 can run the demo at modest scale; use a
  larger capacity when you need more headroom for concurrent Spark, KQL,
  Eventstream, Power BI, and agent workloads. RTI does not require F64.

### Step 1: Run Cell 12 (RTI Deployment) — Automated
Cell 12 deploys all RTI artifacts:
- Eventhouse + KQL Database (from Git artifacts)
- Runs `NB_RTI_Setup_Eventhouse` (creates 6 KQL tables + streaming policies + update policies + mirroring policies)
- Creates and wires the Eventstream topology via API (Processed Ingestion mode)
- Creates OperationsAgent

### Step 2: Enable OneLake Availability (Portal — One-Time)
1. Open **Healthcare_RTI_DB** in the Fabric portal
2. In the **Database details** pane → **OneLake** section
3. Set **Availability** → **Enabled**
4. Check **"Apply to existing tables"** → confirm

This exposes KQL tables as Delta Parquet in OneLake. The mirroring policy (set by `NB_RTI_Setup_Eventhouse`) flushes data every 5 minutes.

> **Why can't this be automated?** OneLake Availability is a portal-only toggle — there is no public REST API or KQL command to enable it programmatically as of April 2026.

### Step 3: Copy the Eventstream Connection String (Portal)
1. Open **Healthcare_RTI_Eventstream** in the Fabric portal
2. Click the **HealthcareCustomEndpoint** source node
3. Copy the **Connection String** (includes EntityPath)

### Step 4: Run Cell 13 (Pipeline Trigger) — Automated
1. Paste the connection string into `ES_CONNECTION_STRING`
2. Run Cell 13

Cell 13 will:
1. **Create OneLake shortcuts** in `lh_gold_curated` pointing to the KQL tables
2. **Trigger PL_Healthcare_RTI** which runs:
   - `NB_RTI_Event_Simulator` — streams 10 batches of events
   - `NB_RTI_Fraud_Detection` — scores claims for fraud (parallel)
   - `NB_RTI_Care_Gap_Alerts` — checks ADT events against HEDIS gaps (parallel)
   - `NB_RTI_HighCost_Trajectory` — rolling cost analysis (parallel)

### Step 5: Switch to Direct Ingestion (Portal — Optional, Recommended)
1. Open **Healthcare_RTI_Eventstream** in the Fabric portal
2. Click the **HealthcareEventhouse** destination → **Delete** it
3. **Add destination** → Eventhouse → Healthcare_RTI_DB → table `rti_all_events`
4. Choose **Direct Ingestion** → **Publish**

After this, update policies fire automatically on every ingestion batch. The scoring 
notebooks' backfill logic becomes a no-op (data is already in typed tables).

> **When to do Step 5:** You can do this before or after Step 4. If done before, 
> the simulator's events will immediately populate typed tables without backfill delay. 
> If done after, it applies to all future pipeline runs.

## Timing & Latency

### With Direct Ingestion (Step 5 completed)

| Component | Latency |
|-----------|---------|
| Simulator → Eventstream | ~1 second per batch |
| Eventstream → rti_all_events | Sub-second |
| Update policies → typed tables | Sub-second (automatic) |
| KQL → OneLake (Delta) | ~5 minutes (mirroring policy) |
| OneLake → Shortcut read | Instant |
| **End-to-end (event → scoring)** | **~5-6 minutes** (dominated by OneLake flush) |

### With Processed Ingestion (default, no Step 5)

| Component | Latency |
|-----------|---------|
| Simulator → Eventstream | ~1 second per batch |
| Eventstream → rti_all_events | 30–120 seconds (ASA buffering) |
| Update policies → typed tables | ❌ Not triggered — requires notebook backfill |
| Notebook backfill | ~30 seconds (runs Extract function as query) |
| KQL → OneLake (Delta) | ~5 minutes (mirroring policy) |
| **End-to-end (event → scoring)** | **~7-8 minutes** |

The scoring notebooks include **wait/retry logic** — they poll `rti_all_events` every 
30 seconds for up to 3 minutes, waiting for Eventstream to deliver data. Then they run 
the backfill, wait for OneLake to flush, and proceed with scoring.

## Artifacts

| Artifact | Type | Purpose |
|----------|------|---------|
| `Healthcare_RTI_Eventhouse` | Eventhouse | Hosts the KQL database |
| `Healthcare_RTI_DB` | KQL Database | 6 tables (3 input + 3 scored output) |
| `Healthcare_RTI_Eventstream` | Eventstream | Routes events from Custom Endpoint → KQL |
| `NB_RTI_Setup_Eventhouse` | Notebook | Creates KQL tables, streaming + mirroring policies |
| `NB_RTI_Event_Simulator` | Notebook | Generates streaming claims/ADT/Rx events |
| `NB_RTI_Fraud_Detection` | Notebook | Scores claims for fraud risk |
| `NB_RTI_Care_Gap_Alerts` | Notebook | Checks ADT events against open HEDIS gaps |
| `NB_RTI_HighCost_Trajectory` | Notebook | Rolling 30d/90d spend + ED visit analysis |
| `NB_RTI_Operations_Agent` | Notebook | AI agent for RTI operational queries |
| `PL_Healthcare_RTI` | Pipeline | Orchestrates Simulator → 3 scoring notebooks |
| `Healthcare RTI Dashboard` | KQL Dashboard | 4-page real-time dashboard (30s auto-refresh) |

## KQL Tables

### Input Tables (from Eventstream)
| Table | Events | Key Fields |
|-------|--------|------------|
| `claims_events` | Claims submissions | claim_id, patient_id, provider_id, claim_amount, injected_fraud_flags |
| `adt_events` | Admit/Discharge/Transfer | patient_id, facility_id, admission_type, has_open_care_gaps |
| `rx_events` | Prescription fills | patient_id, medication_code, drug_class, quantity |

### Output Tables (from Scoring Notebooks)
| Table | Scores | Key Fields |
|-------|--------|------------|
| `fraud_scores` | Fraud risk per claim | fraud_score (0-100), risk_tier, fraud_flags |
| `care_gap_alerts` | Care gap notifications | measure_id, gap_days_overdue, alert_priority |
| `highcost_alerts` | High-cost member flags | rolling_spend_30d/90d, ed_visits_30d, cost_trend |

## Troubleshooting

### Scoring notebooks fail with "table not found" or empty data

1. **Check ingestion mode:** If using Processed Ingestion (default), ensure the 
   notebooks have the backfill logic (they should — it's built in). The typed tables 
   (`claims_events`, `adt_events`) won't auto-populate without Direct Ingestion.
2. Verify OneLake Availability is **enabled** on Healthcare_RTI_DB (portal)
3. Verify the simulator ran and pushed events (check `rti_all_events | count` in KQL)
4. Verify shortcuts exist in lh_gold_curated (Tables tab should show `rti_claims_events`, etc.)
5. Wait 5 minutes — OneLake mirroring may not have flushed yet

### Eventstream destination shows "Warning" status

This typically means the `connectionName` is null. This happens when Direct Ingestion 
is deployed via API without a pre-existing Kusto connection. Fix: delete the destination 
and re-add via the Fabric portal (which auto-creates the connection).

### Eventstream connection string not working

1. Open Healthcare_RTI_Eventstream → click HealthcareCustomEndpoint
2. Ensure the source status is "Created" (not "Creating" or "Error")
3. Copy the full connection string including the EntityPath

### Update policies not firing (typed tables empty but rti_all_events has data)

You're on **Processed Ingestion** mode. Two options:
- **Quick fix:** The scoring notebooks already include backfill logic that runs 
  `ExtractClaimsEvents()` / `ExtractAdtEvents()` as direct queries
- **Permanent fix:** Switch to Direct Ingestion (see Step 5 above)

Verify update policies exist:
```kql
.show table claims_events policy update
.show table adt_events policy update
.show table rx_events policy update
```

### Pipeline times out

- The simulator runs 10 batches with 5-second intervals (~50 seconds)
- Scoring notebooks wait up to 3 minutes for `rti_all_events` + backfill + OneLake sync
- Total expected time: ~8-10 minutes

### Capacity not active

All Fabric operations (topology push, notebook runs, KQL queries) require an active 
capacity. Resume it from the Azure Portal → your Fabric capacity resource → **Resume**.
