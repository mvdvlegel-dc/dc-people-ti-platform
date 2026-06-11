"""
validate_randstad.py
=====================
Valideert de geëxtraheerde Randstad Workmonitor 2026 CSV op 6 niveaus en
schrijft twee outputbestanden:

  validation_report.csv  — alle 6 checks met status, resultaat en toelichting
  validation_issues.csv  — alleen de issues (waarschuwingen en fouten)

Gebruik:
    python etl/validate_randstad.py

Invoer:
    data_processed/randstad_raw.csv

Uitvoer:
    data_processed/validation_report.csv
    data_processed/validation_issues.csv
"""

import pandas as pd
from pathlib import Path

CSV_PATH    = Path("data_processed/randstad_raw.csv")
REPORT_PATH = Path("data_processed/validation_report.csv")
ISSUES_PATH = Path("data_processed/validation_issues.csv")

# ── Configuratie ───────────────────────────────────────────────────────────────

EXPECTED_COUNTRIES = {
    "AU","AT","BE","BR","CA","CL","CN","CZ","DK","FR","DE","GR",
    "HK","HU","IN","IT","JP","LU","MY","MX","NL","NZ","NO","PL",
    "PT","RO","SG","ES","SE","CH","TR","GB","US","UY"
}

EXPECTED_INDICATORS = {
    "employer_confident_growth", "talent_optimism", "talent_second_job",
    "talent_ai_improves_productivity", "employer_ai_improves_productivity",
    "talent_confident_use_technology", "employer_ai_high_proportion_tasks",
    "talent_ai_high_proportion_tasks", "talent_ai_benefits_company_more",
    "talent_trust_leadership", "talent_trust_colleagues",
    "talent_strong_manager_relationship", "talent_manager_best_interests",
    "employer_remote_collaboration_challenging",
    "talent_rely_different_generations",
    "employer_generational_diversity_productivity",
    "employer_want_improve_collaboration",
    "talent_multigenerational_more_productive",
    "talent_want_linear_career", "talent_want_portfolio_career",
    "talent_pay_attracts", "talent_wlb_main_retention_reason",
    "talent_job_security_retention", "talent_pay_retention_reason",
    "talent_wlb_attracts", "employer_autonomy_engagement",
    "talent_quit_personal_life", "talent_left_lack_independence",
    "talent_no_location_flexibility", "talent_no_hours_flexibility",
}

KNOWN_NOT_IN_RM = {
    "talent_ai_high_proportion_tasks": 28,
    "talent_wlb_attracts": 33,
    "talent_pay_attracts": 3,
    "talent_wlb_main_retention_reason": 3,
    "talent_second_job": 3,
    "employer_want_improve_collaboration": 1,
}

CONSISTENCY_RULES = [
    ("talent_pay_attracts", ">", "talent_pay_retention_reason",
     "Pay attracts (attractie) zou hoger moeten zijn dan pay retention (retentie)"),
    ("talent_wlb_main_retention_reason", ">", "talent_pay_retention_reason",
     "WLB is primaire retentiereden, zou hoger moeten zijn dan pay retention"),
]

OUTLIER_THRESHOLD = 25

REQUIRED_COLS = [
    "country_name", "country_code", "indicator_code", "indicator_label",
    "respondent_type", "value_pct", "global_avg_pct",
    "page_number", "extraction_note"
]

# ── Hulpfuncties ───────────────────────────────────────────────────────────────

def separator(char="─", width=80):
    print(char * width)

def section(title):
    print(f"\n{'═' * 80}\n  {title}\n{'═' * 80}")

def ok(msg):   print(f"  ✓  {msg}")
def warn(msg): print(f"  ⚠  {msg}")
def err(msg):  print(f"  ✗  {msg}")

def add_report(report, check_nr, check_naam, status, resultaat, toelichting,
               country=None, indicator=None, value_pct=None,
               global_avg_pct=None, verschil_pp=None):
    """Voeg een rij toe aan het rapport."""
    report.append({
        "check_nr":       check_nr,
        "check_naam":     check_naam,
        "status":         status,          # OK / WAARSCHUWING / FOUT
        "resultaat":      resultaat,       # korte samenvatting
        "toelichting":    toelichting,     # detail
        "country":        country or "",
        "indicator":      indicator or "",
        "value_pct":      value_pct,
        "global_avg_pct": global_avg_pct,
        "verschil_pp":    verschil_pp or "",
    })

# ── Hoofdlogica ────────────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 80)
    print("  RANDSTAD WORKMONITOR 2026 — VALIDATIERAPPORT")
    print("═" * 80)

    if not CSV_PATH.exists():
        err(f"CSV niet gevonden: {CSV_PATH}")
        return

    df = pd.read_csv(CSV_PATH)
    report = []   # alle checks (ook ✓)
    issues = []   # alleen waarschuwingen en fouten

    # ──────────────────────────────────────────────────────────────────────────
    # CHECK 1 — STRUCTUUR
    # ──────────────────────────────────────────────────────────────────────────
    section("1. STRUCTUUR")

    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        msg = f"Ontbrekende kolommen: {missing_cols}"
        err(msg)
        add_report(report, 1, "Structuur — kolommen", "FOUT", msg, msg)
        issues.append({"check_nr": 1, "check_naam": "Structuur — kolommen",
                        "status": "FOUT", "toelichting": msg})
    else:
        msg = f"Alle {len(REQUIRED_COLS)} verplichte kolommen aanwezig"
        ok(msg)
        add_report(report, 1, "Structuur — kolommen", "OK", msg,
                   f"Kolommen: {', '.join(REQUIRED_COLS)}")

    ok(f"Totaal records: {len(df)}")
    add_report(report, 1, "Structuur — recordaantal", "OK",
               f"{len(df)} records", f"Verwacht: {len(EXPECTED_COUNTRIES) * len(EXPECTED_INDICATORS)}")

    type_ok = (pd.api.types.is_float_dtype(df["value_pct"]) and
               pd.api.types.is_float_dtype(df["global_avg_pct"]))
    if type_ok:
        ok("Datatypes correct (value_pct en global_avg_pct zijn float)")
        add_report(report, 1, "Structuur — datatypes", "OK",
                   "value_pct en global_avg_pct zijn float", "")
    else:
        warn("value_pct of global_avg_pct is geen float")
        add_report(report, 1, "Structuur — datatypes", "WAARSCHUWING",
                   "Datatype afwijking", "value_pct of global_avg_pct is geen float")
        issues.append({"check_nr": 1, "check_naam": "Structuur — datatypes",
                        "status": "WAARSCHUWING",
                        "toelichting": "value_pct of global_avg_pct is geen float"})

    # ──────────────────────────────────────────────────────────────────────────
    # CHECK 2 — VOLLEDIGHEID
    # ──────────────────────────────────────────────────────────────────────────
    section("2. VOLLEDIGHEID")

    # Landen
    found_countries = set(df["country_code"].unique())
    missing_countries = EXPECTED_COUNTRIES - found_countries
    extra_countries   = found_countries - EXPECTED_COUNTRIES

    if missing_countries:
        msg = f"Ontbrekende landen: {sorted(missing_countries)}"
        err(msg)
        add_report(report, 2, "Volledigheid — landen", "FOUT", msg, msg)
        issues.append({"check_nr": 2, "check_naam": "Volledigheid — landen",
                        "status": "FOUT", "toelichting": msg})
    else:
        ok("Alle 34 verwachte landen aanwezig")
        add_report(report, 2, "Volledigheid — landen", "OK",
                   "Alle 34 landen aanwezig", f"Landen: {sorted(found_countries)}")

    if extra_countries:
        msg = f"Onverwachte landcodes: {sorted(extra_countries)}"
        warn(msg)
        add_report(report, 2, "Volledigheid — extra landen", "WAARSCHUWING", msg, msg)
        issues.append({"check_nr": 2, "check_naam": "Volledigheid — extra landen",
                        "status": "WAARSCHUWING", "toelichting": msg})

    # Indicatoren
    found_indicators   = set(df["indicator_code"].unique())
    missing_indicators = EXPECTED_INDICATORS - found_indicators
    extra_indicators   = found_indicators - EXPECTED_INDICATORS

    if missing_indicators:
        msg = f"Ontbrekende indicatoren: {sorted(missing_indicators)}"
        err(msg)
        add_report(report, 2, "Volledigheid — indicatoren", "FOUT", msg, msg)
        issues.append({"check_nr": 2, "check_naam": "Volledigheid — indicatoren",
                        "status": "FOUT", "toelichting": msg})
    else:
        ok(f"Alle {len(EXPECTED_INDICATORS)} verwachte indicatoren aanwezig")
        add_report(report, 2, "Volledigheid — indicatoren", "OK",
                   f"Alle {len(EXPECTED_INDICATORS)} indicatoren aanwezig", "")

    # Dekking per indicator
    print()
    print(f"  {'indicator_code':<48} {'gevuld':>7}  {'not_in_rm':>10}  {'echte_null':>11}")
    separator()
    total_filled = total_not_rm = total_real_null = 0

    for code in sorted(EXPECTED_INDICATORS):
        sub      = df[df["indicator_code"] == code]
        filled   = sub["value_pct"].notna().sum()
        not_rm   = sub["extraction_note"].str.startswith("not in RM", na=False).sum()
        real_null = sub["value_pct"].isna().sum() - not_rm

        total_filled    += filled
        total_not_rm    += not_rm
        total_real_null += real_null

        expected_not_rm = KNOWN_NOT_IN_RM.get(code, 0)

        if real_null > 0:
            status_str = f"  ✗ {real_null} echte nulls"
            landen = sub[sub["value_pct"].isna() &
                         ~sub["extraction_note"].str.startswith("not in RM", na=False)
                         ]["country_code"].tolist()
            add_report(report, 2, f"Volledigheid — {code}", "FOUT",
                       f"{filled}/34 gevuld, {real_null} onverwachte nulls",
                       f"Ontbrekende landen: {landen}",
                       indicator=code)
            issues.append({"check_nr": 2, "check_naam": f"Volledigheid — {code}",
                            "status": "FOUT", "indicator": code,
                            "toelichting": f"{real_null} onverwachte nulls bij {landen}"})
        elif not_rm != expected_not_rm and not_rm > expected_not_rm:
            status_str = f"  ⚠ {not_rm} not in RM (verwacht: {expected_not_rm})"
            add_report(report, 2, f"Volledigheid — {code}", "WAARSCHUWING",
                       f"{filled}/34 gevuld, {not_rm} not in RM",
                       f"Meer not-in-RM dan verwacht (verwacht: {expected_not_rm})",
                       indicator=code)
            issues.append({"check_nr": 2, "check_naam": f"Volledigheid — {code}",
                            "status": "WAARSCHUWING", "indicator": code,
                            "toelichting": f"{not_rm} not in RM, verwacht {expected_not_rm}"})
        else:
            if not_rm > 0:
                status_str = f"  ✓ ({not_rm} not in RM — verwacht)"
                toel = f"{not_rm} not in RM — inhoudelijk verklaarbaar (zie KNOWN_NOT_IN_RM)"
            else:
                status_str = "  ✓"
                toel = "Volledig gevuld"
            add_report(report, 2, f"Volledigheid — {code}", "OK",
                       f"{filled}/34 gevuld", toel, indicator=code)

        print(f"  {code:<48} {filled:>5}/34  {not_rm:>10}  {real_null:>11}  {status_str}")

    separator()
    total = len(EXPECTED_INDICATORS) * 34
    print(f"  {'TOTAAL':<48} {total_filled:>5}/{total}  {total_not_rm:>10}  {total_real_null:>11}")
    print(f"\n  Dekking: {total_filled/total*100:.1f}%  |  not in RM: {total_not_rm}  |  echte nulls: {total_real_null}")

    add_report(report, 2, "Volledigheid — samenvatting", "OK",
               f"Dekking: {total_filled/total*100:.1f}% ({total_filled}/{total})",
               f"Not in RM: {total_not_rm} | Echte nulls: {total_real_null}")

    # ──────────────────────────────────────────────────────────────────────────
    # CHECK 3 — WAARDEBEREIK
    # ──────────────────────────────────────────────────────────────────────────
    section("3. WAARDEBEREIK (0–100%)")

    filled_df   = df[df["value_pct"].notna()]
    out_of_range = filled_df[(filled_df["value_pct"] < 0) | (filled_df["value_pct"] > 100)]

    if len(out_of_range) > 0:
        err(f"{len(out_of_range)} waarden buiten bereik 0–100")
        for _, row in out_of_range.iterrows():
            err(f"  {row['country_code']} / {row['indicator_code']}: {row['value_pct']}")
            add_report(report, 3, "Waardebereik — value_pct", "FOUT",
                       f"{row['value_pct']} buiten bereik 0-100",
                       "Waarde moet tussen 0 en 100 liggen",
                       country=row["country_code"], indicator=row["indicator_code"],
                       value_pct=row["value_pct"])
            issues.append({"check_nr": 3, "check_naam": "Waardebereik — value_pct",
                            "status": "FOUT", "country": row["country_code"],
                            "indicator": row["indicator_code"],
                            "toelichting": f"Waarde {row['value_pct']} buiten bereik 0-100"})
    else:
        msg = f"Alle {len(filled_df)} gevulde waarden liggen tussen 0 en 100"
        ok(msg)
        add_report(report, 3, "Waardebereik — value_pct", "OK", msg, "")

    ga_out = df[(df["global_avg_pct"].notna()) &
                ((df["global_avg_pct"] < 0) | (df["global_avg_pct"] > 100))]
    if len(ga_out) > 0:
        err(f"{len(ga_out)} global_avg_pct waarden buiten bereik")
        add_report(report, 3, "Waardebereik — global_avg_pct", "FOUT",
                   f"{len(ga_out)} waarden buiten bereik", "")
        issues.append({"check_nr": 3, "check_naam": "Waardebereik — global_avg_pct",
                        "status": "FOUT",
                        "toelichting": f"{len(ga_out)} global_avg_pct buiten bereik 0-100"})
    else:
        ok("Alle global_avg_pct waarden liggen tussen 0 en 100")
        add_report(report, 3, "Waardebereik — global_avg_pct", "OK",
                   "Alle global_avg_pct waarden liggen tussen 0 en 100", "")

    # ──────────────────────────────────────────────────────────────────────────
    # CHECK 4 — DUPLICATEN
    # ──────────────────────────────────────────────────────────────────────────
    section("4. DUPLICATEN")

    dupes = df[df.duplicated(subset=["country_code", "indicator_code"], keep=False)]
    if len(dupes) > 0:
        err(f"{len(dupes)} dubbele land-indicator combinaties")
        for (cc, ind), grp in dupes.groupby(["country_code", "indicator_code"]):
            err(f"  {cc} / {ind}: {len(grp)} keer")
            add_report(report, 4, "Duplicaten", "FOUT",
                       f"{cc} / {ind}: {len(grp)} keer",
                       "Dubbele rij voor dezelfde land-indicator combinatie",
                       country=cc, indicator=ind)
            issues.append({"check_nr": 4, "check_naam": "Duplicaten",
                            "status": "FOUT", "country": cc, "indicator": ind,
                            "toelichting": f"{len(grp)} dubbele rijen"})
    else:
        msg = f"Geen duplicaten — alle {len(df)} land-indicator combinaties uniek"
        ok(msg)
        add_report(report, 4, "Duplicaten", "OK", msg, "")

    # ──────────────────────────────────────────────────────────────────────────
    # CHECK 5 — CONSISTENTIE
    # ──────────────────────────────────────────────────────────────────────────
    section("5. CONSISTENTIE (logische relaties)")

    pivot = df[df["value_pct"].notna()].pivot_table(
        index="country_code", columns="indicator_code", values="value_pct"
    )

    for ind_a, op, ind_b, desc in CONSISTENCY_RULES:
        if ind_a not in pivot.columns or ind_b not in pivot.columns:
            warn(f"Kan niet controleren: {ind_a} of {ind_b} ontbreekt in pivot")
            add_report(report, 5, f"Consistentie — {ind_a} vs {ind_b}", "WAARSCHUWING",
                       "Kan niet controleren", f"{ind_a} of {ind_b} ontbreekt")
            continue

        compare    = pivot[[ind_a, ind_b]].dropna()
        violations = compare[compare[ind_a] <= compare[ind_b]] if op == ">" else \
                     compare[compare[ind_a] >= compare[ind_b]] if op == "<" else \
                     pd.DataFrame()

        if len(violations) > 0:
            warn(f"{desc}")
            warn(f"  {len(violations)} landen schenden deze regel:")
            for cc, row in violations.iterrows():
                warn(f"  {cc}: {ind_a}={row[ind_a]:.0f}% vs {ind_b}={row[ind_b]:.0f}%")
                add_report(report, 5, f"Consistentie — {ind_a} vs {ind_b}", "WAARSCHUWING",
                           f"{cc}: {ind_a}={row[ind_a]:.0f}% ≤ {ind_b}={row[ind_b]:.0f}%",
                           desc, country=cc,
                           indicator=f"{ind_a} vs {ind_b}",
                           value_pct=row[ind_a], global_avg_pct=row[ind_b])
                issues.append({"check_nr": 5,
                                "check_naam": f"Consistentie — {ind_a} vs {ind_b}",
                                "status": "WAARSCHUWING", "country": cc,
                                "indicator": f"{ind_a} vs {ind_b}",
                                "toelichting": f"{ind_a}={row[ind_a]:.0f}% ≤ {ind_b}={row[ind_b]:.0f}%"})
        else:
            ok(f"{desc} — geen schendingen")
            add_report(report, 5, f"Consistentie — {ind_a} vs {ind_b}", "OK",
                       "Geen schendingen", desc)

    # ──────────────────────────────────────────────────────────────────────────
    # CHECK 6 — UITSCHIETERS
    # ──────────────────────────────────────────────────────────────────────────
    section(f"6. UITSCHIETERS (afwijking > {OUTLIER_THRESHOLD}pp van global benchmark)")

    outliers = filled_df.copy()
    outliers["diff"] = (outliers["value_pct"] - outliers["global_avg_pct"]).abs()
    outliers = outliers[outliers["diff"] > OUTLIER_THRESHOLD].sort_values("diff", ascending=False)

    if len(outliers) == 0:
        msg = f"Geen uitschieters gevonden (drempel: {OUTLIER_THRESHOLD}pp)"
        ok(msg)
        add_report(report, 6, "Uitschieters", "OK", msg, "")
    else:
        warn(f"{len(outliers)} uitschieters (afwijking > {OUTLIER_THRESHOLD}pp van global avg):")
        print()
        print(f"  {'land':<6} {'indicator_code':<46} {'waarde':>7}  {'global':>7}  {'verschil':>9}")
        separator()
        for _, row in outliers.iterrows():
            direction = "↑" if row["value_pct"] > row["global_avg_pct"] else "↓"
            diff_pp   = row["diff"]
            print(f"  {row['country_code']:<6} {row['indicator_code']:<46} "
                  f"{row['value_pct']:>6.0f}%  {row['global_avg_pct']:>6.0f}%  "
                  f"{direction}{diff_pp:>7.0f}pp")
            add_report(report, 6, "Uitschieters", "WAARSCHUWING",
                       f"{row['country_code']}: {direction}{diff_pp:.0f}pp afwijking",
                       f"Controleer handmatig in het PDF",
                       country=row["country_code"],
                       indicator=row["indicator_code"],
                       value_pct=row["value_pct"],
                       global_avg_pct=row["global_avg_pct"],
                       verschil_pp=f"{direction}{diff_pp:.0f}pp")
            issues.append({"check_nr": 6, "check_naam": "Uitschieters",
                            "status": "WAARSCHUWING",
                            "country": row["country_code"],
                            "indicator": row["indicator_code"],
                            "value_pct": row["value_pct"],
                            "global_avg_pct": row["global_avg_pct"],
                            "verschil_pp": f"{direction}{diff_pp:.0f}pp",
                            "toelichting": f"Afwijking {direction}{diff_pp:.0f}pp van global benchmark"})

    # ──────────────────────────────────────────────────────────────────────────
    # SAMENVATTING
    # ──────────────────────────────────────────────────────────────────────────
    section("SAMENVATTING")

    blocking = [i for i in issues if i["status"] == "FOUT"]

    if len(blocking) == 0:
        ok("Geen blokkerende issues gevonden — data is klaar voor laden")
    else:
        err(f"{len(blocking)} blokkerende issues — los deze op voor het laden")

    n_warn = len([i for i in issues if i["status"] == "WAARSCHUWING"])
    if n_warn > 0:
        warn(f"{n_warn} waarschuwingen — controleer handmatig")
    else:
        ok("Geen waarschuwingen")

    print(f"\n  Dekking:        {total_filled}/{total} ({total_filled/total*100:.1f}%)")
    print(f"  Not in RM:      {total_not_rm} (inhoudelijk verklaarbaar)")
    print(f"  Echte nulls:    {total_real_null}")
    print(f"  Duplicaten:     {len(dupes)}")
    print(f"  Uitschieters:   {len(outliers)}")
    print(f"  Fouten:         {len(blocking)}")
    print(f"  Waarschuwingen: {n_warn}")

    # ── Opslaan ───────────────────────────────────────────────────────────────
    report_df = pd.DataFrame(report)
    report_df.to_csv(REPORT_PATH, index=False)
    print(f"\n  Volledig rapport:  {REPORT_PATH}  ({len(report_df)} rijen)")

    if issues:
        issues_df = pd.DataFrame(issues)
        issues_df.to_csv(ISSUES_PATH, index=False)
        print(f"  Issues (fouten + waarschuwingen): {ISSUES_PATH}  ({len(issues_df)} rijen)")
    else:
        ok(f"Geen issues — {ISSUES_PATH} niet aangemaakt")

    print()


if __name__ == "__main__":
    main()
