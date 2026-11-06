"""
SYNTHETIC ICU DATA GENERATOR  --  for development of the clinical decision-noise audit.

!! ALL DATA PRODUCED HERE IS FAKE. Never present it as real patient data. !!

Purpose: build and debug the whole pipeline (cohort -> noise model -> causal analysis)
BEFORE MIMIC-IV access is approved. Because we planted the truth ourselves
(see ground_truth.json), you can check that your methods RECOVER it. That is a
legitimate methodological use of simulation (a "positive control").

Structure mimics MIMIC-IV in spirit (stays / patient-days / lab draws), not in exact schema.

Usage:  python generate_synthetic_icu.py [n_stays] [seed]
"""
import sys, json
import numpy as np
import pandas as pd

N_STAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 42
rng = np.random.default_rng(SEED)

# ---------------- planted ground truth ----------------
TRUTH = {
    "sigma_team_log_rate": 0.30,       # between-team SD on log lab-draw rate (the "noise")
    "beta_severity": 0.05,             # per SOFA point, log rate (legit signal)
    "beta_prior_abnormal": 0.30,       # legit signal
    "beta_first_day": 0.20,
    "beta_weekend": -0.12,             # shift/time effect (noise-like)
    "mgmt_gain_if_abnormal_draw": 0.9, # draws help ONLY when something is truly abnormal
    "mgmt_gain_if_normal_draw": 0.03,  # low-value draws: ~no benefit
    "hb_drop_per_draw_g_dl": 0.06,     # iatrogenic anemia: causal harm of extra draws
    "mortality_effect_of_draws": 0.0,  # truth: NO direct effect on death
}

N_TEAMS = 36
seniority = rng.integers(2, 25, N_TEAMS)
u_team = (-0.012 * (seniority - 12)) + rng.normal(0, TRUTH["sigma_team_log_rate"], N_TEAMS)
teams = pd.DataFrame({"team_id": np.arange(N_TEAMS), "attending_seniority_years": seniority})

def sigmoid(x): return 1 / (1 + np.exp(-x))

def abnormal(lact, cr, k, wbc, hb):
    flags = []
    if lact is not None: flags.append(lact > 2.0)
    if cr is not None: flags.append(cr > 1.3)
    if k is not None: flags.append(k < 3.5 or k > 5.0)
    if wbc is not None: flags.append(wbc < 4 or wbc > 12)
    if hb is not None: flags.append(hb < 8.0)
    return any(flags)

stays, days = [], []
start = pd.Timestamp("2025-01-01")

for sid in range(N_STAYS):
    age = int(np.clip(rng.normal(64, 16), 18, 95))
    sex = rng.choice(["F", "M"], p=[0.43, 0.57])
    adm = rng.choice(["medical", "surgical", "emergency"], p=[0.5, 0.2, 0.3])
    como = int(np.clip(rng.poisson(2.2 + 0.02 * (age - 60)), 0, 10))
    s = float(np.clip(rng.gamma(3.0, 1.6) + (2.0 if adm == "emergency" else 0), 0, 20))
    admit_sofa = int(round(s))
    base_cr = float(np.clip(rng.lognormal(np.log(0.95), 0.25) + 0.05 * como, 0.5, 4.0))
    hb = float(np.clip(rng.normal(12.5 - 0.15 * como, 1.6), 6.5, 17))
    t0 = start + pd.Timedelta(days=int(rng.integers(0, 700)))
    last = dict(lact=None, cr=None, k=None, wbc=None, hb=None)
    died, day = 0, 0
    team_offset = int(rng.integers(0, N_TEAMS))
    while True:
        day += 1
        date = t0 + pd.Timedelta(days=day - 1)
        dow = date.dayofweek
        # team rotates weekly -> assignment ~ independent of patient (quasi-natural experiment)
        team = (team_offset + (date.dayofyear // 7) * 7 + int(rng.integers(0, 3))) % N_TEAMS
        # latent severity dynamics
        s = max(0.0, s + rng.normal(-0.25, 0.9) + (rng.random() < 0.06) * rng.gamma(2, 1.5))
        s = min(s, 22)
        # true biology
        t_lact = 0.9 * np.exp(rng.normal(0, 0.18)) + 0.22 * s
        t_cr = base_cr * (1 + 0.045 * s) * np.exp(rng.normal(0, 0.08))
        t_k = 4.1 + 0.035 * s + rng.normal(0, 0.35)
        t_wbc = max(1.0, 8.0 + 0.5 * s + rng.normal(0, 2.2))
        truly_abn = abnormal(t_lact, t_cr, t_k, t_wbc, hb)

        prior_abn = int(abnormal(**last)) if day > 1 and last["lact"] is not None else 0
        # ----- DECISION: number of lab draws today -----
        log_rate = (np.log(1.2) + TRUTH["beta_severity"] * s
                    + TRUTH["beta_prior_abnormal"] * prior_abn
                    + TRUTH["beta_first_day"] * (day == 1)
                    + TRUTH["beta_weekend"] * (dow >= 5)
                    + u_team[team])
        n_draws = int(min(rng.poisson(np.exp(log_rate)), 6))

        # iatrogenic anemia from draws (planted causal harm)
        hb = max(5.5, hb - TRUTH["hb_drop_per_draw_g_dl"] * n_draws + rng.normal(0, 0.05))

        row_labs = dict(lactate=np.nan, creatinine=np.nan, potassium=np.nan, wbc=np.nan, hemoglobin=np.nan)
        obs_abn = 0
        if n_draws > 0:
            row_labs = dict(
                lactate=round(t_lact * np.exp(rng.normal(0, 0.05)), 2),
                creatinine=round(t_cr * np.exp(rng.normal(0, 0.04)), 2),
                potassium=round(t_k + rng.normal(0, 0.12), 1),
                wbc=round(t_wbc * np.exp(rng.normal(0, 0.06)), 1),
                hemoglobin=round(hb + rng.normal(0, 0.15), 1),
            )
            last = dict(lact=row_labs["lactate"], cr=row_labs["creatinine"], k=row_labs["potassium"],
                        wbc=row_labs["wbc"], hb=row_labs["hemoglobin"])
            obs_abn = int(abnormal(**last))

        # ----- management change (benefit of draws only when truly abnormal) -----
        gain = 0.0
        if n_draws > 0:
            gain = TRUTH["mgmt_gain_if_abnormal_draw"] if obs_abn else TRUTH["mgmt_gain_if_normal_draw"]
        p_mgmt = sigmoid(-2.3 + 0.17 * s + gain)
        mgmt = int(rng.random() < p_mgmt)

        # ----- end of day: death / discharge (NO direct effect of draws) -----
        p_death = sigmoid(-7.2 + 0.30 * s + 0.025 * (age - 60) + 0.05 * como
                          + TRUTH["mortality_effect_of_draws"] * n_draws)
        p_disc = sigmoid(-1.2 - 0.35 * (s - 3)) * (day >= 2)
        d_today = int(rng.random() < p_death)
        disc = int((not d_today) and rng.random() < p_disc) or int(day >= 28)

        days.append(dict(
            stay_id=sid, day=day, date=date.date().isoformat(), day_of_week=dow, team_id=team,
            sofa_observed=int(np.clip(round(s + rng.normal(0, 0.8)), 0, 24)),
            n_lab_draws=n_draws, **row_labs,
            prior_day_any_abnormal=prior_abn, management_change=mgmt,
            true_any_abnormal=int(truly_abn),  # hidden in real data; kept for validation only
            died_today=d_today, discharged_today=disc))
        if d_today:
            died = 1
            break
        if disc:
            break

    stays.append(dict(stay_id=sid, age=age, sex=sex, admission_type=adm, comorbidity_index=como,
                      admit_sofa=admit_sofa, los_days=day, icu_death=died,
                      min_hemoglobin=None))

days_df = pd.DataFrame(days)
stays_df = pd.DataFrame(stays)
stays_df["min_hemoglobin"] = stays_df.stay_id.map(days_df.groupby("stay_id").hemoglobin.min())

import os
out = os.path.dirname(os.path.abspath(__file__))
stays_df.to_csv(f"{out}/stays.csv", index=False)
days_df.to_csv(f"{out}/patient_days.csv", index=False)
teams.to_csv(f"{out}/teams.csv", index=False)
with open(f"{out}/ground_truth.json", "w") as f:
    json.dump({"seed": SEED, "n_stays": N_STAYS, "n_teams": N_TEAMS, **TRUTH,
               "note": "SYNTHETIC. Planted values to validate that your methods recover them."}, f, indent=2)
print(f"stays={len(stays_df)}  patient_days={len(days_df)}  teams={N_TEAMS}  mortality={stays_df.icu_death.mean():.1%}")
