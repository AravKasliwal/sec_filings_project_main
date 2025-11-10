#!/usr/bin/env python3
from datamule import Portfolio

# Create a "Portfolio" folder to store filings
portfolio = Portfolio("10k")

# Download 10-K filings for Cisco (ticker symbol: CSCO)
portfolio.download_submissions(submission_type='10-K', ticker='CSCO')

# Loop through each document and save as JSON
for document in portfolio.document_type('10-K'):
    document.parse()
    print("got path:", document.path)

    if document.path.endswith("txt") or document.path.endswith("htm"):
        outpath = document.path.replace(":", "_") + ".json"
        print("outpath:", outpath)
        document.write_json(outpath)