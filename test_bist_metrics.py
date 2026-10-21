import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from database import get_connection

conn = get_connection()

bist_df = pd.read_sql_query("""
    SELECT * FROM signal_log WHERE source = 'bist'
""", conn)
conn.close()

print("=== BIST METRIKLERI ===")
print(f"Toplam sinyal: {len(bist_df)}")
print(f"Benzersiz kural: {bist_df['rule_name'].nunique()}")
print(f"Benzersiz hisse: {bist_df['symbol'].nunique()}")
print()

print("--- Kural Bazli Sinyal Sayilari ---")
rule_counts = bist_df.groupby('rule_name').size().sort_values(ascending=False)
for rule, count in rule_counts.items():
    print(f"  {rule}: {count} sinyal")

print()
print("--- Hisse Bazli Sinyal Sayilari (Top 10) ---")
hisse_counts = bist_df.groupby('symbol').size().sort_values(ascending=False).head(10)
for hisse, count in hisse_counts.items():
    print(f"  {hisse}: {count} sinyal")
