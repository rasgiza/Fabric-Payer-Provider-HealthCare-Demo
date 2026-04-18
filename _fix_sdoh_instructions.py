"""Fix SDOH threshold guidance in Graph Agent configs.
The agent was filtering social_vulnerability_index > 0.8 but max SVI is ~0.53.
Should use risk_tier = 'High' instead."""

import json

# === Fix stage_config.json — add SDOH thresholds to CLINICAL RULES ===
for folder in ['published', 'draft']:
    path = f'data_agents/Healthcare Ontology Agent.DataAgent/Files/Config/{folder}/stage_config.json'
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    old = data['aiInstructions']
    
    old_rule = '- SDOH risk: correlate risk_tier and poverty_rate with readmission risk and adherence'
    new_rule = (
        "- SDOH risk: ALWAYS filter by risk_tier (High/Medium/Low), NEVER by raw social_vulnerability_index thresholds.\n"
        "  risk_tier = 'High' means SVI >= 0.30 (NOT 0.8! SVI max is ~0.53 in this dataset).\n"
        "  risk_tier = 'Medium' means SVI 0.15-0.30. risk_tier = 'Low' means SVI < 0.15.\n"
        "  For 'socially vulnerable' or 'high SDOH risk', use: WHERE risk_tier = 'High'\n"
        "  For 'any vulnerability', use: WHERE risk_tier IN ['High', 'Medium']\n"
        "  Correlate with readmission risk and adherence"
    )
    
    data['aiInstructions'] = old.replace(old_rule, new_rule)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'Updated {path}')

# === Fix datasource.json — update CommunityHealth description ===
for folder in ['published', 'draft']:
    path = f'data_agents/Healthcare Ontology Agent.DataAgent/Files/Config/{folder}/graph-Healthcare_Demo_Graph/datasource.json'
    with open(path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    old = data['dataSourceInstructions']
    
    old_text = 'CommunityHealth — SDOH by zip code (PK: sdoh_key, Display: zip_code)'
    new_text = (
        'CommunityHealth — SDOH by zip code (PK: sdoh_key, Display: zip_code). '
        'IMPORTANT: social_vulnerability_index ranges 0.05-0.53 (NOT 0-1). '
        'ALWAYS filter by risk_tier (High/Medium/Low) instead of raw SVI values. '
        'High = SVI >= 0.30, Medium = 0.15-0.30, Low < 0.15'
    )
    
    data['dataSourceInstructions'] = old.replace(old_text, new_text)
    
    # Also update the element description for CommunityHealth
    for elem in data.get('elements', []):
        if elem.get('display_name') == 'CommunityHealth':
            elem['description'] = (
                'SDOH profile by zip code: risk_tier (High/Medium/Low — use this for filtering, '
                'NOT raw SVI), poverty_rate, food_desert_flag, transportation_score, uninsured_rate. '
                'SVI ranges 0.05-0.53, so risk_tier=High means SVI>=0.30'
            )
            break
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f'Updated {path}')

# === Fix fewshots.json — update the vulnerable population example + add SDOH example ===
for folder in ['published', 'draft']:
    path = f'data_agents/Healthcare Ontology Agent.DataAgent/Files/Config/{folder}/graph-Healthcare_Demo_Graph/fewshots.json'
    with open(path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    for shot in data.get('fewShots', []):
        if 'most vulnerable population' in shot.get('question', ''):
            shot['answer'] = (
                "I'll combine three filters using separate queries to stay performant.\n\n"
                "**Traversal plan:**\n"
                "1. **Query 1**: Find non-adherent patients: "
                "MATCH (ma:MedicationAdherence) WHERE ma.adherence_category = 'Non-Adherent' "
                "MATCH (ma)-[:adherenceFor]->(pat:Patient) RETURN pat LIMIT 10\n"
                "2. **Query 2**: For those patients, check SDOH using risk_tier "
                "(NOT raw SVI — SVI max is 0.53 in this data, so never filter SVI > 0.8): "
                "MATCH (pat:Patient)-[:livesIn]->(ch:CommunityHealth) WHERE ch.risk_tier = 'High' "
                "AND pat.patient_key IN [list] RETURN pat, ch LIMIT 10\n"
                "3. **Query 3**: For those patients, check readmission risk: "
                "MATCH (e:Encounter)-[:involves]->(pat:Patient) WHERE pat.patient_key IN [list] "
                "AND e.readmission_risk_category = 'High' RETURN e, pat LIMIT 10\n\n"
                "I present the most vulnerable patients with their SDOH profile, medications/pdc_scores, and providers.\n\n"
                "IMPORTANT: I always filter CommunityHealth by risk_tier = 'High' "
                "(not by social_vulnerability_index > 0.8, which would match nothing since SVI max is ~0.53)."
            )
    
    # Add SDOH-specific fewshot
    data['fewShots'].append({
        'question': (
            'Which providers serve patients in socially vulnerable communities? '
            'Show the SDOH profile alongside provider details.'
        ),
        'answer': (
            "I'll trace from high-risk communities to patients to providers.\n\n"
            "**Traversal plan (separate queries):**\n"
            "1. **Query 1 — Find vulnerable communities**: "
            "MATCH (ch:CommunityHealth) WHERE ch.risk_tier = 'High' "
            "RETURN ch.zip_code, ch.poverty_rate, ch.social_vulnerability_index, ch.food_desert_flag LIMIT 10\n"
            "   IMPORTANT: Filter by risk_tier = 'High', NOT by social_vulnerability_index > 0.8 "
            "(SVI max is ~0.53 in this dataset).\n"
            "2. **Query 2 — Find patients in those zips**: "
            "MATCH (pat:Patient)-[:livesIn]->(ch:CommunityHealth) WHERE ch.risk_tier = 'High' "
            "RETURN pat.patient_id, pat.first_name, pat.last_name, ch.zip_code, ch.risk_tier LIMIT 10\n"
            "3. **Query 3 — Find their providers**: For each patient, "
            "MATCH (e:Encounter)-[:involves]->(pat:Patient) WHERE pat.patient_key = X "
            "MATCH (e)-[:serves]->(prov:Provider) RETURN prov.display_name, prov.specialty LIMIT 5\n\n"
            "I present each provider with the SDOH profile of the communities they serve: "
            "zip code, risk_tier, poverty_rate, food_desert_flag, and SVI score.\n\n"
            "Tip: You can also ask about specific SDOH factors like "
            "'providers serving patients in food deserts' or 'providers in high-poverty zip codes'."
        )
    })
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Updated {path} - {len(data['fewShots'])} fewshots")

print('\nAll done')
