import sqlite3, pandas as pd

conn = sqlite3.connect("data/labnoise.db")
for name in ["stays", "patient_days", "teams"]:
    df = pd.read_csv(f"data/{name}.csv")
    df.to_sql(name, conn, if_exists="replace", index=False)
    print(name, len(df), "rows")
conn.close()