# Status Report: Electricity Prices, Household Income, and Residential Electric Heating

Milestone 3 · IS 477 · Fall 2026

<!-- Sections marked TODO(<name>) are written and committed by that team member. -->

## 1. Progress on planned tasks

### 1.1 Verify sources and definitions / data acquisition

### 1.2 Pre-integration quality assessment

### 1.3 Cleaning and standardization

One cleaning script per source turns each raw file into a tidy state-year table. Every operation responds
to a specific issue in the raw data:

| Script | Output | Issues addressed |
| --- | --- | --- |
| [`scripts/clean_eia.py`](scripts/clean_eia.py) | [`data/interim/eia_clean.csv`](data/interim/eia_clean.csv) | EIA mixes the US total, 9 census-division aggregates, DC and the 50 states in one table; prices arrive as text; state is a 2-letter id. The script keeps residential rows for the 50 states, maps ids to full names, converts types, checks the single unit (cents/kWh) and rejects conflicting duplicate state-years. |
| [`scripts/clean_fred.py`](scripts/clean_fred.py) | [`data/interim/fred_clean.csv`](data/interim/fred_clean.csv) | FRED is wide (one column per state) and the state is only encoded in the series id. The script reshapes to long format, parses `MEHOINUS<ST>A672N`, maps codes to full names, reduces dates to years and treats FRED's `.` as missing. |
| [`scripts/clean_acs.py`](scripts/clean_acs.py) | [`data/interim/acs_clean.csv`](data/interim/acs_clean.csv) | The ACS pull includes DC and Puerto Rico, uses negative sentinel codes for unavailable values, and 2020 is a 5-year estimate. The script keeps the 50 states, converts sentinels to missing, computes the electric-heat share **and its margin of error** (Census proportion formula), checks electric units ≤ total units, and keeps an `estimate_type` flag for 2020. |
| [`scripts/clean_cpi.py`](scripts/clean_cpi.py) | [`data/interim/cpi_clean.csv`](data/interim/cpi_clean.csv) | Price index may be monthly or annual; the script reduces it to one annual value and drops incomplete years. |

A shared lookup, [`scripts/state_codes.py`](scripts/state_codes.py), guarantees that all sources use
identical state names, which is what makes the join key reliable.

### 1.4 Integration and validation 

[`scripts/integrate.py`](scripts/integrate.py) joins EIA, FRED and ACS on `(state, year)` with an inner
join limited to 2010–2024, the window all three sources share, and validates that every join is
one-to-one. It then joins the price index on `year` and adds `real_price_cents_kwh`, so prices are in
the same constant dollars as income (an issue raised in our plan's Constraints section). Every source
row that is not carried into [`data/processed/merged_state_year.csv`](data/processed/merged_state_year.csv)
is written to [`results/quality/unmatched_rows.csv`](results/quality/unmatched_rows.csv) with a reason.

[`scripts/profile_integrated.py`](scripts/profile_integrated.py) produces the post-integration quality
report [`results/quality/post_integration.md`](results/quality/post_integration.md) and stops the
workflow if a check fails. It checks:

- **Completeness:** 750 rows (50 states × 15 years), no missing values, no in-window rows lost in the join.
- **Accuracy:** unique keys, plausible ranges, the share recomputes from counts, values identical to the
  cleaned sources after the join, and real prices recompute from the index; large year-over-year
  changes are flagged for review.
- **Consistency:** one state code per state, one dollar base year, the ACS estimate type by year.
- **Timeliness:** year coverage of each source and why the window ends in 2024.

Status: the scripts are complete and were tested end to end on placeholder raw files built from our
original CSVs. With that data, all checks passed: 750 merged rows, and only the 2025 EIA and FRED rows were
excluded (outside the window). They will be rerun on the newly acquired raw files.

### 1.5 Workflow automation

The [`Snakefile`](Snakefile) chains the single-purpose scripts: acquisition → checksum verification →
pre-integration profile → cleaning → integration → post-integration profile → analysis. Acquisition
rules have no inputs, so a fresh clone reuses the committed raw files and runs without an API key;
`--forcerun` re-downloads them. Dependencies are pinned in [`requirements.txt`](requirements.txt).

### 1.6 Exploratory analysis

The analysis follows the three research questions in our plan. The electric-heat share is the outcome
in RQ2 and RQ3, modeled on real price and real income, as the plan describes.

| Question | What we run | Output |
| --- | --- | --- |
| RQ1: how do prices, real income and the share vary across states and over 2010-2024? | Yearly and per-state summaries; between-state vs within-state spread | `results/analysis/rq1_*.csv`, [`results/figures/rq1_trends.png`](results/figures/rq1_trends.png) |
| RQ2: within a year, how are they related? | Per-year Spearman correlations and OLS of share on log price and log income | `results/analysis/rq2_cross_section_by_year.csv`, `results/figures/rq2_*.png` |
| RQ3: are changes in price and income associated with changes in the share? | Models with state and year fixed effects and first differences; standard errors clustered by state | `results/analysis/rq3_models.csv`, [`results/figures/rq3_changes.png`](results/figures/rq3_changes.png) |

[`scripts/analyze.py`](scripts/analyze.py) produces the tables and `results/analysis/summary.md`.
[`scripts/plot_figures.py`](scripts/plot_figures.py) produces four figures. The RQ3 models are repeated
as sensitivity checks that exclude 2020 (5-year ACS estimate), keep 2017 onward (after the CPS income
method changes), use nominal instead of real price, and drop the 10 states with the noisiest share.

**Status.** Both scripts run end to end on test data with the same columns as `merged_state_year.csv`.
They have not yet been run on the final merged file, so we report no findings yet. We will run them after
the Nov 18 full workflow run and report the results in the final report. Results are associations, not
causal effects.

## 2. Updated timeline

| Date | Task | Status | Owner |
| --- | --- | --- | --- |
| Oct 19 | Verify sources and definitions |  | Noah E., Nishaan |
| Oct 24 | Clean and standardize data | Scripts complete; awaiting final raw files | Nishaan |
| Nov 1 | Integrate and validate data | Scripts complete; awaiting final raw files | Nishaan |
| Nov 13 | Exploratory analysis (descriptive tables and plots) | Scripts written and tested; rerun on real data after Nov 18 | Noah C-P |
| Nov 17 | Acquisition scripts + checksums + pre-integration profile |  | Noah E. |
| Nov 18 | Full workflow run on real data | Planned | All |
| Nov 19 | Status report + `status-report` release | In progress | All (release: Nishaan) |
| Nov 20 | Analytical comparisons | Scripts written and tested; final run after Nov 18 workflow run | Noah C-P |
| Nov 27 | Draft final report (README) | Planned | All |
| Dec 4 | Fresh-clone reproducibility test, metadata, licenses | Planned | Nishaan |
| Dec 7 | `final-project` release | Planned | Nishaan |

## 3. Changes to the project plan

- **Measure renamed.** The ACS variable is the share of occupied housing units **heated by electricity**
  (B25040), not electricity demand. Columns and text now say `share_electric_heat`.
- **Acquisition is now scripted.** All sources are downloaded by scripts (EIA through its API) instead of
  manual browser exports, with SHA-256 checksums, which replaces the missing `build_heating_fuel.py`.
- **Price deflation added.** EIA prices are deflated into the same constant dollars as FRED income.
- **Survey uncertainty kept.** ACS margins of error are now carried through and the MOE of the share is
  computed, which addresses part of the "Survey uncertainty" gap.
- **2020 handling decided.** 2020 ACS rows (5-year estimate) are kept and flagged with `estimate_type`.
- **Research questions unchanged, analysis made concrete.** We kept the three research questions and
  defined how each is answered (section 1.6), with the share as the outcome as in the plan.
- **Plan gaps addressed in the analysis.** The measure-mismatch gap is handled by framing results as
  associations with electric-heating adoption. The survey-uncertainty gap is handled by reporting the
  share's relative margin of error and dropping the noisiest states as a sensitivity check. The CPS
  method changes and the 2020 estimate type are handled by sensitivity checks, and state clustering
  addresses non-independence across years.
- **Milestone 2 feedback.** The feedback was positive and requested no changes, so we kept the plan's
  structure and focused on the gaps listed in our plan, as described above.

## 4. Challenges and how we are addressing them

- **EIA export format.** The browser export mixes metadata lines, national and regional aggregates with
  states, so we switched to the API and filter to the 50 states during cleaning.
- **Provenance gap for ACS.** The original ACS file was built by a script that is not in the repository.
  Re-acquiring it from the Census API makes it reproducible.
- **Mixing real and nominal values.** Income is inflation-adjusted but prices are not; solved by
  deflating prices with a price index in the integration step.
- **No DC income data.** FRED has no DC series, so the analysis covers the 50 states only; DC rows are
  dropped and documented.
- **Small, dependent panel.** 50 states over 15 years limits power and observations within a state are
  not independent. We use simple models, state and year fixed effects, and standard errors clustered by
  state, and treat results as exploratory.
- **Uneven measurement across sources.** 2020 is a 5-year ACS estimate, state income comes from a small
  CPS sample with method changes, and the ACS share has margins of error. Each is covered by a
  sensitivity check in section 1.6.
- **Results depend on the final raw files.** The analysis was tested on data shaped like the merged
  table; we will rerun it after the Nov 18 full workflow run.

## 5. Individual contributions

### Nishaan Chavla

### Noah Eischen

### Noah Cha-Price
I wrote the analysis step of the workflow: [`scripts/analyze.py`](scripts/analyze.py) (summaries,
per-year comparisons, fixed-effects and first-difference models, sensitivity checks) and
[`scripts/plot_figures.py`](scripts/plot_figures.py) (four figures), organized around our three research
questions. I wrote the analysis parts of this report (section 1.6, the Nov 13 and Nov 20 timeline rows,
the plan changes and the challenges) and tested both scripts end to end. Next I will run them on the
final merged data after Nov 18 and write up the results.
