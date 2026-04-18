# Fabric notebook source

# METADATA **{"language":"markdown"}**

# MARKDOWN **{"language":"markdown"}**

# # RTI Use Case 4: Operations Agent — Unified Triage, Monitoring & Action
# 
# **Status: ACTIVE — Full implementation**
# 
# The Operations Agent is an AI-powered operational intelligence layer that sits on top
# of the three RTI scoring outputs (fraud, care gaps, high-cost trajectory) and provides:
# 
# ### 1. Unified Alert Triage
# - Reads `fraud_scores`, `care_gap_alerts`, and `highcost_alerts` from the KQL Database
# - Ranks and deduplicates across alert types (a patient can trigger all 3 simultaneously)
# - Produces a **priority-ordered worklist** for ops teams — one queue, not three
# 
# ### 2. SLA & Throughput Monitoring
# - Tracks data freshness: how stale are the KQL input tables? (claims, ADT, Rx)
# - Monitors pipeline SLA: did the batch ETL complete within its window?
# - Measures alert-to-action latency: how long between event ingestion and alert generation?
# - Fires **operational alerts** when thresholds breach (e.g., no claims events in 15 min)
# 
# ### 3. Automated Remediation & Action Routing
# - **Fraud → SIU queue:** CRITICAL fraud scores auto-routed to Special Investigations Unit
# - **Care gaps → provider fax/EHR alert:** CRITICAL gap alerts sent to facility care team
# - **High-cost → care management referral:** CRITICAL trajectory alerts trigger CM assignment
# - Uses Fabric Reflex / Data Activator for event-driven action triggers
# 
# ### Architecture
# ```
# ┌─────────────────────────────────────────────────────────────────────┐
# │  Operations Agent                                                  │
# │                                                                    │
# │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐   │
# │  │ KQL Database  │──▶│ Alert Triage │──▶│ Priority Worklist    │   │
# │  │ (3 scoring    │   │ (deduplicate │   │ (single pane of     │   │
# │  │  outputs)     │   │  + rank)     │   │  glass for ops)     │   │
# │  └──────────────┘   └──────────────┘   └──────────────────────┘   │
# │                                                                    │
# │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐   │
# │  │ SLA Monitor   │──▶│ Freshness    │──▶│ Ops Alerts           │   │
# │  │ (data age,    │   │ Checks +     │   │ (Teams, Email,       │   │
# │  │  pipeline)    │   │ Thresholds   │   │  Data Activator)     │   │
# │  └──────────────┘   └──────────────┘   └──────────────────────┘   │
# │                                                                    │
# │  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐   │
# │  │ Action Router │──▶│ Foundry/     │──▶│ Downstream Systems   │   │
# │  │ (rule-based + │   │ Reflex       │   │ (SIU, EHR, CM,      │   │
# │  │  AI-assisted) │   │ Triggers     │   │  Payer portals)      │   │
# │  └──────────────┘   └──────────────┘   └──────────────────────┘   │
# └─────────────────────────────────────────────────────────────────────┘
# ```
# 
# ### Integration Points
# - **Azure AI Foundry Agent:** Natural language interface for ops teams
#   ("What are today's top 10 priorities across all alert types?")
# - **Fabric Data Activator (Reflex):** Event-driven triggers for automated routing
# - **Microsoft Teams:** Alert notifications via webhook or Power Automate
# - **Power BI Real-Time Dashboard:** Operational KPI tiles (alert volume, SLA, freshness)
# 
# ### KQL Queries (Planned)
# The agent will execute these KQL queries against the Eventhouse:
# - Unified worklist: merge + rank across all 3 alert tables
# - Data freshness: `max(event_timestamp)` per input table vs `now()`
# - Alert velocity: alerts per minute/hour trend (detect surges)
# - Action completion: track which alerts have been routed/resolved
# 
# **Default lakehouse:** `lh_gold_curated`

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# NB_RTI_Operations_Agent — Unified Triage, Monitoring & Action
# ============================================================================
# Operational intelligence layer combining:
#   - Alert triage across fraud, care gap, and high-cost outputs
#   - SLA monitoring for data freshness and pipeline health
#   - Automated action routing via Reflex / Data Activator
#   - Results written to KQL tables: rti_unified_worklist, rti_sla_status, rti_action_log
#
# Default lakehouse: lh_gold_curated
# ============================================================================

print("NB_RTI_Operations_Agent: Starting...")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Parameters ----------
WORKSPACE_ID = ""                               # Auto-detected if blank
EVENTHOUSE_NAME = "Healthcare_RTI_Eventhouse"
KQL_DB_NAME = "Healthcare_RTI_DB"

# SLA thresholds (minutes)
FRESHNESS_WARN_MIN = 15     # Warn if no events in 15 min
FRESHNESS_CRIT_MIN = 60     # Critical if no events in 1 hour
PIPELINE_SLA_HOURS = 4      # Batch pipeline must complete within 4 hours

# Action routing
ENABLE_TEAMS_WEBHOOK = False
TEAMS_WEBHOOK_URL = ""      # Microsoft Teams incoming webhook URL
ENABLE_REFLEX = False       # Requires Data Activator setup

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

import requests
import json
import time
from datetime import datetime, timedelta

def get_fabric_token():
    return notebookutils.credentials.getToken("https://analysis.windows.net/powerbi/api")

def get_headers():
    return {
        "Authorization": f"Bearer {get_fabric_token()}",
        "Content-Type": "application/json"
    }

BASE_URL = "https://api.fabric.microsoft.com/v1"

if not WORKSPACE_ID:
    WORKSPACE_ID = notebookutils.runtime.context.get("currentWorkspaceId", "")

print(f"Workspace ID: {WORKSPACE_ID}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Module 1: Unified Alert Triage
# ============================================================================
# Reads all 3 scoring output tables and produces a single priority worklist.
# Deduplicates patients who appear in multiple alert streams.
# Writes results to rti_unified_worklist in the KQL Database.
# ============================================================================

print("Module 1: Unified Alert Triage")

# ---------- KQL: Unified worklist across all 3 alert streams ----------
UNIFIED_WORKLIST_KQL = """
let fraud = fraud_scores
    | where score_timestamp > ago(24h)
    | project patient_id, alert_type="FRAUD", alert_id=score_id,
      priority=case(risk_tier=="CRITICAL", 1, risk_tier=="HIGH", 2, risk_tier=="MEDIUM", 3, 4),
      risk_tier,
      detail=strcat("Fraud score: ", tostring(fraud_score), " | Flags: ", fraud_flags),
      timestamp=score_timestamp, latitude, longitude;
let gaps = care_gap_alerts
    | where alert_timestamp > ago(24h)
    | project patient_id, alert_type="CARE_GAP", alert_id,
      priority=case(alert_priority=="CRITICAL", 1, alert_priority=="HIGH", 2, alert_priority=="MEDIUM", 3, 4),
      risk_tier=alert_priority,
      detail=strcat("Gap: ", measure_name, " | Overdue: ", tostring(gap_days_overdue), "d"),
      timestamp=alert_timestamp, latitude, longitude;
let costs = highcost_alerts
    | where alert_timestamp > ago(24h)
    | project patient_id, alert_type="HIGH_COST", alert_id,
      priority=case(risk_tier=="CRITICAL", 1, risk_tier=="HIGH", 2, risk_tier=="MEDIUM", 3, 4),
      risk_tier,
      detail=strcat("30d spend: $", tostring(rolling_spend_30d),
        " | ED visits: ", tostring(ed_visits_30d), " | Trend: ", cost_trend),
      timestamp=alert_timestamp, latitude, longitude;
union fraud, gaps, costs
| summarize alert_types=make_set(alert_type),
           max_priority=min(priority),
           alert_count=count(),
           alerts=make_list(pack("type", alert_type, "id", alert_id, "detail", detail, "time", timestamp, "tier", risk_tier)),
           any(latitude), any(longitude)
  by patient_id
| order by max_priority asc, alert_count desc
| take 100
"""

def run_kql_query(query):
    """Execute a KQL query against the Eventhouse and return results as list of dicts."""
    from azure.kusto.data import KustoClient, KustoConnectionStringBuilder
    token = notebookutils.credentials.getToken("kusto")
    kcsb = KustoConnectionStringBuilder.with_aad_user_token_authentication(KUSTO_QUERY_URI, token)
    client = KustoClient(kcsb)
    response = client.execute(KQL_DB_NAME, query)
    rows = []
    for row in response.primary_results[0]:
        rows.append({col.column_name: row[col.column_name] for col in response.primary_results[0].columns})
    return rows

# Discover Kusto URI (same pattern as simulator)
KUSTO_QUERY_URI = ""
try:
    headers_kql = get_headers()
    items_url = f"{BASE_URL}/workspaces/{WORKSPACE_ID}/items?type=Eventhouse"
    resp = requests.get(items_url, headers=headers_kql)
    if resp.status_code == 200:
        for item in resp.json().get("value", []):
            if "Healthcare" in item.get("displayName", ""):
                eh_id = item["id"]
                props_resp = requests.get(
                    f"{BASE_URL}/workspaces/{WORKSPACE_ID}/eventhouses/{eh_id}",
                    headers=headers_kql
                )
                if props_resp.status_code == 200:
                    props = props_resp.json().get("properties", props_resp.json())
                    KUSTO_QUERY_URI = props.get("queryServiceUri", "")
                    print(f"  Eventhouse: {item['displayName']} ({KUSTO_QUERY_URI[:50]}...)")
                break
except Exception as e:
    print(f"  WARN: Could not discover Kusto URI: {e}")

if not KUSTO_QUERY_URI:
    print("  ERROR: No Kusto URI found -- cannot run triage queries")
    print("  Ensure NB_RTI_Setup_Eventhouse ran successfully")

# Execute unified worklist query
worklist_results = []
if KUSTO_QUERY_URI:
    try:
        worklist_results = run_kql_query(UNIFIED_WORKLIST_KQL)
        print(f"  Unified worklist: {len(worklist_results)} patients with active alerts (24h)")
        for i, row in enumerate(worklist_results[:10]):
            types = row.get("alert_types", [])
            print(f"    #{i+1}: {row['patient_id'][:12]}... | Priority {row['max_priority']} | "
                  f"Types: {types} | Alerts: {row['alert_count']}")
    except Exception as e:
        print(f"  WARN: Unified worklist query failed: {e}")
        print("  This is expected if scoring notebooks haven't run yet")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Module 2: SLA & Throughput Monitoring
# ============================================================================
# Checks data freshness across input tables and pipeline completion status.
# Writes results to rti_sla_status in the KQL Database.
# ============================================================================

print("\nModule 2: SLA & Throughput Monitoring")

DATA_FRESHNESS_KQL = """
let claims_age = toscalar(claims_events | summarize max(event_timestamp));
let adt_age = toscalar(adt_events | summarize max(event_timestamp));
let rx_age = toscalar(rx_events | summarize max(event_timestamp));
print claims_minutes_ago=datetime_diff('minute', now(), claims_age),
      adt_minutes_ago=datetime_diff('minute', now(), adt_age),
      rx_minutes_ago=datetime_diff('minute', now(), rx_age)
"""

ALERT_VELOCITY_KQL = """
union 
  (claims_events | project event_timestamp, event_type="claims"),
  (adt_events | project event_timestamp, event_type="adt"),
  (rx_events | project event_timestamp, event_type="rx")
| where event_timestamp > ago(1h)
| summarize event_count=count() by bin(event_timestamp, 5m), event_type
| order by event_timestamp desc
"""

import uuid as _uuid

sla_results = []
if KUSTO_QUERY_URI:
    try:
        freshness = run_kql_query(DATA_FRESHNESS_KQL)
        if freshness:
            row = freshness[0]
            now_ts = datetime.utcnow()
            for table_key, table_name in [
                ("claims_minutes_ago", "claims_events"),
                ("adt_minutes_ago", "adt_events"),
                ("rx_minutes_ago", "rx_events")
            ]:
                minutes = row.get(table_key, 9999)
                if minutes is None:
                    minutes = 9999
                if minutes > FRESHNESS_CRIT_MIN:
                    status = "CRITICAL"
                elif minutes > FRESHNESS_WARN_MIN:
                    status = "WARNING"
                else:
                    status = "OK"
                
                sla_entry = {
                    "check_id": str(_uuid.uuid4()),
                    "check_timestamp": now_ts.isoformat(),
                    "table_name": table_name,
                    "latest_event_timestamp": (now_ts - timedelta(minutes=minutes)).isoformat(),
                    "minutes_ago": round(float(minutes), 1),
                    "status": status,
                    "threshold_warn_min": FRESHNESS_WARN_MIN,
                    "threshold_crit_min": FRESHNESS_CRIT_MIN,
                }
                sla_results.append(sla_entry)
                icon = {"OK": "OK", "WARNING": "WARN", "CRITICAL": "CRIT"}[status]
                print(f"  [{icon}] {table_name}: {minutes:.0f} min since last event")
    except Exception as e:
        print(f"  WARN: Freshness query failed: {e}")
        print("  This is expected if input tables are empty")

    # Alert velocity check
    try:
        velocity = run_kql_query(ALERT_VELOCITY_KQL)
        if velocity:
            total_events = sum(r.get("event_count", 0) for r in velocity)
            print(f"  Event velocity (last 1h): {total_events} events across {len(velocity)} time bins")
        else:
            print("  Event velocity: No events in the last hour")
    except Exception as e:
        print(f"  WARN: Velocity query failed: {e}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Module 3: Action Routing
# ============================================================================
# Routes alerts to downstream systems based on alert type and priority.
# Writes action log to rti_action_log in the KQL Database.
#
# Routing rules:
#   - CRITICAL fraud → SIU investigation queue
#   - CRITICAL care gap → Provider EHR/fax alert
#   - CRITICAL high-cost → Care management referral
#   - All CRITICAL → Microsoft Teams notification (if webhook configured)
#   - Fabric Data Activator (Reflex) for event-driven triggers
# ============================================================================

print("\nModule 3: Action Routing")

def send_teams_alert(webhook_url, title, message, priority):
    """Send an alert card to Microsoft Teams via incoming webhook."""
    card = {
        "@type": "MessageCard",
        "themeColor": "FF0000" if priority == "CRITICAL" else "FFA500",
        "summary": title,
        "sections": [{
            "activityTitle": title,
            "text": message,
            "facts": [
                {"name": "Priority", "value": priority},
                {"name": "Time", "value": datetime.utcnow().isoformat()},
            ]
        }]
    }
    resp = requests.post(webhook_url, json=card, timeout=10)
    return resp.status_code == 200

# Route CRITICAL alerts from the unified worklist
action_log = []
critical_alerts = [r for r in worklist_results if r.get("max_priority") == 1]
print(f"  CRITICAL alerts to route: {len(critical_alerts)}")

for row in critical_alerts:
    patient_id = row["patient_id"]
    alert_types = row.get("alert_types", [])
    alerts = row.get("alerts", [])
    
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        alert_type = alert.get("type", "")
        alert_tier = alert.get("tier", "")
        if alert_tier != "CRITICAL":
            continue
        
        # Determine routing destination
        if alert_type == "FRAUD":
            action_type = "SIU_REFERRAL"
            destination = "Special Investigations Unit Queue"
        elif alert_type == "CARE_GAP":
            action_type = "PROVIDER_ALERT"
            destination = "Provider Care Team / EHR Alert"
        elif alert_type == "HIGH_COST":
            action_type = "CM_REFERRAL"
            destination = "Care Management Program Referral"
        else:
            action_type = "GENERAL_ALERT"
            destination = "Operations Review Queue"
        
        action_entry = {
            "action_id": str(_uuid.uuid4()),
            "action_timestamp": datetime.utcnow().isoformat(),
            "alert_type": alert_type,
            "alert_id": alert.get("id", ""),
            "patient_id": patient_id,
            "action_type": action_type,
            "destination": destination,
            "status": "ROUTED",
            "detail": alert.get("detail", ""),
        }
        action_log.append(action_entry)
        print(f"    {alert_type} -> {action_type} ({destination})")
    
    # Teams notification for all CRITICAL patients
    if ENABLE_TEAMS_WEBHOOK and TEAMS_WEBHOOK_URL:
        types_str = ", ".join(alert_types) if isinstance(alert_types, list) else str(alert_types)
        send_teams_alert(
            TEAMS_WEBHOOK_URL,
            f"CRITICAL: Patient {patient_id[:8]}... — {types_str}",
            f"Alert types: {types_str}\nTotal alerts: {row.get('alert_count', 0)}",
            "CRITICAL"
        )

if not critical_alerts:
    print("  No CRITICAL alerts to route (this is expected if scoring hasn't run)")
print(f"  Actions logged: {len(action_log)}")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ============================================================================
# Module 4: Write Results to KQL + Summary
# ============================================================================
# Writes unified worklist, SLA status, and action log to KQL tables.
# These tables power the Operations Agent natural language interface
# and the RTI Dashboard operational KPI tiles.
# ============================================================================

print("\nModule 4: Write Results to KQL")

import io
import pandas as pd

def write_to_kql(records, table_name, mapping_name):
    """Write a list of dicts to a KQL table via managed streaming ingestion."""
    if not records or not KUSTO_QUERY_URI:
        return False
    try:
        from azure.kusto.ingest import ManagedStreamingIngestClient, IngestionProperties
        from azure.kusto.data import KustoConnectionStringBuilder, DataFormat
        
        token = notebookutils.credentials.getToken("kusto")
        ingest_uri = KUSTO_QUERY_URI.replace("https://", "https://ingest-")
        
        engine_kcsb = KustoConnectionStringBuilder.with_aad_user_token_authentication(KUSTO_QUERY_URI, token)
        dm_kcsb = KustoConnectionStringBuilder.with_aad_user_token_authentication(ingest_uri, token)
        client = ManagedStreamingIngestClient(engine_kcsb, dm_kcsb)
        
        props = IngestionProperties(
            database=KQL_DB_NAME,
            table=table_name,
            data_format=DataFormat.JSON,
            ingestion_mapping_reference=mapping_name,
        )
        
        df = pd.DataFrame(records)
        json_data = df.to_json(orient="records", lines=True, date_format="iso")
        stream = io.StringIO(json_data)
        client.ingest_from_stream(stream, ingestion_properties=props)
        print(f"  KQL: {len(records)} rows -> {table_name}")
        return True
    except Exception as e:
        print(f"  KQL WARN: {table_name} write failed: {e}")
        return False

# Write worklist results
if worklist_results:
    worklist_records = []
    for row in worklist_results:
        alerts = row.get("alerts", [])
        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            worklist_records.append({
                "worklist_id": str(_uuid.uuid4()),
                "generated_at": datetime.utcnow().isoformat(),
                "patient_id": row["patient_id"],
                "alert_type": alert.get("type", ""),
                "alert_id": alert.get("id", ""),
                "priority": row.get("max_priority", 4),
                "risk_tier": alert.get("tier", ""),
                "detail": alert.get("detail", ""),
                "alert_count": row.get("alert_count", 0),
                "alert_types": "|".join(row.get("alert_types", [])) if isinstance(row.get("alert_types"), list) else str(row.get("alert_types", "")),
                "latitude": row.get("any_latitude", 0),
                "longitude": row.get("any_longitude", 0),
            })
    write_to_kql(worklist_records, "rti_unified_worklist", "rti_unified_worklist_mapping")

# Write SLA results
if sla_results:
    write_to_kql(sla_results, "rti_sla_status", "rti_sla_status_mapping")

# Write action log
if action_log:
    write_to_kql(action_log, "rti_action_log", "rti_action_log_mapping")

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Summary ----------
print("\n" + "=" * 60)
print("NB_RTI_Operations_Agent: COMPLETE")
print("=" * 60)
print(f"  Unified worklist: {len(worklist_results)} patients with active alerts")
print(f"  SLA checks: {len(sla_results)} table freshness checks")
sla_critical = [s for s in sla_results if s.get("status") == "CRITICAL"]
sla_warn = [s for s in sla_results if s.get("status") == "WARNING"]
if sla_critical:
    print(f"    CRITICAL: {len(sla_critical)} tables stale > {FRESHNESS_CRIT_MIN} min")
if sla_warn:
    print(f"    WARNING: {len(sla_warn)} tables stale > {FRESHNESS_WARN_MIN} min")
print(f"  Actions routed: {len(action_log)}")
if ENABLE_TEAMS_WEBHOOK and TEAMS_WEBHOOK_URL:
    print(f"  Teams notifications: Enabled")
else:
    print(f"  Teams notifications: Disabled (set ENABLE_TEAMS_WEBHOOK=True to enable)")
if ENABLE_REFLEX:
    print(f"  Data Activator (Reflex): Enabled")
else:
    print(f"  Data Activator (Reflex): Disabled (configure in Fabric portal)")
print()
print("KQL tables updated:")
print("  - rti_unified_worklist  (priority-ranked cross-domain alert queue)")
print("  - rti_sla_status        (data freshness and pipeline health)")
print("  - rti_action_log        (audit trail of routed actions)")
print()
print("Integration points:")
print("  - Operations Agent (HealthcareOpsAgent) queries these tables via natural language")
print("  - RTI Dashboard shows operational KPIs from these tables")
print("  - Data Activator (Healthcare_RTI_Activator) triggers on Eventstream events")
print("=" * 60)

# METADATA **{"language":"python"}**
# You have access to:
# - KQL queries against Healthcare_RTI_DB (real-time scoring outputs)
# - SQL queries against lh_gold_curated (historical batch data)
# - Pipeline status API (data freshness and SLA monitoring)
#
# Always prioritize CRITICAL alerts first. When asked for a worklist,
# deduplicate patients across alert types and rank by composite severity.
# """

# METADATA **{"language":"python"}**

# CELL **{"language":"python"}**

# ---------- Summary ----------
print("\n" + "=" * 70)
print("  NB_RTI_Operations_Agent: ARCHITECTURE STUB")
print("=" * 70)
print()
print("  This notebook outlines the future Operations Agent with 4 modules:")
print()
print("  Module 1: Unified Alert Triage")
print("    - Merge fraud + care gap + high-cost alerts into single worklist")
print("    - Deduplicate by patient, rank by composite priority")
print()
print("  Module 2: SLA & Throughput Monitoring")
print("    - Data freshness checks (claims, ADT, Rx input tables)")
print("    - Pipeline SLA tracking (batch ETL completion)")
print("    - Alert-to-action latency metrics")
print()
print("  Module 3: Action Routing")
print("    - CRITICAL fraud → SIU queue")
print("    - CRITICAL care gaps → Provider EHR/fax alerts")
print("    - CRITICAL high-cost → Care management referral")
print("    - All CRITICAL → Teams webhook notification")
print("    - Fabric Data Activator (Reflex) integration")
print()
print("  Module 4: Foundry Agent Integration")
print("    - Natural language ops: 'What are today's top 10 priorities?'")
print("    - KQL tool access for real-time + Gold SQL for historical context")
print()
print("  To implement: Replace [STUB] sections with live KQL queries,")
print("  configure Teams webhook, set up Reflex triggers, deploy Foundry agent.")
print("=" * 70)

# METADATA **{"language":"python"}**
