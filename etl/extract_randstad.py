"""
extract_randstad.py
====================
Extraheert alle beschikbare indicatoren uit het Randstad Workmonitor 2026 PDF
en schrijft het resultaat naar data_processed/randstad_raw.csv.

De market snapshot pagina's hebben een 3-kolomsindeling:
  - Kolom 1 (x < 480):  "Me and the world"
  - Kolom 2 (x 480-960): navigatiebalk + "Me and my team"
  - Kolom 3 (x > 960):  "Me: the rise of self-defined success"

De tekst wordt per kolom geëxtraheerd en samengevoegd om kolom-interferentie
te voorkomen.

Gebruik:
    python etl/extract_randstad.py

Vereisten:
    pip install pdfplumber pandas

Invoer:
    data_raw/Randstad_Workmonitor_2026.pdf

Uitvoer:
    data_processed/randstad_raw.csv
"""

import re
import pdfplumber
import pandas as pd
from pathlib import Path

# ── Paden ──────────────────────────────────────────────────────────────────────
PDF_PATH = Path("data_raw/Randstad_Workmonitor_2026.pdf")
OUT_PATH = Path("data_processed/randstad_raw.csv")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Landpagina's (paginanummer in PDF, 1-gebaseerd) ───────────────────────────
COUNTRY_PAGES = {
    "Australia":       36, "Austria":        37, "Belgium":         38,
    "Brazil":          39, "Canada":          40, "Chile":           41,
    "China":           42, "Czech Republic":  43, "Denmark":         44,
    "France":          45, "Germany":         46, "Greece":          47,
    "Hong Kong Sar":   48, "Hungary":         49, "India":           50,
    "Italy":           51, "Japan":           52, "Luxembourg":      53,
    "Malaysia":        54, "Mexico":          55, "Netherlands":     56,
    "New Zealand":     57, "Norway":          58, "Poland":          59,
    "Portugal":        60, "Romania":         61, "Singapore":       62,
    "Spain":           63, "Sweden":          64, "Switzerland":     65,
    "Türkiye":         66, "United Kingdom":  67, "United States":   68,
    "Uruguay":         69,
}

COUNTRY_CODES = {
    "Australia": "AU", "Austria": "AT", "Belgium": "BE", "Brazil": "BR",
    "Canada": "CA", "Chile": "CL", "China": "CN", "Czech Republic": "CZ",
    "Denmark": "DK", "France": "FR", "Germany": "DE", "Greece": "GR",
    "Hong Kong Sar": "HK", "Hungary": "HU", "India": "IN", "Italy": "IT",
    "Japan": "JP", "Luxembourg": "LU", "Malaysia": "MY", "Mexico": "MX",
    "Netherlands": "NL", "New Zealand": "NZ", "Norway": "NO", "Poland": "PL",
    "Portugal": "PT", "Romania": "RO", "Singapore": "SG", "Spain": "ES",
    "Sweden": "SE", "Switzerland": "CH", "Türkiye": "TR",
    "United Kingdom": "GB", "United States": "US", "Uruguay": "UY",
}

# ── Kolomgrenzen (x-coördinaten in punten op een 1440pt brede pagina) ─────────
# Kolom 1: Me and the world       → x < 480
# Kolom 2: Me and my team         → 480 ≤ x < 960  (bevat ook navigatiebalk)
# Kolom 3: Self-defined success   → x ≥ 960
COL1_MAX = 480
COL2_MAX = 960

# ── Indicatordefinities ────────────────────────────────────────────────────────
# Formaat: (code, label, respondent_type, global_avg, kolom, [patronen])
# kolom: 1, 2, 3, of 'all' (zoek in volledige tekst)
# Patronen: eerste match wint; groep 1 = het landspecifieke percentage.

INDICATORS = [

    # ── Me and the world (kolom 1 + kolom 2 bevat ook col1-data) ─────────────
    (
        "employer_confident_growth",
        "Employers confident of growing next year",
        "employer", 95.0, 1,
        [
            r"(\d{1,3})% of employers are confident of growing",
            r"All employers \((\d{1,3})%\) are confident",
            r"All employers surveyed \((\d{1,3})%\)",
        ]
    ),
    (
        "talent_optimism",
        "Talent share optimism about business outlook",
        "talent", 51.0, 1,
        [
            r"(\d{1,3})% of talent surveyed share their optimism",
            r"Only (\d{1,3})% of talent (?:surveyed )?share their optimism",
            r"(\d{1,3})% of talent share their optimism",
            # Fallback: 'optimism, slightly less/more than the global average (51%)' → percentage staat vóór 'optimism'
            r"(\d{1,3})%[^.]*their optimism",
            r"(\d{1,3})%[^.]*share[^.]*optimism",
        ]
    ),
    (
        "talent_second_job",
        "Talent taking on or looking for a second job",
        "talent", 40.0, 2,
        [
            # Patroon: "36% of the rising cost of living, 36% of ... they have taken on or are looking ... a second job, compared to the ... of 40%"
            # Het percentage staat VOOR 'they have taken on'
            r"(\d{1,3})% of (?:the rising cost|talent)[^.]*taken on or are looking[^.]*a second job",
            r"(\d{1,3})%[^.]*taken on or are looking[^.]*a second job",
        ]
    ),
    (
        "talent_ai_improves_productivity",
        "Talent feel AI helps improve productivity",
        "talent", 62.0, 1,
        [
            r"(\d{1,3})% of talent feel that AI helps improve",
        ]
    ),
    (
        "employer_ai_improves_productivity",
        "Employers feel AI helps improve productivity",
        "employer", 54.0, 2,
        [
            r"as do (\d{1,3})% of (?:employers|productivity)[^)]*\(global: 54%\)",
            r"as do (\d{1,3})%",
            r"(\d{1,3})% of employers \(global: 54%\)",
        ]
    ),
    (
        "talent_confident_use_technology",
        "Talent feel confident using latest technology",
        "talent", 69.0, 1,
        [
            r"(\d{1,3})% of talent feel confident that they can",
        ]
    ),
    (
        "employer_ai_high_proportion_tasks",
        "Employers estimate AI will impact high proportion of tasks (50-100%)",
        "employer", 68.0, 1,
        [
            r"(\d{1,3})% of employers estimate AI will impact a high proportion",
            r"(\d{1,3})% of employers (?:say|estimate|feel) (?:that )?AI will impact",
        ]
    ),
    (
        "talent_ai_high_proportion_tasks",
        "Talent agree AI will impact high proportion of tasks (50-100%)",
        "talent", 52.0, 1,
        [
            r"with (\d{1,3})% of talent agreeing \(global: 58% vs\. 52%\)",
            r"(\d{1,3})% of talent agreeing \(global: 58%",
        ]
    ),
    (
        "talent_ai_benefits_company_more",
        "Talent believe AI adoption will mainly benefit companies, not them",
        "talent", 47.0, 2,
        [
            r"(\d{1,3})% of talent believe the adoption of AI in the workplace will mainly benefit companies",
            r"(\d{1,3})% of talent believe (?:that )?(?:the )?adoption of AI will mainly benefit companies",
            r"(\d{1,3})% of talent believe the adoption of AI",
            r"(\d{1,3})%[^.]*mainly benefit companies",
            r"(\d{1,3})%[^.]*mainly benefit[^.]*not them",
        ]
    ),

    # ── Me and my team (kolom 2) ──────────────────────────────────────────────
    (
        "talent_trust_leadership",
        "Talent trust the leadership of their company",
        "talent", 72.0, 2,
        [
            r"(\d{1,3})% of talent trust the leadership of",
            r"(\d{1,3})% of talent trust the leadership",
        ]
    ),
    (
        "talent_trust_colleagues",
        "Talent trust their colleagues",
        "talent", 76.0, 2,
        [
            r"(\d{1,3})% say that they trust their colleagues",
            r"(\d{1,3})% trust their colleagues",
        ]
    ),
    (
        "talent_strong_manager_relationship",
        "Talent say they have a strong relationship with their manager",
        "talent", 72.0, 2,
        [
            r"(\d{1,3})% of talent say they have a strong",
        ]
    ),
    (
        "talent_manager_best_interests",
        "Talent believe their manager has their best interests in mind",
        "talent", 71.0, 2,
        [
            r"(\d{1,3})% believe their manager has their best",
            r"(\d{1,3})% of talent believe their manager has their best",
        ]
    ),
    (
        "employer_remote_collaboration_challenging",
        "Employers say remote/hybrid work has made collaboration more challenging",
        "employer", 81.0, 2,
        [
            r"(\d{1,3})% of employers say that remote (?:or hybrid )?work has made collaboration",
            r"(\d{1,3})% (?:of employers say (?:that )?)?(?:remote|hybrid) (?:or hybrid )?work has made collaboration",
            r"(\d{1,3})%[^.]*hybrid work has made collaboration",
            r"(\d{1,3})%[^.]*remote[^.]*collaboration[^.]*challenging",
        ]
    ),
    (
        "talent_rely_different_generations",
        "Talent rely on people from different generations to broaden perspectives",
        "talent", 74.0, 2,
        [
            r"(\d{1,3})% of talent say they rely on people from",
            r"(\d{1,3})% of talent (?:say they )?rely on (?:people from )?different generations",
            # Patroon: 'from different generations to broaden ... their perspectives (global: 74%)' → % staat ervoor
            r"(\d{1,3})%[^.]*from different generations to broaden",
            r"(\d{1,3})%[^.]*different generations to broaden[^.]*perspectives",
        ]
    ),
    (
        "employer_generational_diversity_productivity",
        "Employers highlight generational diversity as a productivity lever",
        "employer", 95.0, 2,
        [
            r"(?:Almost all )?(?:All )?employers \((\d{1,3})%\) surveyed highlight generational diversity",
            r"(\d{1,3})% of employers (?:surveyed )?highlight generational diversity",
            r"All employers \((\d{1,3})%\) surveyed highlight",
            r"All employers surveyed \((\d{1,3})%\) highlight",
            # Patroon: 'surveyed ○ highlight generational diversity as productivity lever (global: 95%)'
            # Het percentage staat in 'All employers (XX%) surveyed' of 'Almost all employers (XX%)'
            r"(?:Almost all|All) employers \((\d{1,3})%\)",
            r"employers \((\d{1,3})%\)[^.]*highlight generational",
            r"employers \((\d{1,3})%\)[^.]*generational diversity",
            r"(\d{1,3})%[^.]*highlight[^.]*generational diversity",
        ]
    ),
    (
        "employer_want_improve_collaboration",
        "Employers want management to spend more time improving team collaboration",
        "employer", 90.0, 2,
        [
            r"(\d{1,3})% want to see management spend more time improving team collaboration",
            r"(\d{1,3})% want (?:to see )?management (?:to )?spend more time improving",
            # Patroon: 'and XX% want management spend more time improving team collaboration (global: 90%)'
            r"(\d{1,3})% want management spend more time",
            r"and (\d{1,3})% want (?:to see )?management",
            r"(\d{1,3})%[^.]*want[^.]*management[^.]*spend more time",
        ]
    ),
    (
        "talent_multigenerational_more_productive",
        "Talent believe they are more productive when collaborating across generations",
        "talent", 78.0, 2,
        [
            r"(\d{1,3})% of talent believe th(?:at|em) (?:that )?they are (?:more )?productive when collaborating",
            r"(\d{1,3})% of talent believe th",
            r"(\d{1,3})%[^.]*productive when collaborat",
        ]
    ),

    # ── Me: self-defined success (kolom 3) ────────────────────────────────────
    (
        "talent_want_linear_career",
        "Talent want to follow a traditional, linear career path",
        "talent", 41.0, 3,
        [
            r"(\d{1,3})% of talent say they want to follow a traditional",
            r"(\d{1,3})% of talent (?:say they )?want to follow a (?:traditional )?linear career",
        ]
    ),
    (
        "talent_want_portfolio_career",
        "Talent want to have a portfolio career (switching sectors and jobs)",
        "talent", 38.0, 3,
        [
            r"but (\d{1,3})% say they want to have a portfolio career",
            r"but (\d{1,3})% want to have a portfolio career",
            r"linear career path \(global: 41%\),? but (\d{1,3})%",
            r"but (\d{1,3})% (?:say they want|want) to have a portfolio",
        ]
    ),
    (
        "talent_pay_attracts",
        "Pay attracts talent (primary attraction driver)",
        "talent", 81.0, 3,
        [
            r"While pay attracts talent \((\d{1,3})% vs\.",
            r"pay attracts talent \((\d{1,3})% vs\.",
        ]
        # NB: LU/NL/TR → 'not in RM', WLB is trekker
    ),
    (
        "talent_wlb_main_retention_reason",
        "Work-life balance is main reason for staying in current role",
        "talent", 46.0, 3,
        [
            r"work.life balance \((\d{1,3})% vs\. 46% globally\) is the main reason for staying",
            r"work.life balance \((\d{1,3})% vs\. 46%\)",
            r"the same consideration is (?:the )?(?:also )?the main reason for staying \((\d{1,3})% vs\. 46%",
            r"the same consideration is the main reason for staying in the current role \((\d{1,3})%",
            r"the same consideration is the main reason for staying \((\d{1,3})%",
            # Patroon AT/DE/HU: 'job security (23% globally) is the main reason for staying ... topping work-life balance (36%; global: 46%)'
            # WLB staat als TWEEDE reden met (XX%; global: 46%)
            r"work.life balance \((\d{1,3})%; global: 46%\)",
            r"topping (?:best )?work.life balance \((\d{1,3})%",
            r"topping work.life balance \((\d{1,3})%",
        ]
    ),
    (
        "talent_job_security_retention",
        "Job security as reason for staying in current role",
        "talent", 23.0, 3,
        [
            r"topping job security \((\d{1,3})%; global: 23%\)",
            r"job security \((\d{1,3})% vs\. 23% globally\) is the main reason",
            r"and job security \((\d{1,3})%; global: 23%\)",
            r"job security \((\d{1,3})%; global",
        ]
    ),
    (
        "talent_pay_retention_reason",
        "Pay/benefits as reason for staying in current role",
        "talent", 23.0, 3,
        [
            r"topping work.life balance[^)]+\) and pay/benefits \((\d{1,3})%",
            r"topping job security[^)]+\) and pay/benefits \((\d{1,3})%",
            r"and pay/benefits \((\d{1,3})%; global",
            r"topping pay/benefits \((\d{1,3})%",
            r"pay/benefits \((\d{1,3})%; global: 23%\)",
            r"security \(\d{1,3}%; global: 23%\) and pay/benefits \((\d{1,3})%",
            # Patroon HU: 'pay/benefits (41% vs. 23% globally) is the main reason for staying'
            r"pay/benefits \((\d{1,3})% vs\. 23% globally\) is the main reason",
            r"pay/benefits \((\d{1,3})% vs\. 23%",
        ]
    ),
    (
        "talent_wlb_attracts",
        "Work-life balance attracts talent (primary attraction driver, NL/LU/TR only)",
        "talent", 78.0, 3,
        [
            r"While work.life balance attracts talent \((\d{1,3})% vs\. 78%",
            r"work.life balance attracts talent \((\d{1,3})% vs\. 78%",
        ]
    ),
    (
        "employer_autonomy_engagement",
        "Employers agree greater autonomy leads to higher engagement, productivity and retention",
        "employer", 72.0, 3,
        [
            r"(\d{1,3})% of employers agree that greater autonomy leads to higher engagement",
            r"(\d{1,3})% of employers (?:agree|say) (?:that )?greater autonomy leads",
        ]
    ),
    (
        "talent_quit_personal_life",
        "Talent quit jobs that didn't fit their personal lives",
        "talent", 39.0, 3,
        [
            r"(\d{1,3})% of talent still say they quit jobs that didn.t (?:or )?fit their personal lives",
            r"(\d{1,3})% of talent (?:still )?say they quit jobs that didn.t (?:or )?fit",
            r"(\d{1,3})%[^.]*quit jobs[^.]*personal lives",
        ]
    ),
    (
        "talent_left_lack_independence",
        "Talent left because they weren't given enough independence",
        "talent", 25.0, 3,
        [
            r"(\d{1,3})% left because they weren.t given enough independence",
            r"(\d{1,3})% (?:of talent )?left (?:because they )?(?:weren.t|lacked) (?:given enough )?independence",
            # Patroon BR/CN/DK: 'weren't given enough from independence to work on their own terms'
            # Het percentage staat vóór 'left' maar 'from' staat ertussen
            r"(\d{1,3})%[^.]*left[^.]*(?:given enough|weren.t given)[^.]*independence",
            r"(\d{1,3})%[^.]*weren.t given[^.]*independence",
            r"(\d{1,3})%[^.]*given enough[^.]*independence",
        ]
    ),
    (
        "talent_no_location_flexibility",
        "Talent would not accept a new job without work location flexibility",
        "talent", 43.0, 3,
        [
            r"(\d{1,3})% of talent would not consider accepting (?:○ )?a new job",
            r"(\d{1,3})% would not consider accepting (?:○ )?a new job",
            r"(\d{1,3})%[^.]*would not consider accepting[^.]*work location",
        ]
    ),
    (
        "talent_no_hours_flexibility",
        "Talent would not accept a role without working hours flexibility",
        "talent", 43.0, 3,
        [
            r"(\d{1,3})% would not accept (?:○ )?(?:a )?(?:new )?role without working hours",
            r"(\d{1,3})%[^.]*would not accept[^.]*working hours flexibility",
            r"and (\d{1,3})% would not accept",
        ]
    ),
]


# ── Hulpfuncties ───────────────────────────────────────────────────────────────

def extract_column_text(page, col: int) -> str:
    """
    Extraheer tekst uit een specifieke kolom van de pagina op basis van x-coördinaten.
    Kolom 1: x < COL1_MAX
    Kolom 2: COL1_MAX ≤ x < COL2_MAX
    Kolom 3: x ≥ COL2_MAX
    """
    words = page.extract_words()
    if col == 1:
        filtered = [w for w in words if w['x0'] < COL1_MAX]
    elif col == 2:
        filtered = [w for w in words if COL1_MAX <= w['x0'] < COL2_MAX]
    else:
        filtered = [w for w in words if w['x0'] >= COL2_MAX]

    # Sorteer op y (top-to-bottom), dan x (left-to-right)
    filtered.sort(key=lambda w: (round(w['top'] / 5) * 5, w['x0']))
    text = ' '.join(w['text'] for w in filtered)
    return normalize_text(text)


def normalize_text(text: str) -> str:
    """Normaliseer PDF-tekst: apostrofs, regelafbrekingen, pay/ splits."""
    text = text.replace('\u2019', "'").replace('\u2018', "'")
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    text = re.sub(r'pay/\s+benefits', 'pay/benefits', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_value(text: str, patterns: list):
    """Probeer elk patroon en geef de eerste match terug als float."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = next((g for g in m.groups() if g is not None), None)
            if val is not None:
                return float(val)
    return None


# ── Hoofdlogica ────────────────────────────────────────────────────────────────

def main():
    print(f"PDF: {PDF_PATH}")
    print(f"Landen: {len(COUNTRY_PAGES)}")
    print(f"Indicatoren: {len(INDICATORS)}\n")

    rows = []

    with pdfplumber.open(PDF_PATH) as pdf:
        for country, page_num in COUNTRY_PAGES.items():
            page = pdf.pages[page_num - 1]
            cc = COUNTRY_CODES[country]

            # Extraheer tekst per kolom
            col_texts = {
                1: extract_column_text(page, 1),
                2: extract_column_text(page, 2),
                3: extract_column_text(page, 3),
            }
            # 'all' = volledige genormaliseerde tekst (fallback)
            full_text = normalize_text(page.extract_text() or "")
            full_text = re.sub(r'pay/\s+benefits', 'pay/benefits', full_text, flags=re.IGNORECASE)

            for (code, label, resp_type, global_avg, col, patterns) in INDICATORS:
                search_text = col_texts.get(col, full_text)
                value = extract_value(search_text, patterns)

                # Fallback: zoek ook in de volledige tekst als kolom geen match geeft
                if value is None:
                    value = extract_value(full_text, patterns)

                # Speciale regels
                note = ""
                if code == "talent_pay_attracts" and cc in ("NL", "LU", "TR"):
                    value = None
                    note = "not in RM — WLB is primary attraction driver for this country"
                elif code == "talent_wlb_attracts" and cc not in ("NL", "LU", "TR"):
                    value = None
                    note = "not in RM — pay is primary attraction driver for this country"
                elif value is None:
                    note = "not in RM"

                rows.append({
                    "country_name":    country,
                    "country_code":    cc,
                    "indicator_code":  code,
                    "indicator_label": label,
                    "respondent_type": resp_type,
                    "value_pct":       value,
                    "global_avg_pct":  global_avg,
                    "page_number":     page_num,
                    "extraction_note": note,
                })

    df = pd.DataFrame(rows)
    df = df.sort_values(["country_name", "indicator_code"]).reset_index(drop=True)

    # ── Samenvatting ──────────────────────────────────────────────────────────
    print(f"{'indicator_code':<48} {'gevuld':>7}  {'not_in_rm':>10}  status")
    print("-" * 85)
    for code, *_ in INDICATORS:
        sub    = df[df["indicator_code"] == code]
        filled = sub["value_pct"].notna().sum()
        not_rm = sub["extraction_note"].str.startswith("not in RM").sum()
        if filled == 34:
            status = "✓ VOLLEDIG"
        elif filled > 0:
            status = f"⚠  {34-filled} ontbreekt"
        else:
            status = "✗ LEEG"
        print(f"  {code:<46} {filled:>5}/34  {not_rm:>10}  {status}")

    total     = len(df)
    filled    = df["value_pct"].notna().sum()
    not_rm    = df["extraction_note"].str.startswith("not in RM").sum()
    real_null = df["value_pct"].isna().sum() - not_rm

    print(f"\nTotaal records:           {total}")
    print(f"Gevuld:                   {filled} ({filled/total*100:.1f}%)")
    print(f"'not in RM':              {not_rm}")
    print(f"Echte nulls (onverwacht): {real_null}")

    df.to_csv(OUT_PATH, index=False)
    print(f"\nOpgeslagen: {OUT_PATH}")


if __name__ == "__main__":
    main()
