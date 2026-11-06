DROP TABLE IF EXISTS analysis_days;

CREATE TABLE analysis_days AS
SELECT
    d.stay_id,
    d.day,
    d.date,
    d.day_of_week,
    CASE WHEN d.day_of_week >= 5 THEN 1 ELSE 0 END           AS is_weekend,
    d.team_id,
    t.attending_seniority_years,
    s.age,
    s.sex,
    s.admission_type,
    s.comorbidity_index,
    s.admit_sofa,
    d.sofa_observed,
    LAG(d.sofa_observed) OVER w                               AS prev_sofa,
    d.sofa_observed - LAG(d.sofa_observed) OVER w             AS sofa_change,
    COALESCE(LAG(d.n_lab_draws) OVER w, 0)                    AS prev_n_draws,
    d.prior_day_any_abnormal,
    d.n_lab_draws,
    CASE WHEN d.n_lab_draws > 0 THEN 1 ELSE 0 END             AS any_draw,
    CASE WHEN d.n_lab_draws > 0
          AND d.day > 1
          AND d.prior_day_any_abnormal = 0
         THEN 1 ELSE 0 END                                    AS low_value_draw,
    d.hemoglobin,
    d.management_change,
    d.died_today,
    d.discharged_today,
    s.los_days,
    s.icu_death
FROM patient_days d
JOIN stays  s ON s.stay_id = d.stay_id
JOIN teams  t ON t.team_id = d.team_id
WINDOW w AS (PARTITION BY d.stay_id ORDER BY d.day);