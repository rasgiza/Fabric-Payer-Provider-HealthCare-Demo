"""
Generate healthcare-architecture.drawio following Microsoft Architecture Center
and cold-chain ontology design patterns.

References:
- https://learn.microsoft.com/en-us/azure/architecture/example-scenario/analytics/enterprise-bi-microsoft-fabric
- https://learn.microsoft.com/en-us/azure/architecture/example-scenario/dataplate2e/data-platform-end-to-end
- https://learn.microsoft.com/en-us/azure/architecture/industries/automotive/automotive-telemetry-analytics
- Cold-chain ontology architecture diagram (design template)
"""

import xml.etree.ElementTree as ET
from pathlib import Path

# ── Colour palette (Microsoft / Fluent) ──────────────────────────
BLUE    = "#0078D4"
GREEN   = "#107C10"
ORANGE  = "#E8700A"
RED     = "#D13438"
PURPLE  = "#5C2D91"
TEAL    = "#0D9488"
GOLD    = "#B8860B"
YELLOW  = "#F2C811"

BG_LIGHT   = "#F2F2F2"
BORDER     = "#D2D0CE"
TEXT_PRI   = "#323130"
TEXT_SEC   = "#605E5C"
TEXT_TER   = "#A19F9D"
WHITE      = "#FFFFFF"
ARROW_CLR  = "#505050"

# ── page dimensions ──────────────────────────────────────────────
PW, PH = 1700, 1020
MARGIN = 20


# ── helper: unique id counter ────────────────────────────────────
_id_counter = [2]  # 0 and 1 reserved for root cells

def _nid():
    _id_counter[0] += 1
    return str(_id_counter[0])


# ── style builders ───────────────────────────────────────────────
def _section_style():
    return (
        "rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={BG_LIGHT};strokeColor={BORDER};"
        "strokeWidth=1;dashed=1;dashPattern=6 3;arcSize=2;"
    )

def _card_style():
    return (
        "rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={WHITE};strokeColor={BORDER};strokeWidth=1;"
    )

def _badge_style(color):
    return (
        "rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={color};strokeColor=none;"
        f"fontColor={WHITE};fontStyle=1;fontSize=11;fontFamily=Segoe UI;"
    )

def _title_style(size=14, bold=True, color=TEXT_PRI):
    return (
        "text;html=1;strokeColor=none;fillColor=none;"
        f"align=left;verticalAlign=middle;fontSize={size};"
        f"fontStyle={'1' if bold else '0'};fontColor={color};"
        "fontFamily=Segoe UI;"
    )

def _center_title_style(size=14, bold=True, color=TEXT_PRI):
    return (
        "text;html=1;strokeColor=none;fillColor=none;"
        f"align=center;verticalAlign=middle;fontSize={size};"
        f"fontStyle={'1' if bold else '0'};fontColor={color};"
        "fontFamily=Segoe UI;"
    )

def _entity_text_style(size=9, color=TEXT_PRI):
    return (
        "text;html=1;strokeColor=none;fillColor=none;"
        f"align=left;verticalAlign=top;fontSize={size};"
        f"fontColor={color};fontFamily=Segoe UI;spacingTop=2;"
    )

def _box_style(color, rounding=1):
    return (
        f"rounded={rounding};whiteSpace=wrap;html=1;"
        f"fillColor={color};strokeColor={BORDER};strokeWidth=1;"
        f"fontColor={WHITE};fontStyle=1;fontSize=10;fontFamily=Segoe UI;"
    )

def _arrow_style(dashed=False, label_size=8):
    dash = "dashed=1;dashPattern=4 3;" if dashed else ""
    return (
        f"endArrow=classic;html=1;strokeWidth=1;strokeColor={ARROW_CLR};"
        f"{dash}fontSize={label_size};fontColor={ARROW_CLR};"
        "edgeStyle=orthogonalEdgeStyle;"
    )

def _curved_arrow_style(dashed=True, label_size=9):
    dash = "dashed=1;dashPattern=4 3;" if dashed else ""
    return (
        f"endArrow=classic;html=1;strokeWidth=1;strokeColor={ARROW_CLR};"
        f"{dash}curved=1;fontSize={label_size};fontColor={ARROW_CLR};"
    )


# ── cell builders ────────────────────────────────────────────────
def _rect(parent, cid, value, style, x, y, w, h):
    cell = ET.SubElement(parent, "mxCell",
                         id=cid, value=value, style=style,
                         vertex="1", parent="1")
    ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y),
                  width=str(w), height=str(h)).set("as", "geometry")
    return cid

def _edge(parent, cid, value, style, sx, sy, tx, ty, pts=None):
    cell = ET.SubElement(parent, "mxCell",
                         id=cid, value=value, style=style,
                         edge="1", parent="1")
    geo = ET.SubElement(cell, "mxGeometry")
    geo.set("relative", "1")
    geo.set("as", "geometry")
    ET.SubElement(geo, "mxPoint", x=str(sx), y=str(sy)).set("as", "sourcePoint")
    ET.SubElement(geo, "mxPoint", x=str(tx), y=str(ty)).set("as", "targetPoint")
    if pts:
        arr = ET.SubElement(geo, "Array")
        arr.set("as", "points")
        for px, py in pts:
            ET.SubElement(arr, "mxPoint", x=str(px), y=str(py))
    return cid


# ── domain definitions ───────────────────────────────────────────
DOMAINS = [
    {
        "name": "People",
        "badge": "P",
        "color": BLUE,
        "entities": [
            ("Patient", "dim_patient", "patient_key, name, dob, gender, zip"),
            ("Provider", "dim_provider", "provider_key, name, specialty, NPI"),
        ],
        "rels": ["involves → Encounter", "livesIn → Community"],
    },
    {
        "name": "Clinical",
        "badge": "C",
        "color": GREEN,
        "entities": [
            ("Encounter", "fact_encounter", "encounter_key, type, admit/discharge"),
            ("Vitals", "fact_vitals", "BP, HR, temp, resp_rate, BMI, O₂"),
        ],
        "rels": ["treatedBy → Provider", "billsFor → Financial"],
    },
    {
        "name": "Financial",
        "badge": "F",
        "color": ORANGE,
        "entities": [
            ("Claim", "fact_claim", "claim_key, amount, status, payer"),
            ("Prescription", "fact_prescription", "Rx_key, cost, fills, NDC"),
        ],
        "rels": ["covers → Patient", "ClaimHasPayer → Payer"],
    },
    {
        "name": "Diagnostic",
        "badge": "D",
        "color": RED,
        "entities": [
            ("PatientDiagnosis", "fact_diagnosis", "diagnosis_key, ICD, severity"),
            ("Diagnosis", "dim_diagnosis", "ICD code, description, category"),
        ],
        "rels": ["affects → Patient", "occursIn → Encounter"],
    },
    {
        "name": "Pharmacy",
        "badge": "R",
        "color": PURPLE,
        "entities": [
            ("Medication", "dim_medication", "med_key, class, therapeutic_area"),
            ("MedAdherence", "agg_med_adherence", "PDC score, gap_days, category"),
        ],
        "rels": ["dispenses → Medication", "adherenceFor → Patient"],
    },
    {
        "name": "Community",
        "badge": "S",
        "color": TEAL,
        "entities": [
            ("Payer", "dim_payer", "payer_key, name, type"),
            ("CommunityHealth", "dim_sdoh", "zip, poverty, food_desert, SVI"),
        ],
        "rels": ["livesIn ← Patient", "ClaimHasPayer ← Claim"],
    },
]


# ══════════════════════════════════════════════════════════════════
def build_diagram():
    """Build the complete mxfile XML."""

    # root
    mxfile = ET.Element("mxfile", host="Copilot")
    diagram = ET.SubElement(mxfile, "diagram",
                            id="healthcare-arch", name="Healthcare Architecture")
    model = ET.SubElement(diagram, "mxGraphModel",
                          dx=str(PW), dy=str(PH),
                          grid="1", gridSize="2",
                          guides="1", tooltips="1", connect="1",
                          arrows="1", fold="1",
                          page="1", pageScale="1",
                          pageWidth=str(PW), pageHeight=str(PH),
                          math="0", shadow="0")
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    # ── TITLE ────────────────────────────────────────────────
    _rect(root, _nid(),
          "Payer-Provider Healthcare Analytics Demo",
          _center_title_style(16, True, TEXT_PRI),
          MARGIN, 8, PW - 2*MARGIN, 22)
    _rect(root, _nid(),
          "Microsoft Fabric  •  Ontology Graph  •  Data Agents  •  Real-Time Intelligence  •  Medallion Lakehouse",
          _center_title_style(10, False, TEXT_SEC),
          MARGIN, 30, PW - 2*MARGIN, 16)

    # ── SECTION 1: DOMAIN MODEL ──────────────────────────────
    SEC1_Y, SEC1_H = 56, 310
    _rect(root, _nid(), "",
          _section_style(),
          MARGIN, SEC1_Y, PW - 2*MARGIN, SEC1_H)
    _rect(root, _nid(),
          "Healthcare Domain Model — 12 Entity Types, 19 Relationships (6 Cross-Domain)",
          _title_style(12, True, TEXT_PRI),
          MARGIN + 16, SEC1_Y + 4, 600, 18)

    # domain cards
    CARD_W, CARD_H = 240, 260
    GAP = 12
    total_w = 6 * CARD_W + 5 * GAP
    start_x = MARGIN + (PW - 2*MARGIN - total_w) // 2
    card_y = SEC1_Y + 30

    card_centers = []  # for cross-domain arcs later

    for i, dom in enumerate(DOMAINS):
        cx = start_x + i * (CARD_W + GAP)
        card_centers.append(cx + CARD_W // 2)

        # card background
        _rect(root, _nid(), "", _card_style(),
              cx, card_y, CARD_W, CARD_H)

        # badge
        _rect(root, _nid(), dom["badge"],
              _badge_style(dom["color"]),
              cx + 8, card_y + 8, 22, 22)

        # domain name
        _rect(root, _nid(), dom["name"],
              _title_style(11, True, TEXT_PRI),
              cx + 36, card_y + 8, CARD_W - 44, 20)

        # entities
        ey = card_y + 38
        for ename, table, fields in dom["entities"]:
            txt = f"<b>{ename}</b>\n<i>{table}</i>\n{fields}"
            _rect(root, _nid(), txt,
                  _entity_text_style(8, TEXT_PRI),
                  cx + 8, ey, CARD_W - 16, 54)
            ey += 58

        # relationships (italic at bottom)
        ey += 4
        rel_text = "\n".join(dom["rels"])
        _rect(root, _nid(), f"<i>{rel_text}</i>",
              _entity_text_style(8, TEXT_SEC),
              cx + 8, ey, CARD_W - 16, 40)

    # cross-domain reasoning arc
    arc_y = card_y + CARD_H + 8
    _edge(root, _nid(),
          "Cross-Domain Reasoning  (Patient → Encounter → Claim → Payer → SDOH)",
          _curved_arrow_style(True, 9),
          card_centers[0], arc_y,
          card_centers[5], arc_y,
          pts=[(card_centers[2], arc_y - 14), (card_centers[3], arc_y - 14)])

    # ── SECTION 2: MICROSOFT FABRIC PLATFORM ─────────────────
    SEC2_Y, SEC2_H = SEC1_Y + SEC1_H + 14, 360
    _rect(root, _nid(), "",
          _section_style(),
          MARGIN, SEC2_Y, PW - 2*MARGIN, SEC2_H)
    _rect(root, _nid(),
          "Microsoft Fabric — Healthcare Analytics Workspace",
          _title_style(12, True, TEXT_PRI),
          MARGIN + 16, SEC2_Y + 4, 500, 18)

    # --- Data Sources column ---
    DS_X = MARGIN + 24
    DS_Y = SEC2_Y + 32
    DS_W = 150

    # EHR System box
    _rect(root, _nid(), "EHR System",
          _box_style(BLUE), DS_X, DS_Y, DS_W, 28)
    # database items
    dbs = ["Reporting DB", "Oracle DB", "Azure SQL", "SQL Server"]
    for j, db in enumerate(dbs):
        _rect(root, _nid(), db,
              (f"shape=cylinder3;whiteSpace=wrap;html=1;"
               f"fillColor={WHITE};strokeColor={BORDER};strokeWidth=1;"
               f"fontSize=8;fontColor={TEXT_PRI};fontFamily=Segoe UI;"
               "size=6;"),
              DS_X + 4 + j * 36, DS_Y + 34, 32, 36)

    # Streaming Sources
    _rect(root, _nid(), "Streaming Sources",
          _box_style(ORANGE), DS_X, DS_Y + 82, DS_W, 28)
    stream_items = ["HL7/FHIR", "IoT Vitals", "ADT Events"]
    for j, si in enumerate(stream_items):
        _rect(root, _nid(), si,
              _entity_text_style(7, TEXT_SEC),
              DS_X + 4, DS_Y + 114 + j * 14, DS_W - 8, 14)

    # Azure Event Hub
    _rect(root, _nid(), "Azure Event Hub",
          _box_style("#0078D4"), DS_X, DS_Y + 170, DS_W, 28)

    # --- Ingest column ---
    ING_X = DS_X + DS_W + 30
    ING_W = 120

    # Data Factory Pipeline
    _rect(root, _nid(), "Data Factory\nPipeline",
          _box_style(BLUE),
          ING_X, DS_Y + 14, ING_W, 44)

    # Eventstream
    _rect(root, _nid(), "Eventstream",
          _box_style(ORANGE),
          ING_X, DS_Y + 170, ING_W, 28)

    # arrows: sources → ingest
    _edge(root, _nid(), "", _arrow_style(True),
          DS_X + DS_W, DS_Y + 36,
          ING_X, DS_Y + 36)
    _edge(root, _nid(), "", _arrow_style(False),
          DS_X + DS_W, DS_Y + 184,
          ING_X, DS_Y + 184)

    # --- Medallion Store (Bronze → Silver → Gold) ---
    MED_X = ING_X + ING_W + 30
    MED_W = 110
    MED_GAP = 14

    layers = [
        ("Bronze\nLakehouse", "#CD7F32", "(raw ingest)"),
        ("Silver\nLakehouse", "#C0C0C0", "(clean + validate)"),
        ("Gold\nLakehouse", "#FFD700", "(star schema)"),
    ]

    for j, (lname, lcolor, lsub) in enumerate(layers):
        lx = MED_X + j * (MED_W + MED_GAP)
        _rect(root, _nid(), lname,
              _box_style(lcolor),
              lx, DS_Y + 8, MED_W, 44)
        _rect(root, _nid(), lsub,
              _center_title_style(7, False, TEXT_SEC),
              lx, DS_Y + 54, MED_W, 12)
        if j > 0:
            prev_x = MED_X + (j-1) * (MED_W + MED_GAP) + MED_W
            _edge(root, _nid(), "", _arrow_style(),
                  prev_x, DS_Y + 30,
                  lx, DS_Y + 30)

    # arrow: pipeline → bronze
    _edge(root, _nid(), "batch", _arrow_style(True, 8),
          ING_X + ING_W, DS_Y + 36,
          MED_X, DS_Y + 30)

    # Eventhouse (for streaming path)
    EH_X = MED_X
    EH_Y = DS_Y + 150
    _rect(root, _nid(), "Eventhouse",
          _box_style(GOLD),
          EH_X, EH_Y, MED_W, 32)

    # KQL Database
    KQL_X = EH_X + MED_W + MED_GAP
    _rect(root, _nid(), "KQL Database",
          _box_style(GOLD),
          KQL_X, EH_Y, MED_W, 32)

    # arrow: eventhouse → KQL
    _edge(root, _nid(), "", _arrow_style(),
          EH_X + MED_W, EH_Y + 16,
          KQL_X, EH_Y + 16)

    # arrow: eventstream → eventhouse
    _edge(root, _nid(), "stream", _arrow_style(False, 8),
          ING_X + ING_W, DS_Y + 184,
          EH_X, EH_Y + 16)

    # OneLake bar (spanning medallion area)
    OL_X = MED_X - 4
    OL_W = 3 * MED_W + 2 * MED_GAP + 8
    OL_Y = DS_Y + 76
    _rect(root, _nid(), "OneLake (Unified Data Lake)",
          (f"rounded=1;whiteSpace=wrap;html=1;"
           f"fillColor=#E6F0FA;strokeColor={BLUE};strokeWidth=1;"
           f"fontSize=9;fontColor={BLUE};fontStyle=2;fontFamily=Segoe UI;"
           "dashed=1;dashPattern=4 3;"),
          OL_X, OL_Y, OL_W, 18)

    # --- Serve column ---
    SRV_X = MED_X + 3 * (MED_W + MED_GAP) + 10
    SRV_W = 120

    # Semantic Model
    _rect(root, _nid(), "Semantic\nModel",
          _box_style(YELLOW),
          SRV_X, DS_Y + 8, SRV_W, 44)

    # Power BI
    PBI_X = SRV_X + SRV_W + 14
    _rect(root, _nid(), "Power BI\nDashboards",
          _box_style(YELLOW),
          PBI_X, DS_Y + 8, SRV_W, 44)

    # arrow: gold → semantic model
    gold_x = MED_X + 2 * (MED_W + MED_GAP) + MED_W
    _edge(root, _nid(), "", _arrow_style(),
          gold_x, DS_Y + 30,
          SRV_X, DS_Y + 30)

    # arrow: semantic model → power bi
    _edge(root, _nid(), "", _arrow_style(),
          SRV_X + SRV_W, DS_Y + 30,
          PBI_X, DS_Y + 30)

    # RTI Dashboard
    _rect(root, _nid(), "RTI Dashboard",
          _box_style(GOLD),
          SRV_X, EH_Y, SRV_W, 32)

    # arrow: KQL → RTI Dashboard
    _edge(root, _nid(), "", _arrow_style(),
          KQL_X + MED_W, EH_Y + 16,
          SRV_X, EH_Y + 16)

    # Data Activator (fraud alerts from Eventstream)
    ACT_X = PBI_X
    _rect(root, _nid(), "Data Activator\n(Fraud ≥ 0.7)",
          _box_style(RED),
          ACT_X, EH_Y, SRV_W, 32)

    # arrow: Eventstream → Data Activator (not KQL — monitors stream directly)
    _edge(root, _nid(), "fraud trigger", _arrow_style(True, 7),
          ING_X + ING_W, DS_Y + 186,
          ACT_X, EH_Y + 16,
          pts=[(ING_X + ING_W + 15, DS_Y + 186),
               (ING_X + ING_W + 15, EH_Y + 16)])

    # --- AI / Intelligence layer ---
    AI_Y = DS_Y + 210
    AI_X = MED_X

    # Ontology Graph
    _rect(root, _nid(), "Ontology Graph\n(12 Entities, 19 Rels)",
          _box_style(PURPLE),
          AI_X, AI_Y, MED_W + 20, 44)

    # arrow: Gold → Ontology
    _edge(root, _nid(), "table bindings", _arrow_style(True, 7),
          MED_X + 2 * (MED_W + MED_GAP) + MED_W // 2, DS_Y + 52,
          AI_X + (MED_W + 20) // 2, AI_Y)

    # HLS Data Agent
    HLS_X = AI_X + MED_W + 20 + MED_GAP + 10
    _rect(root, _nid(), "Healthcare\nHLS Agent",
          _box_style(BLUE),
          HLS_X, AI_Y, SRV_W, 44)

    # arrow: Semantic Model → HLS Agent
    _edge(root, _nid(), "SQL queries", _arrow_style(True, 7),
          SRV_X + SRV_W // 2, DS_Y + 52,
          HLS_X + SRV_W // 2, AI_Y)

    # Graph Data Agent
    GDA_X = HLS_X + SRV_W + 14
    _rect(root, _nid(), "Healthcare\nGraph Agent",
          _box_style(PURPLE),
          GDA_X, AI_Y, SRV_W, 44)

    # arrow: Ontology → Graph Agent
    _edge(root, _nid(), "GQL queries", _arrow_style(True, 7),
          AI_X + MED_W + 20, AI_Y + 22,
          GDA_X, AI_Y + 22)

    # Operations Agent (real-time data via KQL)
    OPS_X = GDA_X + SRV_W + 14
    _rect(root, _nid(), "Operations\nAgent",
          _box_style(GOLD),
          OPS_X, AI_Y, SRV_W, 44)

    # arrow: KQL Database → Operations Agent
    _edge(root, _nid(), "KQL queries", _arrow_style(True, 7),
          KQL_X + MED_W // 2, EH_Y + 32,
          OPS_X + SRV_W // 2, AI_Y)

    # --- Actions column (right edge) ---
    ACT2_X = OPS_X + SRV_W + 14
    ACT2_W = 100

    # Power Automate (hub — receives from both Ops Agent and Activator)
    PA_Y = EH_Y - 6
    _rect(root, _nid(), "Power\nAutomate",
          _box_style(BLUE),
          ACT2_X, PA_Y, ACT2_W, 36)

    # Email
    EMAIL_Y = PA_Y + 48
    _rect(root, _nid(), "Email\n(SIU Alert)",
          _box_style("#0078D4"),
          ACT2_X, EMAIL_Y, ACT2_W, 32)

    # Teams
    TEAMS_Y = EMAIL_Y + 42
    _rect(root, _nid(), "Teams",
          _box_style(PURPLE),
          ACT2_X, TEAMS_Y, ACT2_W, 28)

    # arrow: Operations Agent → Power Automate
    _edge(root, _nid(), "", _arrow_style(),
          OPS_X + SRV_W, AI_Y + 22,
          ACT2_X, PA_Y + 18)

    # arrow: Data Activator → Power Automate
    _edge(root, _nid(), "fraud alert", _arrow_style(False, 7),
          ACT_X + SRV_W, EH_Y + 16,
          ACT2_X, PA_Y + 18)

    # arrow: Power Automate → Email
    _edge(root, _nid(), "", _arrow_style(),
          ACT2_X + ACT2_W // 2, PA_Y + 36,
          ACT2_X + ACT2_W // 2, EMAIL_Y)

    # arrow: Power Automate → Teams
    _edge(root, _nid(), "", _arrow_style(),
          ACT2_X + ACT2_W // 2, PA_Y + 36,
          ACT2_X + ACT2_W // 2, TEAMS_Y)

    # ── SAMPLE TRAVERSAL ─────────────────────────────────────
    TRAV_Y = SEC2_Y + SEC2_H + 14
    TRAV_H = 80
    _rect(root, _nid(), "",
          _section_style(),
          MARGIN, TRAV_Y, PW - 2*MARGIN, TRAV_H)
    _rect(root, _nid(),
          "Sample Graph Traversal",
          _title_style(11, True, TEXT_PRI),
          MARGIN + 16, TRAV_Y + 4, 200, 16)
    _rect(root, _nid(),
          "Patient P-1001 → Encounter E-2045 → Claim C-3021 → Payer (Medicare) → Diagnosis (I10 Hypertension) → Medication (Lisinopril) → Adherence (PDC 0.85)",
          _title_style(9, False, TEXT_SEC),
          MARGIN + 220, TRAV_Y + 4, PW - 2*MARGIN - 240, 16)

    # traversal steps
    steps = [
        ("Patient P-1001\nJohn Smith, 72M\nZip: 10001", BLUE),
        ("Encounter E-2045\nInpatient\n2024-03-15", GREEN),
        ("Claim C-3021\n$12,450\nApproved", ORANGE),
        ("Payer\nMedicare\nPart A", TEAL),
        ("Diagnosis\nI10 Hypertension\nChronic", RED),
        ("Medication\nLisinopril 10mg\nACE Inhibitor", PURPLE),
        ("Adherence\nPDC: 0.85\nAdherent", BLUE),
    ]
    STEP_W = 170
    STEP_H = 46
    STEP_GAP = 10
    total_sw = len(steps) * STEP_W + (len(steps)-1) * STEP_GAP
    step_sx = MARGIN + (PW - 2*MARGIN - total_sw) // 2
    step_sy = TRAV_Y + 26

    for j, (stxt, sclr) in enumerate(steps):
        sx = step_sx + j * (STEP_W + STEP_GAP)
        _rect(root, _nid(), stxt,
              (f"rounded=1;whiteSpace=wrap;html=1;"
               f"fillColor={WHITE};strokeColor={sclr};strokeWidth=2;"
               f"fontSize=8;fontColor={TEXT_PRI};fontFamily=Segoe UI;"
               "align=left;spacingLeft=8;"),
              sx, step_sy, STEP_W, STEP_H)
        if j > 0:
            _edge(root, _nid(), "", _arrow_style(),
                  sx - STEP_GAP, step_sy + STEP_H // 2,
                  sx, step_sy + STEP_H // 2)

    # ── LEGEND ───────────────────────────────────────────────
    LEG_Y = TRAV_Y + TRAV_H + 10
    LEG_H = 70
    _rect(root, _nid(), "",
          _section_style(),
          MARGIN, LEG_Y, PW // 2 - MARGIN, LEG_H)
    _rect(root, _nid(), "Legend",
          _title_style(10, True, TEXT_PRI),
          MARGIN + 16, LEG_Y + 4, 60, 14)

    leg_items = [
        (BLUE, "Batch / Lakehouse / Power Automate"),
        (GREEN, "Clinical"),
        (ORANGE, "Streaming / Real-Time"),
        (RED, "Data Activator (Fraud Alerts)"),
        (PURPLE, "Ontology / Graph / Teams"),
        (GOLD, "RTI / KQL / Operations Agent"),
    ]
    for j, (lclr, ltxt) in enumerate(leg_items):
        col = j // 3
        row = j % 3
        lx = MARGIN + 16 + col * 220
        ly = LEG_Y + 22 + row * 16
        _rect(root, _nid(), "",
              f"rounded=1;whiteSpace=wrap;html=1;fillColor={lclr};strokeColor=none;",
              lx, ly, 12, 12)
        _rect(root, _nid(), ltxt,
              _entity_text_style(8, TEXT_SEC),
              lx + 18, ly - 1, 180, 14)

    # ── FOOTER ───────────────────────────────────────────────
    _rect(root, _nid(),
          "Healthcare: People, Clinical, Financial, Diagnostic, Pharmacy, Community — 12 Entity Types, 19 Relationships (6 Cross-Domain) — 6 Facts, 6 Dimensions — Star Schema",
          _center_title_style(9, False, TEXT_SEC),
          MARGIN, LEG_Y + LEG_H + 4, PW - 2*MARGIN, 14)
    _rect(root, _nid(),
          "Payer-Provider Healthcare Analytics Demo — Microsoft Fabric — Architecture Reference Diagram",
          _center_title_style(8, False, TEXT_TER),
          MARGIN, LEG_Y + LEG_H + 20, PW - 2*MARGIN, 14)

    return mxfile


def main():
    tree = build_diagram()
    out = Path(__file__).parent / "diagrams" / "healthcare-architecture.drawio"
    out.parent.mkdir(parents=True, exist_ok=True)

    # write with XML declaration
    ET.indent(tree, space="  ")
    ET.ElementTree(tree).write(str(out), encoding="unicode", xml_declaration=True)
    print(f"✅ Written {out}  ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
