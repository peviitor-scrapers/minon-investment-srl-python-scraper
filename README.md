[![Oportunitati si Cariere](https://github.com/peviitor-scrapers/minon-investment-srl-python-scraper/actions/workflows/job-seeker-ro-spider.yml/badge.svg)](https://github.com/peviitor-scrapers/minon-investment-srl-python-scraper/actions/workflows/job-seeker-ro-spider.yml)
[![Automation Tests](https://github.com/peviitor-scrapers/minon-investment-srl-python-scraper/actions/workflows/automation-testing.yml/badge.svg)](https://github.com/peviitor-scrapers/minon-investment-srl-python-scraper/actions/workflows/automation-testing.yml)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Website](https://img.shields.io/website?url=https%3A%2F%2Fpeviitor.ro&label=peviitor.ro)](https://peviitor.ro)
[![API](https://img.shields.io/website?url=https%3A%2F%2Fapi.peviitor.ro%2F&label=api.peviitor.ro)](https://api.peviitor.ro/)
[![GitHub Pages](https://img.shields.io/github/deployments/peviitor-scrapers/minon-investment-srl-python-scraper/github-pages?label=GitHub%20Pages)](https://peviitor-scrapers.github.io/minon-investment-srl-python-scraper/)

# job_seeker_ro_spider — MINON INVESTMENT S.R.L. Scraper

**job_seeker_ro_spider** — a scraper for MINON INVESTMENT S.R.L. jobs in Romania. It collects announcements published by the company on [ANOFM](https://mediere.anofm.ro/app/module/mediere/jobs), [jobRapid](https://www.jobrapid.ro/), [BeBee](https://bebee.com/), [Emprego](https://emprego.com/) and [Horeo](https://horeo.ro/), then publishes them to [peviitor.ro](https://peviitor.ro) through the Peviitor API.

ANOFM is the authoritative source (`employer_tax_code=9864469`). The other portals republish the same ANOFM offer on their own detail pages; because peviitor.ro identifies jobs by unique URL, each distinct URL is published as a distinct job. Portals found during discovery without their own job-detail URLs (Ziarul Muncii, Careerjet, Jooble, BestJobs) add no listings.

> **CIF note.** The company's CUI is `9864469` (7 digits). ANOFM expects that raw form, while the Peviitor API requires an 8-digit id, so the scraper stores `09864469` (zero-padded) in the company and job cores.

> **🌱 Derived scraper.** This repository is derived from [variant-agro-srl-python-scraper](https://github.com/peviitor-scrapers/variant-agro-srl-python-scraper).

## Overview

The project automates the daily collection of MINON INVESTMENT jobs in Romania, keeping the peviitor.ro board up to date with the latest career opportunities.

## Features

- Extracts jobs from ANOFM (`mediere.anofm.ro`) by employer CUI
- Extracts jobRapid postings by company-name search and JSON-LD `JobPosting` blocks
- Derives BeBee/Horeo detail URLs from ANOFM ids and reads Emprego job links from its company profile; each page's JSON-LD hiring organization is verified
- Deduplicates by URL across all five sources; distinct URLs remain distinct jobs
- Publishes non-personal fields stated by the source: location, salary, tags, work mode and expiry date
- Never stores job descriptions, contact names, emails or phone numbers (GDPR data minimization)
- Validates the company via CUIScan (legal name and address, by CIF) and CUIFirma (brand search)
- **Company cache** — does not hit the APIs on every scrape
- **Stale cache / config fallback** when CUIScan is unavailable
- Cross-validates against the Peviitor API
- Deletes stale jobs from peviitor when they are no longer live (scoped to this scraper's five URL prefixes)
- Stores to the Peviitor API (job core + company core)
- Generates `docs/jobs.md` automatically — accessible on GitHub Pages
- **Company identity in a single file** (`scraper/config/company.json`)
- GitHub Actions: daily scrape + automated testing (unit, integration, e2e, consistency)
- Identifies itself through the User-Agent: `job_seeker_ro_spider`

## Local setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest tests/unit tests/consistency   # offline checks
.venv/bin/python -m scraper.index                         # full scrape + publish
```

## License

Copyright (c) 2026 Alexandra Ifrim

Licensed under the [MIT License](LICENSE).

## Managed By

This project is managed by [ASOCIATIA OPORTUNITATI SI CARIERE](https://oportunitatisicariere.ro) and used as a web scraper for the [peviitor.ro](https://peviitor.ro) job board project.

## Disclaimer

This scraper is designed for educational purposes and legitimate job data aggregation for the Romanian job market.
