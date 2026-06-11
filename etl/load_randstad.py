"""
load_randstad.py
=================
Laadt de Randstad Workmonitor 2026 data naar PostgreSQL (Supabase).

Gebruik:
    python etl/load_randstad.py

Vereisten:
    pip install sqlalchemy psycopg2-binary pandas python-dotenv

Omgevingsvariabelen (.env in projectroot):
    DATABASE_URL=postgresql://postgres.xxx:WACHTWOORD@aws-0-eu-central-1.pooler.supabase.com:5432/postgres

Invoer:
    data_processed/randstad_raw.csv   (gegenereerd door extract_randstad.py)

Stappen:
    1. Laad en valideer de CSV
    2. Voeg een rij in rw_source_metadata in (of hergebruik bestaande)
    3. Laad alle rijen in rw_market_indicators
    4. Voer verificatiequery's uit
"""

import os
import sys
import pandas as pd
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print("Installeer sqlalchemy: pip install sqlalchemy psycopg2-binary")
    sys.exit(1)

# ── Configuratie ──────────────────────────────────────────────────────────────
INPUT_PATH   = Path("data_processed/randstad_raw.csv")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
SOURCE_CODE  = "RANDSTAD_WM_2026"

SOURCE_METADATA = {
    "source_code":       "RANDSTAD_WM_2026",
    "source_name":       "Randstad Workmonitor",
    "edition":           "2026",
    "survey_year":       2026,
    "n_talent":          27000,
    "n_employers":       1225,
    "n_markets":         34,
    "publication_url":   "https://www.randstad.com/workmonitor/",
    "notes": (
        "Extracted via extract_randstad.py. "
        "'not in RM' = indicator not reported for this country in the PDF."
    ),
}

# ── Validatie ─────────────────────────────────────────────────────────────────

def validate(df: pd.DataFrame) -> bool:
    print("\n── Validatie ──────────────────────────────────────────────────────")
    ok = True

    # 1. Verplichte kolommen
    required = ["country_name", "country_code", "indicator_code",
                "indicator_label", "respondent_type", "value_pct",
                "global_avg_pct", "page_number", "extraction_note"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        print(f"  [FOUT] Ontbrekende kolommen: {missing_cols}")
        ok = False
    else:
        print("  [OK] Alle verplichte kolommen aanwezig")

    # 2. Geen echte nulls (alleen 'not in RM' is toegestaan)
    real_nulls = df[
        (df["value_pct"].isna()) &
        (~df["extraction_note"].fillna("").str.startswith("not in RM"))
    ]
    if len(real_nulls) > 0:
        print(f"  [FOUT] {len(real_nulls)} onverwachte null-waarden:")
        print(real_nulls[["country_name", "indicator_code"]].to_string(index=False))
        ok = False
    else:
        print("  [OK] Geen onverwachte null-waarden")

    # 3. Bereik 0–100
    out_of_range = df[
        (df["value_pct"].notna()) &
        ((df["value_pct"] < 0) | (df["value_pct"] > 100))
    ]
    if len(out_of_range) > 0:
        print(f"  [FOUT] {len(out_of_range)} waarden buiten bereik 0–100:")
        print(out_of_range[["country_name", "indicator_code", "value_pct"]].to_string(index=False))
        ok = False
    else:
        print("  [OK] Alle waarden binnen bereik 0–100")

    # 4. Geen duplicaten
    dupes = df.duplicated(subset=["country_code", "indicator_code"], keep=False)
    if dupes.sum() > 0:
        print(f"  [FOUT] {dupes.sum()} dubbele rijen:")
        print(df[dupes][["country_name", "indicator_code"]].to_string(index=False))
        ok = False
    else:
        print("  [OK] Geen duplicaten")

    # 5. Landen
    n = df["country_code"].nunique()
    print(f"  [INFO] {n} landen, {df['indicator_code'].nunique()} indicatoren, {len(df)} rijen totaal")

    return ok

# ── Laadlogica ────────────────────────────────────────────────────────────────

def load(df: pd.DataFrame, engine) -> None:
    print("\n── Laden ──────────────────────────────────────────────────────────")
    with engine.begin() as conn:

        # Stap 1: rw_source_metadata
        conn.execute(text("""
            INSERT INTO rw_source_metadata
                (source_code, source_name, edition, survey_year,
                 n_talent, n_employers, n_markets, publication_url, notes, loaded_at)
            VALUES
                (:source_code, :source_name, :edition, :survey_year,
                 :n_talent, :n_employers, :n_markets, :publication_url, :notes, NOW())
            ON CONFLICT (source_code) DO UPDATE
                SET loaded_at  = NOW(),
                    notes      = EXCLUDED.notes
        """), SOURCE_METADATA)
        print(f"  [OK] rw_source_metadata bijgewerkt")

        # Stap 2: verwijder bestaande rijen voor deze bron
        result = conn.execute(text(
            "DELETE FROM rw_market_indicators WHERE source_code = :sc"
        ), {"sc": SOURCE_CODE})
        print(f"  [OK] {result.rowcount} bestaande rijen verwijderd")

        # Stap 3: laad nieuwe rijen
        # Selecteer alleen de kolommen die in de tabel bestaan
        # (deviation_pp is een GENERATED kolom — nooit zelf invullen)
        DB_COLUMNS = [
            "source_id", "source_code", "country_name", "country_code",
            "indicator_code", "indicator_label", "respondent_type",
            "value_pct", "global_avg_pct",
            "page_number", "extraction_note", "loaded_at",
        ]

        load_df = df.copy()
        load_df["source_code"] = SOURCE_CODE
        load_df["loaded_at"]   = pd.Timestamp.now()

        # Haal source_id op
        source_id = conn.execute(
            text("SELECT id FROM rw_source_metadata WHERE source_code = :sc"),
            {"sc": SOURCE_CODE}
        ).scalar()
        load_df["source_id"] = source_id

        # Houd alleen de kolommen die in de tabel bestaan
        load_df = load_df[[c for c in DB_COLUMNS if c in load_df.columns]]

        load_df.to_sql(
            "rw_market_indicators",
            conn,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=500,
        )
        print(f"  [OK] {len(load_df)} rijen geladen in rw_market_indicators")

# ── Verificatie ───────────────────────────────────────────────────────────────

def verify(engine) -> None:
    print("\n── Verificatie ────────────────────────────────────────────────────")
    sc = SOURCE_CODE
    queries = {
        "Totaal rijen":
            f"SELECT COUNT(*) FROM rw_market_indicators WHERE source_code = '{sc}'",
        "Unieke landen":
            f"SELECT COUNT(DISTINCT country_code) FROM rw_market_indicators WHERE source_code = '{sc}'",
        "Unieke indicatoren":
            f"SELECT COUNT(DISTINCT indicator_code) FROM rw_market_indicators WHERE source_code = '{sc}'",
        "Rijen met waarde (niet null)":
            f"SELECT COUNT(*) FROM rw_market_indicators WHERE source_code = '{sc}' AND value_pct IS NOT NULL",
        "Rijen 'not in RM'":
            f"SELECT COUNT(*) FROM rw_market_indicators WHERE source_code = '{sc}' AND extraction_note LIKE 'not in RM%'",
        "Echte nulls (onverwacht)":
            f"SELECT COUNT(*) FROM rw_market_indicators WHERE source_code = '{sc}' AND value_pct IS NULL AND extraction_note NOT LIKE 'not in RM%'",
    }
    with engine.connect() as conn:
        for label, q in queries.items():
            result = conn.execute(text(q)).scalar()
            flag = " ← CONTROLEER" if label == "Echte nulls (onverwacht)" and result > 0 else ""
            print(f"  {label}: {result}{flag}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== load_randstad.py ===")

    # Laad CSV
    if not INPUT_PATH.exists():
        print(f"\n[FOUT] Bestand niet gevonden: {INPUT_PATH}")
        print("Voer eerst extract_randstad.py uit.")
        sys.exit(1)

    df = pd.read_csv(INPUT_PATH)
    print(f"CSV geladen: {len(df)} rijen")

    # Valideer
    if not validate(df):
        print("\n[GESTOPT] Validatie mislukt. Los de fouten op voor je laadt.")
        sys.exit(1)

    # DATABASE_URL check
    if not DATABASE_URL:
        print("\n[FOUT] DATABASE_URL niet ingesteld.")
        print("Voeg toe aan .env: DATABASE_URL=postgresql://...")
        sys.exit(1)

    # Verbinding
    print("\n── Verbinding ─────────────────────────────────────────────────────")
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("  [OK] Verbinding geslaagd")

    # Laad en verificeer
    load(df, engine)
    verify(engine)

    print("\n[KLAAR] Randstad Workmonitor 2026 succesvol geladen.")


if __name__ == "__main__":
    main()
