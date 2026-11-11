# Post-Discharge Readmission Prevention

This is the accelerator's flagship end-to-end provider scenario: connect
clinical, pharmacy, claims, follow-up, and social-risk signals early enough for
a care manager to review the evidence and act during the post-discharge
transition.

The objective is not to claim that AI prevents readmissions. The objective is
to shorten the time between a meaningful risk signal and a documented,
human-approved intervention.

> [!IMPORTANT]
> All patients and events in this repository are synthetic. This scenario is a
> demonstration and proof-of-concept pattern, not a clinical decision system.
> Production implementations require organization-specific clinical
> validation, workflow integration, governance, privacy, security, and human
> oversight.

## The Industry Problem

The information needed to manage a post-discharge transition is often spread
across separate systems:

- The encounter record knows when and why the patient was discharged.
- Risk models identify clinical and utilization risk.
- Pharmacy data shows medication dispensing and longitudinal adherence.
- Scheduling and care-management systems track follow-up and outreach.
- Claims data shows subsequent emergency or inpatient utilization.
- SDOH data identifies transportation, pharmacy-access, housing, and financial
  barriers.

Each system can be correct while the combined risk remains invisible. The
customer problem is therefore not only prediction; it is assembling an
actionable picture soon enough for a care team to respond.

## Target Users

- Transition-of-care nurses
- Care managers
- Clinical pharmacists
- Population-health teams
- Quality and value-based-care leaders
- Medical directors

## Desired Workflow

1. A patient is discharged from an inpatient encounter.
2. Fabric evaluates available clinical, utilization, medication, follow-up,
   and social-risk signals.
3. The patient is prioritized when the combined evidence warrants review.
4. `HealthcareHLSAgent` retrieves the underlying patient evidence from the
   Gold lakehouse.
5. `HealthcareOrchestratorAgent2` combines that verified evidence with cited
   transition-of-care and medication-policy content from Azure AI Search.
6. A qualified care-team member reviews the evidence and approves the next
   action.
7. The organization monitors outreach completion, medication access,
   follow-up, emergency utilization, and 30-day readmission.

The workflow is:

```text
Risk signal
  -> verified patient evidence
  -> cited policy guidance
  -> care-team review
  -> approved intervention
  -> observed outcome
```

## Example Care-Team Actions

Depending on the verified evidence and the organization's approved protocols,
a care manager might:

- Arrange medication delivery or pharmacy assistance.
- Schedule primary-care, specialty, or pharmacist follow-up.
- Address a transportation or access barrier.
- Reconcile the discharge medication list.
- Escalate a concerning clinical pattern to an authorized clinician.
- Document outreach and schedule another review.

The agent recommends options; it does not independently diagnose, prescribe,
or initiate clinical action.

## Solution Mapping

| Responsibility | Accelerator component |
|---|---|
| Integrate encounter, pharmacy, claims, provider, payer, and SDOH data | Bronze, Silver, and Gold lakehouses |
| Calculate readmission, adherence, utilization, and social-risk signals | Gold facts, aggregates, and semantic model |
| Retrieve patient-level evidence and cohort results | `HealthcareHLSAgent` |
| Detect optional streaming events and operational signals | Fabric Real-Time Intelligence |
| Retrieve cited policy and guideline evidence | Azure AI Search knowledge index |
| Combine patient evidence with policy-grounded next actions | `HealthcareOrchestratorAgent2` |
| Review and approve intervention | Care manager or other qualified user |
| Explore entity relationships | Healthcare ontology, where supported and validated |

## Capability Status

The current accelerator supports investigation and prioritization, but it does
not yet implement every step of a production closed-loop workflow.

| Capability | Status | Notes |
|---|---|---|
| Readmission-risk score and category | Available | Stored on the curated encounter data and summarized in `agg_readmission` |
| Patient, encounter, diagnosis, medication, provider, payer, and SDOH evidence | Available | Queryable through the Gold lakehouse |
| Longitudinal medication adherence using PDC | Available | Appropriate for chronic adherence analysis |
| Natural-language cohort and patient investigation | Available | Delivered through `HealthcareHLSAgent` |
| Policy-grounded recommendations with citations | Optional | Requires the Foundry and Azure AI Search setup |
| ADT and operational event processing | Optional | Requires `DEPLOY_STREAMING = True` |
| Discharge-prescription non-fill detection | Planned | Requires an expected-fill event and a defined elapsed-time rule |
| Follow-up appointment and outreach completion | Planned | Requires scheduling or care-management workflow data |
| Care-manager task creation and closure | Planned | Requires integration with the organization's workflow system |
| Intervention-to-outcome tracking | Planned | Requires a durable intervention record and observation window |
| New ontology experience as Data Agent context | Blocked | Deferred while Microsoft Fabric known issue 1987 remains active |

## Important Measurement Distinctions

### Adherence is not the same as a discharge prescription fill

The accelerator's PDC measures describe longitudinal medication possession for
chronic therapy. They should not be used to claim that a newly discharged
patient failed to fill a specific prescription within two or three days.

A production non-fill signal needs:

- A discharge prescription or medication order
- The time the prescription became actionable
- A matching dispense/fill event
- A defined elapsed-time threshold
- Rules for cancelled, transferred, substituted, or clinically discontinued
  prescriptions

### Risk is not certainty

A high-risk score prioritizes review. It does not establish that the patient
will be readmitted or that existing care is inappropriate.

### An observed outcome is not proof of causation

Use measurable language:

> The intervention was completed, and no readmission was observed during the
> 30-day monitoring period.

Do not claim that the intervention definitively prevented a readmission
without an appropriate evaluation design.

## Demonstration Approach

### What can be demonstrated now

1. Identify a high-risk or non-adherent cohort.
2. Investigate a named patient's encounters, medications, providers, payer,
   adherence, and social-risk context.
3. Find other patients with a similar evidence pattern.
4. Send verified patient evidence to `HealthcareOrchestratorAgent2`.
5. Retrieve cited policy guidance and proposed next actions for human review.

Use [EXECUTIVE_DEMO_RUNBOOK.md](EXECUTIVE_DEMO_RUNBOOK.md) for the tested
Nancy White and Sarah Johnson presentation flow.

### What should be added before demonstrating the full closed loop

Create a deterministic synthetic patient journey containing:

- A qualifying discharge encounter
- A documented discharge medication
- An expected but missing fill event
- A relevant social-access barrier
- A defined follow-up requirement
- A care-manager intervention record
- A reproducible 30-day observation period

The illustrative patient and timeline should not be promoted as a tested demo
until those records exist in the generated data and the expected results are
validated against the Gold lakehouse.

## Suggested Questions

These are target questions for the completed workflow. They are not yet part
of the tested question contract.

- Which recently discharged patients have elevated readmission risk and
  unresolved medication-access or follow-up concerns?
- For this patient, show the discharge, diagnoses, medications, fill activity,
  follow-up status, recent utilization, and relevant social barriers.
- Which evidence caused this patient to be prioritized?
- Which transition-of-care policies apply, and what actions do they recommend?
- Which interventions were completed, and what utilization was observed during
  the following 30 days?

Tested prompts for currently deployed capabilities remain in
[SAMPLE_QUESTIONS.md](SAMPLE_QUESTIONS.md).

## Success Measures

A production implementation should measure both operational performance and
patient outcomes:

| Measure | Purpose |
|---|---|
| Time from discharge to risk identification | Determines whether the signal is early enough to act |
| Time from identification to first outreach | Measures operational responsiveness |
| Outreach completion rate | Confirms that prioritized patients were contacted |
| Medication-access issue resolution | Tracks whether identified barriers were addressed |
| Follow-up appointment completion | Measures transition-of-care execution |
| Emergency visit within 30 days | Monitors subsequent acute utilization |
| Readmission within 30 days | Monitors the observed outcome |
| Recommendation acceptance and override | Supports governance and model improvement |

## Ontology Roadmap

The use case does not depend on ontology to deliver its first customer value.
The current lakehouse agent can retrieve the evidence, and the Foundry
orchestrator can ground recommendations in cited policy.

Once the new Fabric ontology experience works reliably as Data Agent context,
it can strengthen relationship-oriented investigation across:

```text
Patient
  -> discharge encounter
  -> prescription
  -> medication
  -> prescribing provider
  -> payer
  -> community-access context
  -> intervention
```

Until then, the repository keeps the existing graph-backed ontology for
compatibility and does not claim that `HealthcareOrchestratorAgent2` is
ontology-grounded.
