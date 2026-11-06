import sqlite3, pandas as pd

conn = sqlite3.connect("data/labnoise.db")
conn.executescript(open("sql/build_cohort.sql").read())
df = pd.read_sql("SELECT * FROM analysis_days", conn)
print(len(df), "rows,", df.shape[1], "columns")
print(df.isna().sum()[lambda x: x > 0])
print("low-value draw share:", df.low_value_draw.mean().round(3))
df.to_csv("data/analysis_days.csv", index=False)
conn.close()