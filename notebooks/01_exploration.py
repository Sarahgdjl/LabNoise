# %% [markdown]
# # LabNoise - Phase 2: Exploration
# DATA IS SYNTHETIC. Run each cell with Shift+Enter (VS Code) and write ONE sentence under each plot.

# %% 1. Load
import pandas as pd, matplotlib.pyplot as plt

df = pd.read_csv("data/analysis_days.csv")
print(df.shape)
df.head()

# %% 2. How many draws per day? (the decision we study)
print("Mean draws/day:", df.n_lab_draws.mean().round(2))
print("Days with zero draws:", (df.n_lab_draws == 0).mean().round(3))
df.n_lab_draws.value_counts().sort_index().plot(kind="bar", color="#4C72B0")
plt.xlabel("Lab draws in a day"); plt.ylabel("Patient-days")
plt.title("Distribution of daily lab draws")
plt.savefig("figures/01_draws_distribution.png", dpi=150, bbox_inches="tight"); plt.show()

# %% 3. Legit signal: do sicker patients get more draws?
df["sofa_bin"] = pd.cut(df.sofa_observed, [-1, 2, 5, 8, 11, 15, 30],
                        labels=["0-2", "3-5", "6-8", "9-11", "12-15", "16+"])
by_sofa = df.groupby("sofa_bin", observed=True).n_lab_draws.mean()
by_sofa.plot(marker="o")
plt.xlabel("Severity (SOFA bin)"); plt.ylabel("Mean draws/day")
plt.title("Ordering rises with severity (expected, legitimate)")
plt.savefig("figures/02_draws_vs_severity.png", dpi=150, bbox_inches="tight"); plt.show()

# %% 4. Raw team differences (looks like noise, but patients may differ)
team_mean = df.groupby("team_id").n_lab_draws.mean().sort_values()
team_mean.plot(kind="bar", figsize=(10, 4), color="#55A868")
plt.axhline(df.n_lab_draws.mean(), color="red", ls="--", label="overall mean")
plt.ylabel("Mean draws/day"); plt.title("Raw mean draws per team"); plt.legend()
plt.savefig("figures/03_team_raw.png", dpi=150, bbox_inches="tight"); plt.show()

# %% 5. KEY PLOT: "same patient, different team" (observed / expected)
# Expected = average draws of ALL patient-days in the same situation (severity bin x prior abnormal x first day)
df["first_day"] = (df.day == 1).astype(int)
df["expected"] = df.groupby(["sofa_bin", "prior_day_any_abnormal", "first_day"],
                            observed=True).n_lab_draws.transform("mean")
oe = (df.groupby("team_id").n_lab_draws.sum() / df.groupby("team_id").expected.sum()).sort_values()
oe.plot(kind="bar", figsize=(10, 4), color="#C44E52")
plt.axhline(1, color="black", ls="--")
plt.ylabel("Observed / expected draws")
plt.title("Same-patient comparison: ordering by team (1.0 = as expected)")
plt.savefig("figures/04_team_obs_over_exp.png", dpi=150, bbox_inches="tight"); plt.show()
print(f"Teams range from {oe.min():.2f}x to {oe.max():.2f}x expected ordering")

# %% 6. Low-value draws by team
lv = df[df.day > 1].groupby("team_id").low_value_draw.mean().sort_values()
lv.plot(kind="bar", figsize=(10, 4), color="#8172B2")
plt.ylabel("Share of patient-days with a low-value draw")
plt.title("Low-value draw rate per team")
plt.savefig("figures/05_lowvalue_by_team.png", dpi=150, bbox_inches="tight"); plt.show()

# %% 7. Weekend effect
print(df.groupby("is_weekend").n_lab_draws.mean().round(2))