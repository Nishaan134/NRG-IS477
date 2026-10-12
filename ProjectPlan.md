# Project Plan: Electricity Prices, Household Income, Residential Electrification

## Overview

Our project will look into how residential electricity prices and household income relate to electricity use in housing in the United States. We will integrate our three datasets, which focus on: Energy Information Administration retail electricity prices, household income via FRED, and an American Community Survey (ACS) on annual electricity demand at the state level. Our initial study window is 2010–2024, subject to source and coverage verification.

We plan to first document each dataset's source, variable definitions, units, and collection methods. Then, we will reshape the EIA and FRED files into cleaner tables and integrate all three datasets using state and year. We will also check for quality, identifying and dropping (if needed) missing observations, duplicate keys, incompatible definitions, and unmatched records.

Using the validated integrated data, we will compare state trends and associations among electricity prices, real household income, and the ACS electricity share. We will use descriptive statistics and visualizations to communicate trends we identify. Our results will describe associations between the three datasets, such as a relationship between electricity prices and household income.

## Team

| Team Member | Role | Responsibilities |
| --- | --- | --- |
| Noah Cha-Price | Data analysis | Determines research questions, develops planned analysis, interprets findings. |
| Nishaan Chavla | Data integration | Documents dependencies and results, makes sure findings are presentable, leads GitHub tags and releases. |
| Noah Eischen | Data acquisition | Verifies data sources, documents data acquisition and validates data, ensures data is usable for other members.|

## Research Questions

1. How do residential electricity prices, median household incomes, and the verified ACS electricity share vary across states and over the common study period?
2. Within a given year, what relationships, if any, exist between residential electricity prices, real median household income, and the ACS electricity share?
3. Are changes in electricity prices and real income associated with changes in the ACS electricity share over the study period?

## Datasets

| Dataset | Source and description | Observed coverage | Contribution and linkage |
| --- | --- | --- | --- |
| Residential electricity prices | [U.S. EIA Electricity Data Browser](https://www.eia.gov/electricity/data/browser/), "Average retail price of electricity" dataset, residential sector, annual, in cents per kWh. Exported as a CSV table. | 50 states; annual values 2010–2025. | Addresses the price-related parts of the research questions. Reshape from one column/year to one row/state-year, remove any header or metadata lines, convert prices to numeric (trim commas/space), and join on state and year. 2025 values have no ACS match. |
| Real median household income | Census Bureau estimates distributed through [FRED](https://fred.stlouisfed.org/series/MEHOINUSILA672N) as one series per state (`MEHOINUS<ST>A672N`), in inflation-adjusted dollars. District of Columbia was excluded because FRED's data list is limited to 50 series. | 16 annual rows (2010–2025) × 50 states, with no missing values. | Addresses the income-related parts of the research questions. Reshape to one row per state-year, reduce the observation date to a year, extract the state abbreviation from each series ID, and map it to the full state name instead. State-level estimates can swing from year to year. |
| ACS electric heating share | [ACS table B25040: House Heating Fuel](https://data.census.gov/table/ACSDT1Y2024.B25040), downloaded one year at a time and combined with `build_heating_fuel.py`. All heating fuels were read, then reduced to electricity (count and share of occupied housing units). | 750 rows (50 states × 2010–2024). 2020 is an ACS 5-year estimate because the standard 1-year file was not released due to COVID-related data collection issues. | Answers how much housing depends on electric heat. Stack the yearly files, reshape state columns into rows, and compute the electricity share. State names already match EIA's, so it links on state and year, but ACS ends in 2024. |

## Analysis
These datasets all have the common attributes 'state' and 'year', which allows us to identify similarities across these categories. Creating visualizations like states' trends year by year or same-year scatterplots can help us find relationships between states. We could also fit models to estimate ACS share using electricity prices and real income and determine the relationship's correlation coefficient.

## Constraints

- **Data window.** EIA and FRED extend to 2025, but ACS 1-year data ends in 2024, so the integrated analysis is limited to 2010–2024. 2025 values from EIA and FRED will be dropped at merge.
- **2020 ACS data.** The Census Bureau did not release standard 2020 ACS 1-year estimates because of COVID-19 collection problems; only experimental estimates exist. We will verify what our 2020 rows contain and either flag, exclude, or interpolate that year, documenting the choice.
- **Geographic scope.** Analysis is limited to the 50 states. Washington, D.C., and territories will be excluded unless all three sources include them consistently.
- **Nominal vs. real values.** EIA prices are nominal (cents per kWh), while FRED income is in constant (inflation-adjusted) dollars. Prices must be deflated with the same price index (CPI-U-RS) before the two are compared.
- **Price definition.** EIA residential price is average revenue per kWh sold. It reflects the overall cost of electricity but not rate structures, fixed charges, or time-of-use pricing.
- **Income estimate quality.** State median household income in FRED comes from the CPS ASEC, which has small state samples and large standard errors. Methodology changes (notably 2013 and 2017) may create breaks in the series.
- **Sample size.** With 50 states over 15 years (at most 750 state-year observations), statistical power is limited, and observations within a state are not independent across years.
- **Time and scope.** With three members and about eight weeks, the analysis will remain descriptive and correlational rather than causal or predictive.

## Gaps

- **Measure mismatch.** ACS B25040 measures the share of occupied housing units that use electricity as their primary heating fuel. It does not measure electricity consumption or demand. Findings will be framed as associations with electric heating adoption, not electricity use. The Overview wording should be revised to match.
- **Missing confounders.** Climate (heating degree days), natural gas availability and price, housing age and type, and state energy policies all likely affect heating fuel choice, but none appear in our data. Any relationships we observe may be driven by these unmeasured factors.
- **Aggregation level.** All three datasets are state-level aggregates. Results cannot be applied to individual households (ecological fallacy), and within-state differences such as urban versus rural areas are hidden.
- **Survey uncertainty.** ACS estimates include margins of error that we do not currently plan to propagate through the analysis, so small year-to-year changes in electricity share may not be meaningful.
- **Different income sources.** Income comes from the CPS (via FRED), while the housing measure comes from the ACS. Because the two surveys use different samples and methods, the measures are not perfectly comparable.
- **No causal identification.** Our design cannot establish whether prices or income cause changes in electric heating share. The research questions are limited to associations.
- **Unverified provenance.** ACS estimate type (1-year vs. 5-year), FRED units, and EIA definitions are still being confirmed (Oct 19 milestone). Any discrepancies found then may require revising this plan.

## Timeline

| Date | Task | Task Description | Member Responsible |
| --- | --- | --- | --- |
| October 19, 2026 | Verify sources and definitions | Recover ACS provenance and estimate product, confirm FRED units and EIA definitions. | Acquisition lead & integration lead |
| October 24, 2026 | Clean and standardize data | Reshape EIA/FRED, normalize types and missing values, create geographic crosswalk, and document temporal alignment. | All members |
| November 1, 2026 | Integrate and validate data | Build state-year tables and merged output, check keys, counts, units, unmatched rows, and share calculations; log any issues with data. | All members |
| November 6, 2026 | Status report / revise plan | Summarize progress and unresolved issues, take in any instructor feedback, prepare status-report tag/release. | All members |
| November 13, 2026 | Exploratory analysis | Create descriptive tables and plots, evaluate comparability and refine questions based on new discoveries within the data. | Analysis lead |
| November 20, 2026 | Analytical comparisons | Examine cross-sectional, within-state, and year-by-year associations, evaluate sensitivity to different aspects of the datasets. | All members |
| November 27, 2026 | Draft final report | Explain methods, integration, findings, doubts, and limitations; connect our results to our research questions. | All members |
| December 4, 2026 | Final submission | Verify documentation, citations, each member's contribution, and complete the final project. | All members |
