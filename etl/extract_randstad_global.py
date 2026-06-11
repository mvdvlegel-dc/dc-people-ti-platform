"""
extract_randstad_global.py
===========================
Extraheert globale thema-indicatoren uit het Randstad Workmonitor 2026 PDF
en slaat ze op als data_processed/randstad_global.csv.

Structuur output (past op rw_global_indicators):
  theme | indicator_code | indicator_label | respondent_type | value_pct | year_prev_pct | notes

Gebruik:
    python etl/extract_randstad_global.py

Vereisten:
    pip install pdfplumber pandas
"""

import re
import pandas as pd
from pathlib import Path

PDF_PATH    = Path("data_raw/Randstad_Workmonitor_2026.pdf")
OUTPUT_PATH = Path("data_processed/randstad_global.csv")

# ── Statische dataset ─────────────────────────────────────────────────────────
# De globale indicatoren zijn verspreid over pagina's 3-30 in de tekst en
# grafieken. Hieronder zijn alle extraheerbare cijfers opgenomen, inclusief
# de pagina en de exacte bronzin als verificatie.
#
# Kolommen: theme | indicator_code | indicator_label | respondent_type
#           | value_pct | year_prev_pct | notes
#
# year_prev_pct = waarde 2025 indien vermeld in het rapport (voor change_pp)

GLOBAL_INDICATORS = [

    # ── THEME 1: Me and the world ─────────────────────────────────────────────

    {
        "theme": "me_and_the_world",
        "indicator_code": "global_employer_confident_growth",
        "indicator_label": "Employers confident their business will grow next year",
        "respondent_type": "employer",
        "value_pct": 95.0,
        "year_prev_pct": None,
        "notes": "p.3 foreword: '95% of employers believe they will grow over the next year'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_optimism_growth",
        "indicator_label": "Talent confident their employer will grow next year",
        "respondent_type": "talent",
        "value_pct": 51.0,
        "year_prev_pct": None,
        "notes": "p.3 foreword: 'only 51% of talent share that optimism'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_second_job",
        "indicator_label": "Talent who have taken on (or are looking at) a second job",
        "respondent_type": "talent",
        "value_pct": 40.0,
        "year_prev_pct": 22.0,
        "notes": "p.11: '40% of talent state they have taken on, or are looking at taking on, a second job. This is nearly twice as many as in 2024 (22%)'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_increased_hours",
        "indicator_label": "Talent who have increased or plan to increase working hours",
        "respondent_type": "talent",
        "value_pct": 36.0,
        "year_prev_pct": 20.0,
        "notes": "p.11: '36% have increased or plan to increase their hours in their current job, up from 20% in 2024'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_worried_job_security",
        "indicator_label": "Talent worried about impact of economic uncertainty on job security",
        "respondent_type": "talent",
        "value_pct": 46.0,
        "year_prev_pct": None,
        "notes": "p.11: 'Close to half worry about the impact of economic uncertainty on their job security (46%)'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_employer_invested_ai",
        "indicator_label": "Employers who have invested in AI in the last 12 months",
        "respondent_type": "employer",
        "value_pct": 63.0,
        "year_prev_pct": None,
        "notes": "p.5/12/14: 'nearly two-thirds of employers state that they have invested in AI in the last 12 months'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_ai_investment_increased",
        "indicator_label": "Talent who say their company's overall investment in AI has increased",
        "respondent_type": "talent",
        "value_pct": 34.0,
        "year_prev_pct": None,
        "notes": "p.5/14: '34% of talent say their company's overall investment in AI has increased'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_ai_improves_productivity",
        "indicator_label": "Talent who say AI makes them more productive at work",
        "respondent_type": "talent",
        "value_pct": 62.0,
        "year_prev_pct": None,
        "notes": "p.12/14: '62% — AI makes me more productive at work'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_employer_ai_improves_productivity",
        "indicator_label": "Employers who say AI has increased workforce productivity in the last year",
        "respondent_type": "employer",
        "value_pct": 54.0,
        "year_prev_pct": None,
        "notes": "p.12/14: '54% of employers: AI has increased my workforce's productivity in the last year'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_confident_use_technology",
        "indicator_label": "Talent who feel confident they can use the latest technology",
        "respondent_type": "talent",
        "value_pct": 69.0,
        "year_prev_pct": None,
        "notes": "p.5/12: 'over two-thirds (69%) of talent feel confident they can use the latest technology'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_ai_benefits_company_more",
        "indicator_label": "Office workers who believe AI will benefit companies more than employees",
        "respondent_type": "talent",
        "value_pct": 47.0,
        "year_prev_pct": None,
        "notes": "p.5/13: 'Nearly half of the office workers surveyed (47%) believe AI will benefit companies more than employees'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_ai_no_impact",
        "indicator_label": "Talent who do not expect AI to affect their work at all",
        "respondent_type": "talent",
        "value_pct": 21.0,
        "year_prev_pct": None,
        "notes": "p.5/13: '1 in 5 talent (21%) do not expect AI to affect their work at all'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_employer_ai_high_impact_tasks",
        "indicator_label": "Employers who expect AI to have a high to very high impact on work tasks",
        "respondent_type": "employer",
        "value_pct": 58.0,
        "year_prev_pct": None,
        "notes": "p.13: '58% of employers expect AI to have a high to very high impact on tasks'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_ai_high_impact_tasks",
        "indicator_label": "Talent who expect AI to have a high to very high impact on work tasks",
        "respondent_type": "talent",
        "value_pct": 52.0,
        "year_prev_pct": None,
        "notes": "p.13: '52% of workers [expect high to very high impact]'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_concerned_job_disappear",
        "indicator_label": "Talent concerned their job will disappear in the next five years",
        "respondent_type": "talent",
        "value_pct": 34.0,
        "year_prev_pct": None,
        "notes": "p.13: 'A third of all talent in the study (34%) are concerned that their jobs will disappear in the next five years'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_want_more_ai_development",
        "indicator_label": "Talent who want more investment in AI skills development from employer",
        "respondent_type": "talent",
        "value_pct": 65.0,
        "year_prev_pct": None,
        "notes": "p.12/14: 'two-thirds of talent wanting to see more investment in AI skills development from their employers (65%)'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_employer_hire_fewer_graduates_ai",
        "indicator_label": "Employers planning to hire fewer graduates this year because of AI",
        "respondent_type": "employer",
        "value_pct": 38.0,
        "year_prev_pct": None,
        "notes": "p.14: '38% employers: I am planning to hire fewer graduates this year compared to last year because of AI'"
    },
    {
        "theme": "me_and_the_world",
        "indicator_code": "global_talent_worry_entry_level_disappear",
        "indicator_label": "Talent who worry that entry-level jobs will disappear in the next five years because of AI",
        "respondent_type": "talent",
        "value_pct": 41.0,
        "year_prev_pct": None,
        "notes": "p.14: '41% talent: I worry that entry-level jobs will disappear in the next five years because of AI'"
    },

    # ── THEME 2: Me and my team ───────────────────────────────────────────────

    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_strong_manager_relationship",
        "indicator_label": "Talent who say they have a strong relationship with their manager",
        "respondent_type": "talent",
        "value_pct": 72.0,
        "year_prev_pct": 64.0,
        "notes": "p.19: '72% of talent say they have a strong relationship with their manager, up 8 percentage points from 2025'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_more_connected_manager_than_company",
        "indicator_label": "Talent who feel more connected to their manager than to the company",
        "respondent_type": "talent",
        "value_pct": 63.0,
        "year_prev_pct": None,
        "notes": "p.19: '63% also said they felt more connected to their manager than to the company as a whole'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_seek_reassurance_manager",
        "indicator_label": "Talent who seek more reassurance from manager due to volatile macro environment",
        "respondent_type": "talent",
        "value_pct": 60.0,
        "year_prev_pct": None,
        "notes": "p.19/21: '60% talent: I seek more reassurance from my manager because of the volatile macroeconomic environment'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_avoid_issues_manager_insecurity",
        "indicator_label": "Talent who avoid raising issues with manager due to job insecurity",
        "respondent_type": "talent",
        "value_pct": 55.0,
        "year_prev_pct": None,
        "notes": "p.19/21: '55% talent: I avoid raising issues with my manager due to job insecurity'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_use_ai_work_advice",
        "indicator_label": "Talent who use AI for work advice instead of asking their manager",
        "respondent_type": "talent",
        "value_pct": 50.0,
        "year_prev_pct": None,
        "notes": "p.19: 'half of talent surveyed state that they use AI for work advice instead of their manager'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_employer_encourage_manager_checkins",
        "indicator_label": "Employers actively encouraging managers to check in with talent more due to retention risks",
        "respondent_type": "employer",
        "value_pct": 66.0,
        "year_prev_pct": None,
        "notes": "p.19/21: '66% employer: I have encouraged managers to check in with employees more due to retention risks'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_trust_leadership",
        "indicator_label": "Talent who feel they can trust the leadership of their company",
        "respondent_type": "talent",
        "value_pct": 72.0,
        "year_prev_pct": 76.0,
        "notes": "p.18: 'trust in leadership (72%) ... declining slightly since last year [~76% in 2025]'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_trust_colleagues",
        "indicator_label": "Talent who trust their colleagues",
        "respondent_type": "talent",
        "value_pct": 76.0,
        "year_prev_pct": 79.0,
        "notes": "p.18: 'trust ... among colleagues (76%) both declining slightly since last year [~79% in 2025]'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_workplace_community",
        "indicator_label": "Talent who say their workplace provides a sense of community",
        "respondent_type": "talent",
        "value_pct": 72.0,
        "year_prev_pct": 79.0,
        "notes": "p.18: 'Close to three-quarters of talent (72%) state that their workplace does this successfully, although this sentiment has softened slightly since 2025 (79%)'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_authentic_self_at_work",
        "indicator_label": "Talent who say they can be their authentic selves at work",
        "respondent_type": "talent",
        "value_pct": 76.0,
        "year_prev_pct": None,
        "notes": "p.18: '76% say they can be their authentic selves at work'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_avoid_politics_at_work",
        "indicator_label": "Talent who actively avoid discussing politics with colleagues",
        "respondent_type": "talent",
        "value_pct": 43.0,
        "year_prev_pct": None,
        "notes": "p.18: '43% of respondents state that they actively avoid political discussions'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_more_productive_collaborating",
        "indicator_label": "Talent who are more productive when collaborating and taking multiple perspectives on board",
        "respondent_type": "talent",
        "value_pct": 78.0,
        "year_prev_pct": None,
        "notes": "p.20/21: '78% — I am more productive when I collaborate and multiple perspectives are involved'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_rely_different_generations",
        "indicator_label": "Talent who rely on colleagues from different generations to broaden perspectives",
        "respondent_type": "talent",
        "value_pct": 74.0,
        "year_prev_pct": None,
        "notes": "p.20: '74% of talent say they rely on people from different generations to broaden their perspectives'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_employer_generational_diversity_productivity",
        "indicator_label": "Employers who say having a mix of generations working together is positive for productivity",
        "respondent_type": "employer",
        "value_pct": 95.0,
        "year_prev_pct": None,
        "notes": "p.20/21: '95% of employers highlight generational diversity as a productivity lever'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_employer_want_improve_collaboration",
        "indicator_label": "Employers who want management to spend more time improving team collaboration",
        "respondent_type": "employer",
        "value_pct": 90.0,
        "year_prev_pct": None,
        "notes": "p.20: '90% want to see management spend more time improving team collaboration'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_employer_remote_collaboration_challenging",
        "indicator_label": "Employers who say remote or hybrid work has made collaboration more challenging",
        "respondent_type": "employer",
        "value_pct": 81.0,
        "year_prev_pct": None,
        "notes": "p.6/20/21: '81% [employers] stating that remote or hybrid work has made collaboration more challenging'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_office_boosts_productivity",
        "indicator_label": "Talent who feel working in the office with their team boosts productivity",
        "respondent_type": "talent",
        "value_pct": 48.0,
        "year_prev_pct": None,
        "notes": "p.20/21: '48% of talent feel that working in the office with their team boosts their productivity'"
    },
    {
        "theme": "me_and_my_team",
        "indicator_code": "global_talent_quit_lack_collaboration",
        "indicator_label": "Talent who have quit a job because there was no collaborative atmosphere",
        "respondent_type": "talent",
        "value_pct": 31.0,
        "year_prev_pct": None,
        "notes": "p.20/21: '31% of talent quit a job because there wasn't a collaborative atmosphere'"
    },

    # ── THEME 3: Me — rise of self-defined success ────────────────────────────

    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_talent_pay_attracts",
        "indicator_label": "Talent who say pay is the top factor when looking for a new job",
        "respondent_type": "talent",
        "value_pct": 81.0,
        "year_prev_pct": None,
        "notes": "p.7/26: '81% of talent say that pay is the top factor when looking for a new job'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_talent_wlb_main_retention",
        "indicator_label": "Talent who say work-life balance is the main reason for staying in current role",
        "respondent_type": "talent",
        "value_pct": 46.0,
        "year_prev_pct": None,
        "notes": "p.7/26: 'work-life balance (46%) remains above pay and job security (23% each) as the main reason for staying'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_talent_job_security_retention",
        "indicator_label": "Talent who say job security is the main reason for staying in current role",
        "respondent_type": "talent",
        "value_pct": 23.0,
        "year_prev_pct": None,
        "notes": "p.7/26: 'pay and job security (23% each) as the main reason for staying'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_talent_pay_retention",
        "indicator_label": "Talent who say pay/benefits is the main reason for staying in current role",
        "respondent_type": "talent",
        "value_pct": 23.0,
        "year_prev_pct": None,
        "notes": "p.7/26: 'pay and job security (23% each) as the main reason for staying'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_talent_quit_personal_life",
        "indicator_label": "Talent who have quit a job incompatible with their personal life",
        "respondent_type": "talent",
        "value_pct": 39.0,
        "year_prev_pct": 37.0,
        "notes": "p.7/27: '39% quit a job incompatible with their personal life, up from 37% last year'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_talent_want_portfolio_career",
        "indicator_label": "Talent who do not want a linear career but prefer different jobs across sectors",
        "respondent_type": "talent",
        "value_pct": 38.0,
        "year_prev_pct": None,
        "notes": "p.7/25: 'Nearly 2 in 5 talent (38%) agree, stating that they don't want a linear career'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_talent_want_linear_career",
        "indicator_label": "Talent who still desire a traditional linear career path",
        "respondent_type": "talent",
        "value_pct": 41.0,
        "year_prev_pct": None,
        "notes": "p.25: 'a comparable share (41%) still desire a traditional career path'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_employer_linear_career_outdated",
        "indicator_label": "Employers who feel the traditional linear career path is outdated",
        "respondent_type": "employer",
        "value_pct": 72.0,
        "year_prev_pct": None,
        "notes": "p.7/25: '72% [of employers] feel that the traditional linear career path is outdated'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_employer_autonomy_boosts_engagement",
        "indicator_label": "Employers who believe autonomy boosts engagement, productivity and retention",
        "respondent_type": "employer",
        "value_pct": 72.0,
        "year_prev_pct": None,
        "notes": "p.7/27: '72% of employers believe autonomy boosts engagement, productivity and retention'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_employer_dont_let_talent_set_schedule",
        "indicator_label": "Employers who do not let talent set their own schedules",
        "respondent_type": "employer",
        "value_pct": 81.0,
        "year_prev_pct": None,
        "notes": "p.7/27: '81% don't let talent set their own schedules'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_talent_left_lack_independence",
        "indicator_label": "Talent who quit a job because they lacked independence",
        "respondent_type": "talent",
        "value_pct": 25.0,
        "year_prev_pct": None,
        "notes": "p.27: 'A quarter of the respondents said they quit because they lacked independence'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_talent_location_flexibility",
        "indicator_label": "Talent whose job provides location flexibility (where they work)",
        "respondent_type": "talent",
        "value_pct": 53.0,
        "year_prev_pct": 60.0,
        "notes": "p.26: 'location autonomy ... down to 53% from 60% in 2025'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_talent_hours_flexibility",
        "indicator_label": "Talent whose job provides flexibility in working hours (when they work)",
        "respondent_type": "talent",
        "value_pct": 62.0,
        "year_prev_pct": 65.0,
        "notes": "p.26: 'share of those whose jobs provide flexibility in terms of working hours ... is down slightly from 65% to 62% since last year'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_talent_authentic_self_engaged",
        "indicator_label": "Office workers who feel more engaged and productive when they can be their authentic selves",
        "respondent_type": "talent",
        "value_pct": 57.0,
        "year_prev_pct": None,
        "notes": "p.24/25: '57% of office workers feel more engaged and productive when they can be their authentic self'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_talent_quit_not_authentic",
        "indicator_label": "Talent who have quit a job because they could not be their authentic selves",
        "respondent_type": "talent",
        "value_pct": 27.0,
        "year_prev_pct": None,
        "notes": "p.25: 'nearly a third of respondents (27%) have quit a job because they could not be their authentic selves'"
    },
    {
        "theme": "me_self_defined_success",
        "indicator_code": "global_employer_skills_over_qualifications",
        "indicator_label": "Employers who prioritize skills and experience over formal qualifications when hiring",
        "respondent_type": "employer",
        "value_pct": 87.0,
        "year_prev_pct": None,
        "notes": "p.7/25: 'Employers value skills and experience over formal qualifications when hiring (87%)'"
    },
]


def main():
    print("=== extract_randstad_global.py ===")
    print(f"Aantal globale indicatoren: {len(GLOBAL_INDICATORS)}")

    df = pd.DataFrame(GLOBAL_INDICATORS)

    # Validatie
    assert df["indicator_code"].nunique() == len(df), \
        "Dubbele indicator_codes gevonden!"
    assert df["value_pct"].between(0, 100).all(), \
        "Waarden buiten bereik 0-100!"

    # Bereken change_pp indien year_prev_pct beschikbaar
    df["change_pp"] = df.apply(
        lambda r: round(r["value_pct"] - r["year_prev_pct"], 2)
        if pd.notna(r.get("year_prev_pct")) else None,
        axis=1
    )

    # Output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"\nOutput: {OUTPUT_PATH}")
    print(f"Totaal: {len(df)} indicatoren")
    print(f"Met year_prev_pct: {df['year_prev_pct'].notna().sum()}")
    print(f"Themes:")
    for theme, count in df["theme"].value_counts().items():
        print(f"  {theme}: {count}")

    print("\nVoorbeeld (eerste 5 rijen):")
    print(df[["theme", "indicator_code", "respondent_type", "value_pct", "year_prev_pct"]].head().to_string(index=False))
    print("\n[KLAAR] randstad_global.csv aangemaakt.")


if __name__ == "__main__":
    main()
