# Status Report: Electricity Prices, Household Income, and Residential Electric Heating

Milestone 3 · IS 477 · Fall 2026 · Team: Nishaan Chavla, Noah Eischen, Noah Cha-Price

Work is developed on one branch per role and has not yet been merged into `main`. Links therefore point
to the branch that holds each artifact:
[`noah-e/acquisition`](https://github.com/Nishaan134/NRG-IS477/tree/noah-e/acquisition) (acquisition, raw data, pre-integration quality),
[`nishaan/integration`](https://github.com/Nishaan134/NRG-IS477/tree/nishaan/integration) (cleaning, integration, post-integration quality, workflow) and
[`interim-project-report`](https://github.com/Nishaan134/NRG-IS477/tree/interim-project-report) (analysis).
The branches will be merged into `main` after the full workflow run planned for Nov 18.

## 1. Progress on planned tasks

### 1.1 Verify sources and definitions / data acquisition

All four sources are now downloaded by scripts instead of manual exports, and each script writes to `data/raw/`.
[`acquire_eia.py`](https://github.com/Nishaan134/NRG-IS477/blob/noah-e/acquisition/scripts/acquire_eia.py) pulls annual residential prices for all geographies from the EIA API,
[`acquire_fred.py`](https://github.com/Nishaan134/NRG-IS477/blob/noah-e/acquisition/scripts/acquire_fred.py) pulls the 50 state income series,
[`acquire_acs.py`](https://github.com/Nishaan134/NRG-IS477/blob/noah-e/acquisition/scripts/acquire_acs.py) pulls Census table B25040 with margins of error (using the 5-year estimate
for 2020), and [`acquire_cpi.py`](https://github.com/Nishaan134/NRG-IS477/blob/noah-e/acquisition/scripts/acquire_cpi.py) pulls the annual chained CPI-U. The raw files are
[`eia_residential_price.csv`](https://github.com/Nishaan134/NRG-IS477/blob/noah-e/acquisition/data/raw/eia_residential_price.csv),
[`fred_median_household_income.csv`](https://github.com/Nishaan134/NRG-IS477/blob/noah-e/acquisition/data/raw/fred_median_household_income.csv),
[`acs_b25040.csv`](https://github.com/Nishaan134/NRG-IS477/blob/noah-e/acquisition/data/raw/acs_b25040.csv) and [`cpi.csv`](https://github.com/Nishaan134/NRG-IS477/blob/noah-e/acquisition/data/raw/cpi.csv).
[`verify_checksums.py`](https://github.com/Nishaan134/NRG-IS477/blob/noah-e/acquisition/scripts/verify_checksums.py) records a SHA-256 hash for each of the seven files in
`data/raw/`, including the three original CSVs that now live in
[`data/raw/legacy/`](https://github.com/Nishaan134/NRG-IS477/tree/noah-e/acquisition/data/raw/legacy), in
[`checksums.sha256`](https://github.com/Nishaan134/NRG-IS477/blob/noah-e/acquisition/checksums.sha256).

FRED's series notes show that the income series is in C-CPI-U dollars (2025 dollars in the current release), so
the price index is BLS series `SUUR0000SA0`. One month of 2025 has no published value, so the 2025 index is an
average of 11 months (the `months_used` column shows this). The re-acquired ACS data matches the original
`ACS_states_annual_electricity_demand.csv` exactly for all 750 state-years, and the new file also has margins of
error and an `estimate_type` column.

### 1.2 Pre-integration quality assessment

[`results/quality/pre_integration.md`](https://github.com/Nishaan134/NRG-IS477/blob/noah-e/acquisition/results/quality/pre_integration.md),
produced by [`profile_raw.py`](https://github.com/Nishaan134/NRG-IS477/blob/noah-e/acquisition/scripts/profile_raw.py),
profiles each raw file for accuracy, completeness, timeliness and consistency.

- **Accuracy:** values look plausible (prices 7.87 to 43.03 cents/kWh, income $43,250 to $118,700, electric-heat
  share 4.2% to 92.7%). Nine state-years were flagged for year-over-year jumps above 25%; these are for review and
  not necessarily errors.
- **Completeness:** EIA has 799 of 800 expected state-years because the API returns no price for Alaska 2016.
  FRED has all 800 and ACS has all 750.
- **Timeliness:** EIA and FRED run through 2025 and ACS through 2024, so the study window ends in 2024.
- **Consistency:** EIA and FRED identify states by 2-letter codes while ACS uses full names, and the 2020 ACS value
  is a 5-year estimate.

Overall, 749 of 750 state-years exist in all three sources, so integration is feasible once the Alaska gap is handled.

### 1.3 Cleaning and standardization

One cleaning script per source turns each raw file into a tidy state-year table. Every operation responds
to a specific issue found in the raw data:

| Script | Output | Issues addressed |
| --- | --- | --- |
| [`clean_eia.py`](https://github.com/Nishaan134/NRG-IS477/blob/nishaan/integration/scripts/clean_eia.py) | `data/interim/eia_clean.csv` | EIA mixes the US total, census-division aggregates, DC and the 50 states in one table; prices arrive as text; the state is a 2-letter id. The script keeps residential rows for the 50 states, maps ids to full names, converts types, drops rows with no price, checks that there is a single unit (cents/kWh) and rejects conflicting duplicate state-years. |
| [`clean_fred.py`](https://github.com/Nishaan134/NRG-IS477/blob/nishaan/integration/scripts/clean_fred.py) | `data/interim/fred_clean.csv` | FRED is wide (one column per state) and the state is only encoded in the series id. The script reshapes to long format, parses `MEHOINUS<ST>A672N`, maps codes to full names, reduces dates to years and treats FRED's `.` as missing. |
| [`clean_acs.py`](https://github.com/Nishaan134/NRG-IS477/blob/nishaan/integration/scripts/clean_acs.py) | `data/interim/acs_clean.csv` | The ACS pull includes DC and Puerto Rico, uses negative sentinel codes for unavailable values, and 2020 is a 5-year estimate. The script keeps the 50 states, converts sentinels to missing, computes the electric-heat share **and its margin of error** (Census proportion formula), checks electric units ≤ total units, and keeps an `estimate_type` flag for 2020. |
| [`clean_cpi.py`](https://github.com/Nishaan134/NRG-IS477/blob/nishaan/integration/scripts/clean_cpi.py) | `data/interim/cpi_clean.csv` | The price index may be monthly or annual; the script reduces it to one value per year. |

A shared lookup, [`state_codes.py`](https://github.com/Nishaan134/NRG-IS477/blob/nishaan/integration/scripts/state_codes.py),
guarantees that all sources use identical state names, which is what makes the join key reliable.

### 1.4 Integration and validation

[`integrate.py`](https://github.com/Nishaan134/NRG-IS477/blob/nishaan/integration/scripts/integrate.py) joins EIA,
FRED and ACS on `(state, year)` with an inner join limited to 2010–2024, the window all three sources share, and
validates that every join is one-to-one. It then joins the price index on `year` and adds `real_price_cents_kwh`,
so prices are in the same constant (2025 C-CPI-U) dollars as income, an issue raised in our plan's Constraints
section. Every source row that is not carried into `data/processed/merged_state_year.csv` is written to
`results/quality/unmatched_rows.csv` with a reason.

[`profile_integrated.py`](https://github.com/Nishaan134/NRG-IS477/blob/nishaan/integration/scripts/profile_integrated.py)
produces the post-integration quality report `results/quality/post_integration.md` and stops the workflow if a
check fails. It covers:

- **Completeness:** 750 rows (50 states × 15 years), no missing values, no in-window rows lost in the join.
- **Accuracy:** unique keys, plausible ranges, the share recomputes from counts, values are identical to the
  cleaned sources after the join, and real prices recompute from the index; large year-over-year changes are
  flagged for review.
- **Consistency:** one state code per state, one dollar base year, the ACS estimate type by year.
- **Timeliness:** year coverage of each source and why the window ends in 2024.

**Status.** The scripts were first tested on placeholder files built from our original CSVs (all checks passed),
then run on the newly acquired raw data on Nov 16. On the real data the integration produces **749** state-years:
the missing Alaska 2016 EIA price removes that state-year, and the 2025 EIA and FRED rows (100 rows) are excluded
as outside the window. 14 of the 17 post-integration checks pass, including unique keys, value ranges, unchanged
values after the join and the deflation check. The 3 failing checks (row count, full year coverage per state,
no in-window rows lost) are all caused by Alaska 2016, so the quality gate is working as intended. Resolving this
gap is the main open item (see section 4). Generated outputs will be committed after the gap is resolved and the
workflow is rerun.

### 1.5 Workflow automation

The [`Snakefile`](https://github.com/Nishaan134/NRG-IS477/blob/nishaan/integration/Snakefile) chains the
single-purpose scripts: acquisition → checksum verification → pre-integration profile → cleaning → integration →
post-integration profile → analysis. Acquisition rules have no inputs, so a fresh clone reuses the committed raw
files and runs without API keys; `--forcerun` re-downloads them. Dependencies are pinned in
[`requirements.txt`](https://github.com/Nishaan134/NRG-IS477/blob/nishaan/integration/requirements.txt).
On the real data, the workflow runs from checksum verification through integration and stops at the
post-integration check described above. The analysis rules still need to be aligned with the analysis scripts'
file locations and outputs (section 4).

### 1.6 Exploratory analysis

The analysis follows the three research questions in our plan. The electric-heat share is the outcome
in RQ2 and RQ3, modeled on real price and real income, as the plan describes.

| Question | What we run | Output |
| --- | --- | --- |
| RQ1: how do prices, real income and the share vary across states and over 2010-2024? | Yearly and per-state summaries; between-state vs within-state spread | `results/analysis/rq1_*.csv`, `results/figures/rq1_trends.png` |
| RQ2: within a year, how are they related? | Per-year Spearman correlations and OLS of share on log price and log income | `results/analysis/rq2_cross_section_by_year.csv`, `results/figures/rq2_*.png` |
| RQ3: are changes in price and income associated with changes in the share? | Models with state and year fixed effects and first differences; standard errors clustered by state | `results/analysis/rq3_models.csv`, `results/figures/rq3_changes.png` |

[`analyze.py`](https://github.com/Nishaan134/NRG-IS477/blob/interim-project-report/scripts/scripts/analyze.py) produces the tables and `results/analysis/summary.md`.
[`plot_figures.py`](https://github.com/Nishaan134/NRG-IS477/blob/interim-project-report/scripts/scripts/plot_figures.py) produces four figures. The RQ3 models are repeated
as sensitivity checks that exclude 2020 (5-year ACS estimate), keep 2017 onward (after the CPS income
method changes), use nominal instead of real price, and drop the 10 states with the noisiest share.

**Status.** Both scripts run end to end on test data with the same columns as `merged_state_year.csv`.
They have not yet been run on the final merged file, so we report no findings yet. We will run them after
the Nov 18 full workflow run and report the results in the final report. Results are associations, not
causal effects.

## 2. Updated timeline

| Date | Task | Status | Owner |
| --- | --- | --- | --- |
| Oct 19 | Verify sources and definitions | Done (completed Nov 16 with scripted acquisition) | Noah E., Nishaan |
| Oct 24 | Clean and standardize data | Done; run on real data Nov 16 | Nishaan |
| Nov 1 | Integrate and validate data | Done; 749/750 rows, Alaska 2016 gap open | Nishaan |
| Nov 13 | Exploratory analysis (descriptive tables and plots) | Scripts written and tested; rerun on real data after Nov 18 | Noah C-P |
| Nov 17 | Acquisition scripts + checksums + pre-integration profile | Done; on `noah-e/acquisition` | Noah E. |
| Nov 18 | Resolve Alaska 2016 gap; align analysis step with the workflow; full workflow run; merge branches into `main` | Planned | All |
| Nov 19 | Status report + `status-report` release | In progress | All (release: Nishaan) |
| Nov 20 | Analytical comparisons | Scripts written and tested; final run after Nov 18 workflow run | Noah C-P |
| Nov 27 | Draft final report (README) | Planned | All |
| Dec 4 | Fresh-clone reproducibility test, metadata, licenses | Planned | Nishaan |
| Dec 7 | `final-project` release | Planned | Nishaan |

## 3. Changes to the project plan

- **Measure renamed.** The ACS variable is the share of occupied housing units **heated by electricity**
  (B25040), not electricity demand. Columns and text now say `share_electric_heat`.
- **Acquisition is now scripted.** All sources are downloaded by scripts (EIA and Census through their APIs)
  instead of manual browser exports, with SHA-256 checksums. This replaces the missing `build_heating_fuel.py`.
- **Deflator changed.** The plan proposed CPI-U-RS, but FRED's income series is in C-CPI-U dollars, so prices are
  deflated with the chained CPI-U (`SUUR0000SA0`) to keep both in the same constant dollars.
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

- **EIA export format.** The browser export mixes metadata lines and national and regional aggregates with
  states, so we switched to the API and filter to the 50 states during cleaning.
- **Provenance gap for ACS.** The original ACS file was built by a script that is not in the repository.
  Re-acquiring it from the Census API makes it reproducible, and it matches the original for all 750 state-years.
- **Missing Alaska 2016 price.** The EIA API returns no price for Alaska 2016, although the original browser
  export has 20.30 and the 2015 and 2017 values match the API. This leaves 749 of 750 joinable state-years and
  makes the post-integration checks fail. By Nov 18 we will either accept the gap (and adjust the expected row
  count with a documented reason) or fill the value from the archived browser export and flag it as imputed.
- **Mixing real and nominal values.** Income is inflation-adjusted but prices are not; solved by deflating
  prices with the matching price index in the integration step.
- **Incomplete 2025 CPI.** One month of 2025 has no published CPI value, so the base-year index is an 11-month
  average. We will document this; it rescales all real prices by the same factor and does not change their
  relative differences.
- **API keys.** The EIA and Census APIs both need a free key (`EIA_API_KEY`, `CENSUS_API_KEY`). Keys are read from
  environment variables and never committed, and committed raw files let the workflow run without them.
- **No DC income data.** FRED has no DC series, so the analysis covers the 50 states only; DC rows are
  dropped and documented.
- **Connecting the analysis step.** The analysis scripts currently sit in `scripts/scripts/`, write to
  `results/analysis/` rather than the outputs the Snakefile expects, and use `statsmodels`, which is not yet in
  `requirements.txt`. We will align the file locations, the Snakefile rules and the requirements before the
  Nov 18 run.
- **Small, dependent panel.** 50 states over 15 years limits power and observations within a state are
  not independent. We use simple models, state and year fixed effects, and standard errors clustered by
  state, and treat results as exploratory.
- **Uneven measurement across sources.** 2020 is a 5-year ACS estimate, state income comes from a small
  CPS sample with method changes, and the ACS share has margins of error. Each is covered by a
  sensitivity check in section 1.6.
- **Results depend on the final raw files.** The analysis was tested on data shaped like the merged
  table; we will rerun it after the Nov 18 full workflow run.

## 5. Individual contributions

Each member adds and commits their own summary.

### Nishaan Chavla

I set up the repository layout, `.gitignore` and pinned `requirements.txt`, and wrote the data integration
stage: the four per-source cleaning scripts, the shared state lookup, the state-year integration script with its
unmatched-row log, the post-integration quality assessment and the Snakefile that ties every stage together.
I defined the file formats passed between stages so the three of us could work in parallel, tested the
pipeline first on placeholder data and then on the newly acquired data, which surfaced the Alaska 2016 gap, and
assembled this report. Next I will resolve the Alaska gap with the team, connect the analysis step to the
workflow, merge the branches and create the `status-report` release.

### Noah Eischen

### Noah Cha-Price
