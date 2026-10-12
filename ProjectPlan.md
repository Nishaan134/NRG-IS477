# Project Plan: Electricity Prices, Household Income, Residential Electrification

## Overview

Our project will look into how residential electricity prices and household income relate to electricity use in housing in the United States. We will integrate our three datasets, which focus on: Energy Information Administration retail electricity prices, household income via FRED, and an American Community Survey (ACS) on annual electricity demand at the state level. Our initial study window is 2010–2024, subject to source and coverage verification.

We plan to first document each dataset's original source, variable definitions, units, and collection methods. Then, we will reshape the EIA and FRED files into cleaner tables and integrate all three datasets using state and year. We will also check for quality, identifying and dropping (if needed) missing observations, duplicate keys, incompatible definitions, and unmatched records.

Using the validated integrated data, we will compare state trends and associations among electricity prices, real household income, and the ACS electricity share. We will use descriptive statistics and visualizations to communicate trends we identify. Our results will describe associations between the three datasets, such as a relationship between electricity prices and household income.

## Team

| Team Member | Role | Responsibilities |
| --- | --- | --- |
| Noah Cha-Price | Data analysis | Determines research questions, develops planned analysis, interprets findings. |
| Nishaan Chavla | Data integration | Documents dependencies and results, makes sure findings are presentable, leads GitHub tags and releases. |
| Noah Eischen | Data acquisition | Verify data sources, documents data acquisition and validates data, ensures data is usable for other members.|

## Research Questions

1. How do residential electricity prices, median household incomes, and the verified ACS electricity share vary across states and over the common study period?
2. Within a given year, what relationships, if any, exist between residential electricity prices, real median household income, and the ACS electricity share?
3. Are changes in electricity prices and real income associated with changes in the ACS electricity share over the study period?

## Datasets

| Dataset | Source and description | Observed coverage | Contribution and linkage |
| --- | --- | --- | --- |
| Residential electricity prices| [U.S. EIA Electricity Data Browser](https://www.eia.gov/electricity/data/browser/). | Year columns 2010–2025; 50 states. | Measures the price of residential electricity. We may extract state abbreviations from identifiers like `ELEC.PRICE.IL-RES.A` and reshape year columns into rows. Possibly remove locations without values. |
| Real median household income | Census Bureau estimates distributed through [FRED](https://fred.stlouisfed.org/series/MEHOINUSILA672N). | 16 annual rows, 2010–2025, and 50 states. | This dataset adds economic context. Convert observation dates to years, reshape state series into rows, and map series IDs to state abbreviations. |
| ACS electricity-related housing measure | [ACS table B25040: House Heating Fuel](https://data.census.gov/table/ACSDT1Y2024.B25040) | 750 rows, 50 states, 2010–2024. | Provides housing counts and an electricity share. We could map state names to the same state identifiers used by EIA and FRED, then link on state/year. |

## Analysis
| These datasets all have the common attributes of state and year, which will allow us to identify similarities by these categories. We can do this by creating visualizations by state trend year over year or same-year scatterplots finding relationships between states. We could also fit models estimating for ACS share using electricity prices and real income and determine the correlation coefficient.|

## Timeline

| Date | Task | Task Description | Member Responsible |
| --- | --- | --- | --- |
| October 19, 2026 | Verify sources and definitions | Recover ACS provenance and estimate product, confirm FRED units and EIA definitions. | Acquisition lead & integration lead |
| October 24, 2026 | Clean and standardize data | Reshape EIA/FRED, normalize types and missing values, create geographic crosswalk, and document temporal alignment. | All members |
| November 1, 2026 | Integrate and validate data | Build state-year tables and merged output, check keys, counts, units, unmatched rows, and share calculations, log any issues with data. | All members |
| November 6, 2026 | Status report / revise plan | Summarize progress and unresolved issues, take in any instructor feedback, prepare status-report tag/release. | All members |
| November 13, 2026 | Exploratory analysis | Create descriptive tables and plots, evaluate comparability and refine questions based on new discoveries within the data. | Analysis lead |
| November 20, 2026 | Analytical comparisons | Examine cross-sectional, within-state, and year-by-year associations, evaluate sensitivity to different aspects of the datasets. | All members |
| November 27, 2026 | Draft final report | Explain methods, integration, findings, doubts, and limitations, connect our results to our research questions. | All members |
| December 4, 2026 | Final submission | Verify documentation, citations, each member's contribution, and complete final project. | All members |
