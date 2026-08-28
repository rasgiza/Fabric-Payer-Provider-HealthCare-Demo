# Executive Demo Runbook — The Nancy & Sarah Story

**Audience:** Healthcare executives (CMO, COO, CFO, CIO, VP Quality) — provider-side or mixed payer/provider
**Length:** ~10 minutes
**Tool:** Healthcare Ontology Agent (Graph Data Agent) only
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
7. **Final line** — sit down, don't fill the silence

Total: ~6 minutes narration + ~3 minutes agent runtime = **~10 minutes**.

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

> **"Show me medication adherence for Nancy White age 63 by drug class"**

### While it runs

> "Patient → prescriptions → medications → drug class, with fill rate per class. A four-table join in SQL. One sentence in English."

### After it lands (30 sec)

> "Look at these three drug classes — **NSAID, ACE inhibitor, loop diuretic.** In pharmacy this combination has a name. It's called the **triple whammy.** Each drug alone is safe. Together, they cause kidney failure in older patients. It's one of the most preventable causes of hospital admissions over age sixty.
>
> Nancy is sixty-three. She's prescribed all three. And no dashboard in your hospital today shows you this — because the prescriptions live in three different systems.
>
> **That's the mechanism behind her readmission risk.** Now — who prescribed all of this to her?"

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

> "Five more Nancys. Look at this one — **Barbara Johnson, age fifty. Ten providers. Nine different specialties.** Almost one specialty per prescription. Worse than Nancy.
>
> Robert Wilson, eighty-five, ten doctors. Christopher Gonzalez, seventy-two, eleven providers.
>
> Each name is a Nancy. Each is a readmission waiting to happen. The agent found them in three seconds — without me telling it what to look for. I asked for the **pattern**. It returned the **people**.
>
> But I want to show you one more patient. Not from this list. **Younger.** And the story is worse."

---

## STEP 5 — Sarah Johnson: the close

> ⚠️ **Use the patient ID, never the name.** There are 11 Sarah Johnsons in `dim_patient`.
> The story patient is **`PAT006030`**.

### Type

> **"Show me patient PAT006030 — her diagnoses, her medications with prescribing provider and specialty, and her medication adherence"**

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
> Line one — **COPD.** Diagnosed March of last year, by an orthopedist, at a community clinic.
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

### Final line — say it, then stop

> "Two patients. Twelve minutes. One ontology.
>
> **What's the first question you'd want to ask it about your own data?**"

**Sit down. Don't fill the silence.**

---

## ⛔ DO NOT SAY — disproven for PAT006030

These claims were in earlier versions of this script. They are **false for this patient** and were
verified against `lh_gold_curated` on 2026-08-27. If a customer's clinician checks, you lose the room.

| Do not say | Why it's false |
|---|---|
| "Concurrent opioid + benzodiazepine" / "FDA black-box combination" | Her opioid (Apr 2025) and her benzo (Apr 2026) are **362 days apart**. No overlap. Dataset-wide, **no provider ever prescribes both** to the same patient. |
| "She's non-adherent" / "PDC under 50%" / "she only fills the opioid" | She is **Adherent on every measured class**: ACE-I 1.00, Inhaled Corticosteroid 1.00, Statin 0.978, Anticoagulant 0.957. |
| "Warfarin + NSAID interaction" | No overlap — warfarin coverage ends 2026-07-01, ibuprofen starts 2026-07-10. **−9 days.** Frame as a coordination near-miss only. |
| "Three psychiatrists" | She has **one** (Dr. Sarah Smith). |
| "A pediatrician prescribing to an adult" | Fictional. The real anomaly is an **ophthalmologist** who wrote her opioid, and a **psychiatrist** who wrote her statin. |
| "Age 41" / "Commercial insurance" / "13 providers" | She is **39**, **Tricare**, **12 providers**, 7 facilities. |

**The verified close is:** benzodiazepine started 396 days after a documented COPD diagnosis, by a
one-visit prescriber at a different facility, still active — plus a duplicated ACE inhibitor
(630 days dispensed into a 406-day window) from two prescribers filling days apart.

---

## The ROI close (use if asked, or as a follow-on)

### The 30-second version

> "Look — Nancy and Sarah aren't hypothetical patients. They're already in your data. Your hospital is already paying for their readmissions. So the question isn't *should we invest in this* — the math works if we prevent even one readmission a quarter. The real question is whether your care team can find these patients today, before they bounce back. **Right now, they can't. With this, they can.**"

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
> "The ontology layer sits on top of Microsoft Fabric's OneLake. If your EMR, claims, and pharmacy data already land in Fabric — or any modern lakehouse — we're talking weeks, not quarters. The schema we just queried is twelve entities and eighteen relationships. That's the whole map."

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
| Sarah: opioid PDC 1.00, benzo PDC 0.50 | Agent screen | ✅ Bulletproof |
| Sarah: opioid by Cardiology, benzo by Internal Medicine | Agent screen (earlier prescriber pull) | ✅ Bulletproof |
| Triple-whammy clinical mechanism | BMJ 2013 (Lomas et al.) + standard PharmD literature | ✅ Real |
| FDA black-box opioid+benzo | FDA boxed warning, August 2016 | ✅ Real |
| HRRP 3% cap, six conditions | ACA Section 3025, CMS rule | ✅ Bulletproof |
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
