"""
load_randstad_global.py
========================
Laadt data_processed/randstad_global.csv in de rw_global_indicators tabel
in Supabase/Postgres.

Gebruik:
    python etl/load_randstad_global.py

Vereisten:
    pip install pandas sqlalchemy psycopg2-binary python-dotenv
"""

import os
import sys
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

CSV_PATH    = Path("data_processed/randstad_global.csv")
SOURCE_CODE = "RANDSTAD_WM_2026"


def get_engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("[FOUT] DATABASE_URL niet gevonden in .env")
        sys.exit(1)
    return create_engine(url)


def validate(df: pd.DataFrame):
    print("── Validatie ──")
    required = ["theme", "indicator_code", "indicator_label",
                "respondent_type", "value_pct"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"  [FOUT] Ontbrekende kolommen: {missing}")
        sys.exit(1)
    print(f"  [OK] Alle verplichte kolommen aanwezig")

    dupes = df[df.duplicated("indicator_code")]
    if not dupes.empty:
        print(f"  [FOUT] Dubbele indicator_codes: {dupes['indicator_code'].tolist()}")
        sys.exit(1)
    print(f"  [OK] Geen duplicaten")

    out_of_range = df[df["value_pct"].notna() & ~df["value_pct"].between(0, 100)]
    if not out_of_range.empty:
        print(f"  [FOUT] Waarden buiten bereik: {out_of_range['indicator_code'].tolist()}")
        sys.exit(1)
    print(f"  [OK] Alle waarden binnen bereik 0–100")


def get_source_id(engine) -> int:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id FROM rw_source_metadata WHERE source_code = :sc"),
            {"sc": SOURCE_CODE}
        ).fetchone()
        if not result:
            print(f"  [FOUT] Geen rij gevonden in rw_source_metadata met source_code='{SOURCE_CODE}'")
            print("         Voer eerst load_randstad.py uit om de metadata te laden.")
            sys.exit(1)
        return result[0]


def load(df: pd.DataFrame, engine, source_id: int):
    print("── Laden ──")

    # Verwijder bestaande rijen voor deze bron
    with engine.begin() as conn:
        deleted = conn.execute(
            text("DELETE FROM rw_global_indicators WHERE source_id = :sid"),
            {"sid": source_id}
        ).rowcount
        print(f"  [OK] {deleted} bestaande rijen verwijderd")

    # Selecteer en hernoem kolommen passend bij het schema
    load_cols = {
        "theme":           "theme",
        "indicator_code":  "indicator_code",
        "indicator_label": "indicator_label",
        "respondent_type": "respondent_type",
        "value_pct":       "value_pct",
        "year_prev_pct":   "year_prev_pct",
        "notes":           "notes",
    }
    df_load = df[[c for c in load_cols if c in df.columns]].copy()
    df_load["source_id"] = source_id

    # change_pp is een GENERATED ALWAYS kolom — niet zelf invullen
    df_load.to_sql(
        "rw_global_indicators",
        engine,
        if_exists="append",
        index=False,
        method="multi"
    )
    print(f"  [OK] {len(df_load)} rijen geladen in rw_global_indicators")


def verify(engine, source_id: int):
    print("── Verificatie ──")
    with engine.connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM rw_global_indicators WHERE source_id = :sid"),
            {"sid": source_id}
        ).scalar()
        print(f"  Totaal rijen:      {total}")

        themes = conn.execute(
            text("""
                SELECT theme, COUNT(*) as n
                FROM rw_global_indicators
                WHERE source_id = :sid
                GROUP BY theme ORDER BY theme
            """),
            {"sid": source_id}
        ).fetchall()
        print(f"  Per theme:")
        for theme, n in themes:
            print(f"    {theme}: {n}")

        with_prev = conn.execute(
            text("""
                SELECT COUNT(*) FROM rw_global_indicators
                WHERE source_id = :sid AND year_prev_pct IS NOT NULL
            """),
            {"sid": source_id}
        ).scalar()
        print(f"  Met year_prev_pct: {with_prev}")

        with_change = conn.execute(
            text("""
                SELECT COUNT(*) FROM rw_global_indicators
                WHERE source_id = :sid AND change_pp IS NOT NULL
            """),
            {"sid": source_id}
        ).scalar()
        print(f"  Met change_pp:     {with_change}")


def main():
    print("=== load_randstad_global.py ===")

    if not CSV_PATH.exists():
        print(f"[FOUT] {CSV_PATH} niet gevonden. Voer eerst extract_randstad_global.py uit.")
        sys.exit(1)

    df = pd.read_csv(CSV_PATH)
    print(f"CSV geladen: {len(df)} rijen")

    validate(df)

    engine = get_engine()
    print("── Verbinding ──")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("  [OK] Verbinding geslaagd")

    source_id = get_source_id(engine)
    print(f"  [OK] source_id = {source_id}")

    load(df, engine, source_id)
    verify(engine, source_id)

    print(f"\n[KLAAR] Randstad Workmonitor 2026 — globale indicatoren succesvol geladen.")


if __name__ == "__main__":
    main()
