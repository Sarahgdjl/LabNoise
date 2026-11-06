# Synthetic ICU dataset (FAKE) — decision-noise audit

**All data is simulated. Say so in your repo, slides and report.**
It is a stand-in until MIMIC-IV access is approved. The pipeline you build here transfers to MIMIC.

Regenerate: `python generate_synthetic_icu.py 3000 42` (n_stays, seed)

## Files
| File | Rows | What |
|---|---|---|
| `stays.csv` | 3000 | one row per ICU stay: age, sex, admission_type, comorbidity_index, admit_sofa, los_days, icu_death, min_hemoglobin |
| `patient_days.csv` | ~24k | one row per stay-day: team_id, sofa_observed, **n_lab_draws** (the decision), lab values (empty if no draw), prior_day_any_abnormal, management_change, died_today |
| `teams.csv` | 36 | team_id, attending_seniority_years |
| `ground_truth.json` | – | the planted truth, for validating your methods |

`true_any_abnormal` in `patient_days.csv` is hidden in real life. Never use it as a feature; it is only for validation.

## What is planted (your positive controls)
- Teams differ in how much they order, independent of patient state (noise). Expected ICC of ~0.12 after adjusting for patient state.
- Legitimate drivers of ordering: severity, previous abnormal labs, first day.
- Draws only help management when something is truly abnormal; low-value draws help ~nothing.
- Each draw lowers hemoglobin (iatrogenic anemia). There is no direct effect of draws on death.

If your mixed model, your causal estimate, and your fairness checks do not recover this, your code has a bug. Debug here, where you know the answer.

## Build order
1. Load into SQLite/Postgres and rebuild the analysis table with SQL (practice for the MIMIC extraction).
2. Define the "low-value draw": a draw when the previous day's labs were all normal and stable.
3. EDA: draws per team vs. severity-adjusted expectation.
4. Mixed model with team random intercept, then variance decomposition and ICC.
5. Causal question: effect of extra draws on hemoglobin (known truth), then on death (known truth: zero).
6. Swap in MIMIC-IV and compare to the planted-truth results.
