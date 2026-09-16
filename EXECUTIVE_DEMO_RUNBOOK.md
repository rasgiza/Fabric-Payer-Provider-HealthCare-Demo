# Executive Demo Runbook — The Nancy & Sarah Story

**Audience:** Healthcare executives (CMO, COO, CFO, CIO, VP Quality) — provider-side or mixed payer/provider
**Length:** ~12 minutes
**Tools:** Fabric data agent `HealthcareHLSAgent` (Steps 0–5, returns rows) → Foundry agent `Healthcare Ontology Agent` (Step 6, returns policy + actions)
**Two patients:** Nancy White (the setup) → Sarah Johnson (the close)
**Goal:** Prove that Microsoft Fabric + an ontology + a plain-English agent can surface readmission risk and care fragmentation no current tool in their hospital can see.

---

## The arc at a glance

1. **Warm-up** — prime the agent silently
2. **Q1** — size the problem (cohort of 300+ at-risk patients)
3. **Q2** — Nancy's adherence by drug class (the triple whammy)
4. **Q3** — Nancy's prescribers (no cardiologist managing)
5. **Q4** — find more patients like Nancy (the pattern scales)
6. **Q5** — Sarah Johnson's full story (benzo-in-COPD contraindication close)
7. **Q6** — hand off to Foundry: what the policy says and what to do about it
8. **Final line** — sit down, don't fill the silence

Total: ~7 minutes narration + ~5 minutes agent runtime = **~12 minutes**.

> **The framing line for the handoff:** *"The Fabric data agent knows what happened. The Foundry agent knows what it means."*

---

## STEP 0 — Warm-up (silent, ~30 sec)

Type these one at a time. Don't narrate them in detail.

1. `List 5 providers`
2. `Show me 5 patients`

If asked what you're doing:

> "Priming the agent — these run on a shared model thread, the first couple of queries warm it up."

Move on.

---

## STEP 1 — Size of the problem

### Set the stage (45 sec — look at the room, not the screen)

> "Every healthcare executive I've sat across from in the last year — provider or payer — has the same number on their scorecard: hospital readmissions. CMS withholds up to three percent of Medicare revenue from hospitals under the HRRP program. Plans see those same readmissions hit their MLR and their Star Ratings. Each avoidable readmission costs the system roughly fifteen thousand dollars in care nobody gets reimbursed for. **Same patient. Different scorecards. One root cause — the data is fragmented.**
>
> A discharge planner today logs into four systems to assemble one patient's full picture. By the time she does, that patient is back in your ED.
>
> What I'm about to show you is what happens when all of that is connected through **one ontology** and you can ask it questions in plain English. Let's start with the size of the problem."

### Type

> **"How many patients are at high readmission risk and non-adherent to their medications?"**

### While it runs (~10 sec)

> "The agent is joining readmission risk from the encounter data with adherence from the pharmacy data. Two systems your team would normally query separately."

### After it lands (30 sec)

> "Over three hundred patients. Each at high risk. Each not taking the medications keeping them out of your ED.
>
> At roughly fifteen thousand dollars per avoidable readmission, **if even one in five comes back, that's nine hundred thousand dollars in avoidable cost — every quarter.** Before the HRRP penalty layered on top.
>
> But the count doesn't tell you what to do. **The story does.** Let me show you one of these patients."

---

## STEP 2 — Nancy White: the triple whammy

### Pivot (15 sec)

> "Three hundred is a number. Numbers don't change behavior — stories do. Nancy White, sixty-three years old. She's on this list. The question is **why**."

### Type

> **"Show me every medication prescribed to Nancy White age 63, with its drug class"**

> 🚨 **Ask for medications here, not adherence.** Adherence is only computed for *chronic*
> maintenance drugs, and her ibuprofen is an acute script — so an adherence question silently
> drops the NSAID and you lose the triple whammy. Expect **10 drug classes**.

### While it runs

> "Patient → prescriptions → medications → drug class. A four-table join in SQL. One sentence in English."

### After it lands (30 sec)

> "Look at these three drug classes — **NSAID, ACE inhibitor, loop diuretic.** In pharmacy this combination has a name. It's called the **triple whammy.** Each drug alone is safe. Together, they cause kidney failure in older patients. It's one of the most preventable causes of hospital admissions over age sixty.
>
> Nancy is sixty-three. She's prescribed all three. And no dashboard in your hospital today shows you this — because the prescriptions live in three different systems.
>
> **That's the mechanism behind her readmission risk.** Now — who prescribed all of this to her?"

### Optional follow-up — if someone asks whether she's actually taking them

> **"Now show me her medication adherence by drug class"**

Expect **9 rows, 8 of them Non-Adherent** at a PDC of 0.43. The only class she takes properly is
her thyroid hormone. The NSAID does not appear here — see the note above.

---

## STEP 3 — Nancy's prescribers: no cardiologist

### Type

> **"Which providers prescribed Nancy White age 63 medications, and what is each provider's specialty?"**

### While it runs

> "Patient → prescriptions → prescribing provider → specialty. Three hops in the ontology."

### After it lands (25 sec)

> "Nine providers. Eight specialties. **Two psychiatrists who don't know about each other. And no cardiologist managing her heart medications.**
>
> Each prescription is safe on its own. Nobody saw the combination — because nobody could.
>
> So — who else in our population looks like Nancy?"

---

## STEP 4 — Find the pattern, not the patient

### Type

> **"Show me 5 more patients who, like Nancy White, have prescriptions from many different providers across multiple specialties"**

### While it runs

> "I'm asking the agent to find the **pattern**, not the patient. Every person in your network whose care looks like Nancy's."

### After it lands (45 sec)

> "Five more Nancys. **Read the top row off the screen — name, age, provider count, specialty count.** Several of them are worse than Nancy: ten providers, nine different specialties, almost one specialty per prescription.
>
> Each name is a Nancy. Each is a readmission waiting to happen. The agent found them in three seconds — without me telling it what to look for. I asked for the **pattern**. It returned the **people**.
>
> But I want to show you one more patient. Not from this list. **Younger.** And the story is worse."

---

## STEP 5 — Sarah Johnson: the close

> ⚠️ **Ask by name AND age — not by patient ID.**
> At the default 10,000-patient volume there are 11 Sarah Johnsons in `dim_patient`, but the
> generator guarantees only **one is 39**, so name + age is unique.
>
> Do **not** type `PAT006030` into the agent. `patient_id` exists only on `dim_patient`; every fact
> table keys on `patient_key`. Filtering facts by patient ID returns zero rows and the agent will
> correctly tell you it has no data for her. `PAT006030` is for *your* reference and for SQL — not for the agent.

> 🚨 **Do not ask for medications and adherence in the same question.**
> "...and her medication adherence" anchors the agent on `agg_medication_adherence`, which holds
> **only 4 chronic drug classes** — ACE inhibitor, statin, anticoagulant, inhaled corticosteroid.
> **Lorazepam has no adherence row.** Ask them together and the benzodiazepine never appears —
> and you lose the close. Two questions, in this order.

### Type — question 1 of 2

> **"Show me Sarah Johnson, age 39 — all her diagnoses, and every medication she has been prescribed with the prescribing provider and their specialty"**

Expect **9 drug classes**, Lorazepam among them. If you see fewer, re-ask with
*"list every medication she has ever filled, including ones she is no longer taking."*

### Type — question 2 of 2 (after you have narrated the medications)

> **"Now show me her medication adherence by drug class"**

Expect **4 rows, all Adherent**: ACE inhibitor 1.00, inhaled corticosteroid 1.00,
statin 0.98, anticoagulant 0.96.

### While it runs

> "Same agent. Same ontology. Different patient. Watch what comes back."

### After it lands (45 sec — stand still, don't click)

> "Sarah Johnson. **Thirty-nine.** Working-age. Tricare — so she's not in a single CMS program you're measured on. Nobody's dashboard is watching her.
>
> Twelve providers. Seven facilities. **Zero** primary care physicians.
>
> Now look at her adherence. This is the part that surprised me. She is **adherent to everything.** ACE inhibitor, one-point-zero-zero. Inhaled corticosteroid, one-point-zero-zero. Statin, ninety-eight. Anticoagulant, ninety-six. **This patient does everything right.**
>
> So watch what the ontology does with that.
>
> Line one — **COPD.** Diagnosed about seventeen months ago, by an orthopedist, at a community clinic.
>
> Line two — **Lorazepam.** A benzodiazepine. Started three hundred and ninety-six days later by an **anesthesiologist**, at a different hospital, who saw her **exactly once** — and then refilled it eight more times without ever seeing her again.
>
> **Benzodiazepines are contraindicated in COPD.** Respiratory depression. It's in your own formulary guide — the agent cited it.
>
> And here's the line that ends the conversation. **Five days ago**, a *second* anesthesiologist started her on a COPD inhaler — while that Lorazepam was still active. Two doctors. Same specialty. Same patient. Pulling in opposite directions. Neither one knew the other existed.
>
> **Nobody made a mistake.** Every single prescription was reasonable in isolation. That's what makes this invisible — and that's exactly what an ontology is for."

Pause. Three full seconds.

### If you have time — the second finding

> "One more, quickly. Her blood pressure medication — lisinopril. Twenty-one fills. **Six hundred and thirty days of medication dispensed into a four-hundred-and-six-day window.** Two prescribers, a surgeon and an orthopedist, at two different facilities, filling two to three days apart, eight separate times. She's been taking a double dose of an ACE inhibitor for over a year. She has heart failure. She's on a blood thinner.
>
> No dashboard shows you this, because to every individual system, she looks perfectly adherent."

---

## STEP 6 — The Foundry handoff (~90 sec)

Switch agents. **Say this while you switch:**

> "Everything so far came from the data agent. It knows *what happened*. Now I'll ask a different agent what it *means* — same ontology underneath, but this one can also read your policy library."

**Agent:** `Healthcare Ontology Agent` in Foundry — it holds the Fabric data agent *and* an MCP tool over the 26-document knowledge base.

**Type this:**

> **"Sarah Johnson, age 39. Confirm from the data every benzodiazepine she has been prescribed — the drug, the prescribing provider, their specialty, the first fill date, and the total days supplied. Then, given her documented diagnoses, tell me what policy says about it, including any prior authorization requirement. Cite your sources and give me next actions."**

> ⚠️ Same rule as Step 5 — **name and age, never the patient ID.**
>
> 🚨 **Do not name Lorazepam in the question.** If you hand the agent the drug, it will answer
> *from your prompt* and print "details not shown here, but stated in the question" — which tells
> the room you fed it the answer. Make it retrieve. The phrase **"confirm from the data"** is
> what forces the traversal; **"prior authorization requirement"** is what pulls the kill-shot document.
>
> ⏱️ **Budget 2–3 minutes, not 60 seconds.** Observed 203s. Talk over it — this is where you
> narrate what it's doing, not where you stand silent.

**What should come back:** Lorazepam 0.5 MG, **Dr. Richard Wilson, Anesthesiology**, first filled
**about four months ago**, **126 days** supplied — then quoted policy with `Source:` lines, then 2–4 actions.

> **If it returns the drug but not the prescriber or the days**, follow up with:
> *"Who prescribed it, what is their specialty, and how many days has she been on it?"*
> Never supply those facts yourself.

**The five documents it should reach for:**

| Document | What it says |
|---|---|
| `formulary/Drug_Formulary_Guide.md` | Lorazepam is **CONTRAINDICATED** in COPD (J44.9) — respiratory depression risk |
| `clinical_guidelines/COPD_Management_Guidelines.md` | Avoid Lorazepam in COPD — benzodiazepines suppress respiratory drive |
| `formulary/Step_Therapy_Protocols.md` | Protocol MH-STEP-002 — a COPD patient is **DENIED** |
| `compliance/Clinical_Documentation_Standards.md` | Requires indication, duration plan, fall risk, respiratory status |
| `denial_management/Prior_Authorization_Requirements.md` | Lorazepam >30 days requires prior auth **and a psychiatry consult** |

> ⚠️ **If it quotes the Beers Criteria, get ahead of it.** `Drug_Formulary_Guide.md:88` genuinely
> cites AGS 2023 Beers — but Beers applies to **age >65**, and Sarah is **39**. The agent sometimes
> blends it in. If a clinician catches it, agree instantly: *"Right — Beers is the elderly rule and
> she isn't elderly. The COPD contraindication and your own prior-auth rule are what apply here."*
> Conceding that fast makes everything else more credible, not less.

**The narration — the last one is the kill shot:**

> "That last rule is your own. Lorazepam beyond thirty days requires a psychiatry consult. **She's at a hundred and twenty-six days.** Her only psychiatry encounter was nearly eighteen months *before* the first Lorazepam fill — and that psychiatrist prescribed her cholesterol medication.
>
> Nobody broke a rule they knew about. The rule was written down. It just wasn't reachable from where the prescription was written."

---

### Final line — say it, then stop

> "Two patients. Twelve minutes. One ontology.
>
> **What's the first question you'd want to ask it about your own data?**"

**Sit down. Don't fill the silence.**

---

## ⛔ DO NOT SAY — disproven for PAT006030

These claims were in earlier versions of this script. They are **false for this patient**. Every
fact this runbook does assert is pinned by `NB_Generate_Sample_Data` and re-verified on each build,
so it survives a regeneration. If a customer's clinician checks, you lose the room.

| Do not say | Why it's false |
|---|---|
| "Concurrent opioid + benzodiazepine" / "FDA black-box combination" | Her opioid and her benzo are **362 days apart**. No overlap. Dataset-wide, **no provider ever prescribes both** to the same patient. |
| "She's non-adherent" / "PDC under 50%" / "she only fills the opioid" | She is **Adherent on every measured class**: ACE-I 1.00, Inhaled Corticosteroid 1.00, Statin 0.978, Anticoagulant 0.957. |
| "Warfarin + NSAID interaction" | No overlap — her warfarin coverage ends **9 days before** the ibuprofen starts. Frame as a coordination near-miss only. |
| "Three psychiatrists" | She has **one** (Dr. Sarah Smith). |
| "A pediatrician prescribing to an adult" | Fictional. The real anomaly is an **ophthalmologist** who wrote her opioid, and a **psychiatrist** who wrote her statin. |
| "Age 41" / "Commercial insurance" / "13 providers" | She is **39**, **Tricare**, **12 providers**, 7 facilities. |

**The verified close is:** benzodiazepine started 396 days after a documented COPD diagnosis, by a
one-visit prescriber at a different facility, still active — plus a duplicated ACE inhibitor
(630 days dispensed into a 406-day window) from two prescribers filling days apart.

---

## The ROI close (use if asked, or as a follow-on)

### The 30-second version

> "Look — Nancy and Sarah aren't hypothetical patients. They're already in your data. So the question isn't *should we invest in this* — the math works if we prevent even one readmission a quarter. The real question is whether your care team can find these patients today. **Right now, they can't. With this, they can.**"

> ⚠️ **The two patients carry different economics. Don't merge them.**
> **Nancy** is the readmission case — Medicare, HRRP-exposed, and the table below applies to her directly.
> **Sarah** is Tricare with no readmission. Her exposure is coordination and safety: a contraindicated
> active prescription, a duplicated ACE inhibitor, and $179K billed across 7 facilities with no PCP.
> If a CFO ties Sarah to the HRRP line, say so plainly: *"She's the reason the penalty math understates
> the problem. Nobody is paying you to find her — and she's the more dangerous patient."*

### The four ways readmissions hit a provider's P&L

| Lever | Annual exposure (mid-size system) | Realistic 1-year capture |
|---|---|---|
| HRRP penalty avoidance | $1M–$3M | $300K–$1M |
| Unreimbursed readmission cost | $12M–$18M | $2M–$4M |
| Bed-day opportunity cost (lost commercial admissions) | $3M–$5M | $1M–$2M |
| Star Ratings / value-based contract bonuses | $3M–$8M | $500K–$2M |
| **Total annual upside** | **$19M–$34M** | **$4M–$9M** |

### The defensible one-liner

> "Every percentage point off the readmission rate is worth roughly **two to four million dollars** for a mid-size system once you add the penalty avoidance, unreimbursed readmissions, freed-up bed days, and value-based bonuses. Sarah and Nancy aren't anecdotes — they're the **mechanism** of moving that needle. You can't reduce a rate you can't see the cause of."

---

## Q&A prep — the lines they'll challenge

**"Is this real patient data?"**
> "Synthetic data, modeled on real-world distributions. The patterns — fragmented prescribing, triple-whammy combinations, contraindicated co-prescribing across specialties — are pulled from published clinical literature and CMS data. We use synthetic patients so we can demo without HIPAA exposure. When we connect this to your data, the names change. The patterns won't."

**"Where does the $15K come from?"**
> "AHRQ's HCUP brief on 30-day readmissions puts the all-payer average around fifteen-two. Medicare-specific is slightly higher. Premier's analyses range ten to twenty depending on DRG. Fifteen is the round midpoint."

**"Where does the 3% HRRP penalty come from?"**
> "ACA Section 3025, codified at 42 USC 1395ww(q). Started at 1% in FY2013, has been capped at 3% since FY2015. Six conditions: heart failure, COPD, pneumonia, AMI, CABG, elective hip and knee."

**"Don't I already have this in my Power BI semantic model?"**
> "A semantic model **counts**. An ontology **connects**. Your semantic model tells you Nancy has nine prescriptions and a 73% non-adherence score. The ontology tells you those nine prescriptions came from eight specialties with no cardiologist coordinating. Same data. Different question. You need both — the semantic model runs your dashboards, the ontology answers the questions that start with *why* and *who else*."

**"How long to stand this up on our data?"**
> "The ontology layer sits on top of Microsoft Fabric's OneLake. If your EMR, claims, and pharmacy data already land in Fabric — or any modern lakehouse — we're talking weeks, not quarters. The schema we just queried is eleven entities and seventeen relationships. That's the whole map."

**"What about hallucinations?"**
> "Every answer is a query against your data, not a generated guess. The ontology constrains it — it can only return what's actually in the graph. We can show you the underlying GQL traversal for any answer."

**"Do you do real-time / streaming?"**
> "Yes — and it closes the loop on what we just showed you. **Batch finds the patient. Streaming catches the moment.** What we just demoed identifies who's at risk. Streaming — Fabric Real-Time Intelligence — tells you the moment Nancy's vitals shift, or the moment she finally fills her ACE inhibitor, or the moment she shows up at another hospital's ED via your HIE feed. Happy to do a separate session on that."

---

## Deliverability checklist (data is real?)

| Claim | Source | Confidence |
|---|---|---|
| 300+ patients high-risk + non-adherent | Agent screen | ✅ Bulletproof |
| Nancy: 9 prescribers, 8 specialties | Agent screen | ✅ Bulletproof |
| Two psychiatrists on Nancy's chart | Agent screen | ✅ Bulletproof |
| No cardiologist on Nancy's chart | Agent screen | ✅ Bulletproof |
| Sarah (`PAT006030`): 12 providers, 7 facilities, 0 PCP | Agent screen | ✅ Bulletproof |
| Sarah: adherent on every measured class (ACE-I 1.00, ICS 1.00, statin 0.978, anticoagulant 0.957) | Agent screen | ✅ Bulletproof |
| Sarah: Lorazepam started 396 days after COPD (J44.9), by a one-visit anesthesiologist | Agent screen | ✅ Bulletproof |
| Sarah: lisinopril 630 days dispensed into a 406-day window, two prescribers | Agent screen | ✅ Bulletproof |
| Triple-whammy clinical mechanism | BMJ 2013 (Lomas et al.) + standard PharmD literature | ✅ Real |
| Benzodiazepine contraindicated in COPD | Customer's own `Drug_Formulary_Guide.md` and `COPD_Management_Guidelines.md` | ✅ Real (agent cites it live) |
| Lorazepam >30 days needs prior auth + psychiatry consult | `Prior_Authorization_Requirements.md` | ✅ Real (she is at 126 days) |
| HRRP 3% cap, six conditions | ACA Section 3025, CMS rule | ✅ Bulletproof (Nancy only — Sarah is Tricare) |
| ~$15K per readmission | AHRQ HCUP brief | ✅ Defensible (say "roughly") |

---

## Delivery rules

1. **Don't read what's on the screen.** Narrate the *meaning*, not the data.
2. **Three beats per question:** what pattern is on screen, why it matters clinically, why no human could have seen it.
3. **Pause after the punchlines.** Don't fill silence. Let it land.
4. **Soften where it's not bulletproof:** "roughly," "if she's filling that NSAID," "working-age."
5. **The close earns the time.** Step 5 is the only place you go long. Everything else is tight.
6. **End with the question. Then sit down.**

---

## What changed across drafts (lessons banked)

- Cut the BMJ citation and the PharmD checklist line — citation flex, slows the room.
- Cut the "pediatrician on a 63-year-old" headline — likely synthetic-data randomness, not bulletproof. Lead with "two psychiatrists" and "no cardiologist" instead.
- Cut the ontology-vs-semantic-model pivot from the live demo — hold for Q&A. Two pivots is one too many.
- Cut reading every PDC number out loud in Step 5 — the screen shows it. One line ("all under 50% on her chronic meds") does the work.
- Don't claim Sarah's insurance type — say "working-age, not Medicare" instead.
- Don't say "no PCP managing" Nancy — Family Medicine *is* on her list. Say "no cardiologist managing her heart medications" instead.
- Always run two warm-up queries first — the agent fails on cold start.
- Never ask the graph agent for `COUNT(DISTINCT)` aggregations — it can't reliably do them. Stick to list and traversal queries.
