# Milestone 3 status report: Noah Eischen's contributions

These are the parts of the interim status report that cover data acquisition and the pre-integration quality assessment.

## 1. Progress on planned tasks

### 1.1 Verify sources and definitions / data acquisition

All four sources are now downloaded by scripts instead of manual exports, and each script writes to `data/raw/`.
[`acquire_eia.py`](../scripts/acquire_eia.py) pulls annual residential prices for all geographies from the EIA API,
[`acquire_fred.py`](../scripts/acquire_fred.py) pulls the 50 state income series,
[`acquire_acs.py`](../scripts/acquire_acs.py) pulls Census table B25040 with margins of error (using the 5-year estimate
for 2020), and [`acquire_cpi.py`](../scripts/acquire_cpi.py) pulls the annual chained CPI-U. The raw files are
[`eia_residential_price.csv`](../data/raw/eia_residential_price.csv),
[`fred_median_household_income.csv`](../data/raw/fred_median_household_income.csv),
[`acs_b25040.csv`](../data/raw/acs_b25040.csv) and [`cpi.csv`](../data/raw/cpi.csv).
[`verify_checksums.py`](../scripts/verify_checksums.py) records a SHA-256 hash for each of the seven files in
`data/raw/`, including the three original CSVs that now live in `data/raw/legacy/`, in
[`checksums.sha256`](../checksums.sha256).

I checked FRED's series notes, and the income series is in C-CPI-U dollars (2025 dollars in the current release), so
the price index is BLS series `SUUR0000SA0`. One month of 2025 has no published value, so the 2025 index is an
average of 11 months (the `months_used` column shows this). The re-acquired ACS data matches the original
`ACS_states_annual_electricity_demand.csv` exactly for all 750 state-years, and the new file also has margins of
error and an `estimate_type` column. All four scripts, the verifier and the profile ran on the real data and are
pushed to `noah-e/acquisition`.

### 1.2 Pre-integration quality assessment

[`results/quality/pre_integration.md`](../results/quality/pre_integration.md) profiles each raw file for accuracy,
completeness, timeliness and consistency. Values look plausible (prices 7.87 to 43.03 cents/kWh, income $43,250 to
$118,700, electric-heat share 4.2% to 92.7%), and nine state-years were flagged for year-over-year jumps above 25%,
which are for review and not necessarily errors. EIA has 799 of 800 expected state-years because the API returns no
price for Alaska 2016, while FRED has all 800 and ACS has all 750. EIA and FRED run through 2025 and ACS through 2024,
so the study window ends in 2024. EIA and FRED identify states by 2-letter codes, ACS uses full names, and the 2020
ACS value is a 5-year estimate. Overall, 749 of 750 state-years exist in all three sources, so integration is
feasible once the Alaska gap is handled.

## 2. Timeline rows

| Date | Task | Status | Owner |
| --- | --- | --- | --- |
| Oct 19 | Verify sources and definitions | Done | Noah E., Nishaan |
| Nov 17 | Acquisition scripts + checksums + pre-integration profile | Done; pushed to `noah-e/acquisition` | Noah E. |

## 4. Challenges and how we are addressing them

- The EIA API returns no price for Alaska 2016, although the original browser export has 20.30 and the 2015 and 2017
  values match the API. That leaves 749 of 750 joinable state-years, and the team still has to decide whether to
  accept the gap or fill the value from the browser export and flag it.
- The Census API now rejects requests without a key, so `acquire_acs.py` needs a free `CENSUS_API_KEY`. Like the EIA
  key, it is read from an environment variable and never committed.
- One month of 2025 has no published CPI, so the base-year index is an 11-month average. `integrate.py` deflates to
  2025 dollars, so the integration owner needs to confirm this is acceptable.

## 5. Individual contribution

I wrote the four acquisition scripts (EIA, FRED, ACS and CPI), the checksum verifier and the pre-integration
profile. I worked out which deflator FRED's income series uses, compared the re-acquired ACS data against the
original file (all 750 state-years matched), and found the missing Alaska 2016 EIA price and the 11-month 2025 CPI.
