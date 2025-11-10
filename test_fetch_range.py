#!/usr/bin/env python3
import os
from datamule import Portfolio

# Always set a proper User-Agent for SEC queries
os.environ["SEC_API_USER_AGENT"] = "AravKasliwal sec_filings_project_main (your_email@example.com)"

COMPANIES = {
    "T-Mobile US": "0001283699",
    "Coinbase Global": "0001679788",
    "AT&T": "0000732717"
}

# Handle base + amended forms separately
FORM_TYPES = ["10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"]
DATE_RANGE = ("2020-01-01", "2025-12-31")

for name, cik in COMPANIES.items():
    portfolio = Portfolio(cik)
    print(f"\n=== Downloading filings for {name} ({cik}), {DATE_RANGE[0]} → {DATE_RANGE[1]} ===")

    for form in FORM_TYPES:
        try:
            portfolio.download_submissions(
                submission_type=form,
                cik=cik,
                filing_date=DATE_RANGE,
            )

            print(f"\n--- Parsing {form} documents for {name} ---")
            for document in portfolio.document_type(form):
                document.parse()
                print("got path:", document.path)

                if document.path.endswith(("txt", "htm", "html")):
                    outpath = document.path.replace(":", "_") + ".json"
                    document.write_json(outpath)
                    print("outpath:", outpath)

                    # Clean up intermediate tar files
                    tar_file = document.path.split("::")[0]
                    if os.path.exists(tar_file):
                        os.remove(tar_file)
                        print(f"🗑 Deleted {tar_file}")

        except Exception as e:
            print(f"⚠️ Skipped {form} for {name} due to error: {e}")

print("\n✅ Done. Only JSON files remain.")