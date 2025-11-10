#!/usr/bin/env python3
from datamule import Portfolio

# 23andMe CIK (not ticker!)
CIK = "0001804591"

# Choose which forms you want
FORM_TYPES = ["10-K", "10-Q", "8-K"]

portfolio = Portfolio("23andme")

# Download filings using CIK instead of ticker
for form in FORM_TYPES:
    print(f"\n--- Downloading {form} for 23andMe ---")
    portfolio.download_submissions(submission_type=form, cik=CIK)

# Parse each document
for form in FORM_TYPES:
    print(f"\n--- Parsing {form} documents ---")
    for document in portfolio.document_type(form):
        document.parse()
        print("got path:", document.path)

        if document.path.endswith(("txt", "htm", "html")):
            outpath = document.path.replace(":", "_") + ".json"
            print("outpath:", outpath)
            document.write_json(outpath)

print("\nAll done. JSON files are in the '23andme/' folder.")