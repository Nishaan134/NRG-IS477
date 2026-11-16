# End-to-end workflow: acquisition -> integrity check -> pre-integration quality ->
# cleaning -> integration -> post-integration quality -> analysis.
#
# Run everything:          snakemake --cores 1
# Re-download raw data:    snakemake --cores 1 --forcerun acquire_eia acquire_fred acquire_acs acquire_cpi
#                          (acquire_eia needs the EIA_API_KEY environment variable)
#
# Acquisition rules have no inputs, so committed raw files are reused on a fresh clone and the
# workflow runs without an API key unless a re-download is forced.

RAW = {
    "eia": "data/raw/eia_residential_price.csv",
    "fred": "data/raw/fred_median_household_income.csv",
    "acs": "data/raw/acs_b25040.csv",
    "cpi": "data/raw/cpi.csv",
}
CHECKSUM_REPORT = "results/quality/checksum_report.txt"


rule all:
    input:
        CHECKSUM_REPORT,
        "results/quality/pre_integration.md",
        "results/quality/post_integration.md",
        "results/tables/descriptive_stats.csv",
        "results/tables/correlations.csv",
        "results/figures",


# ---------------------------------------------------------------- acquisition (Noah Eischen)
rule acquire_eia:
    output: RAW["eia"]
    shell: "python scripts/acquire_eia.py"

rule acquire_fred:
    output: RAW["fred"]
    shell: "python scripts/acquire_fred.py"

rule acquire_acs:
    output: RAW["acs"]
    shell: "python scripts/acquire_acs.py"

rule acquire_cpi:
    output: RAW["cpi"]
    shell: "python scripts/acquire_cpi.py"

rule verify_checksums:
    input:
        raw=list(RAW.values()),
        sums="checksums.sha256",
        script="scripts/verify_checksums.py",
    output: CHECKSUM_REPORT
    shell: "python scripts/verify_checksums.py"

rule profile_raw:
    input:
        raw=list(RAW.values()),
        verified=CHECKSUM_REPORT,
        script="scripts/profile_raw.py",
    output: "results/quality/pre_integration.md"
    shell: "python scripts/profile_raw.py"


# ---------------------------------------------------------------- cleaning (Nishaan Chavla)
rule clean:
    wildcard_constraints: source="eia|fred|acs|cpi"
    input:
        raw=lambda wc: RAW[wc.source],
        verified=CHECKSUM_REPORT,
        script="scripts/clean_{source}.py",
        lookup="scripts/state_codes.py",
    output: "data/interim/{source}_clean.csv"
    shell: "python scripts/clean_{wildcards.source}.py"


# ---------------------------------------------------------------- integration (Nishaan Chavla)
rule integrate:
    input:
        expand("data/interim/{source}_clean.csv", source=["eia", "fred", "acs", "cpi"]),
        script="scripts/integrate.py",
    output:
        merged="data/processed/merged_state_year.csv",
        unmatched="results/quality/unmatched_rows.csv",
    shell: "python scripts/integrate.py"

rule profile_integrated:
    input:
        rules.integrate.output,
        script="scripts/profile_integrated.py",
        lookup="scripts/state_codes.py",
    output: "results/quality/post_integration.md"
    shell: "python scripts/profile_integrated.py"


# ---------------------------------------------------------------- analysis (Noah Cha-Price)
rule analyze:
    input:
        merged="data/processed/merged_state_year.csv",
        quality_ok="results/quality/post_integration.md",
        script="scripts/analyze.py",
    output:
        "results/tables/descriptive_stats.csv",
        "results/tables/correlations.csv",
    shell: "python scripts/analyze.py"

rule plot_figures:
    input:
        merged="data/processed/merged_state_year.csv",
        quality_ok="results/quality/post_integration.md",
        script="scripts/plot_figures.py",
    output: directory("results/figures")
    shell: "python scripts/plot_figures.py"
