# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- BeBee, Emprego and Horeo as third/fourth/fifth sources. BeBee and Horeo
  detail URLs are derived from ANOFM ids; Emprego job links come from its
  company profile. All JSON-LD `JobPosting` blocks are checked against the
  hiring organization before publication (#1).
- Generic JSON-LD parsing that handles plain objects, arrays and `@graph`,
  including posting date, salary, location and expiry date (#1).
- `_anofm_cif()` helper: ANOFM is queried with the raw CUI `9864469` while
  Peviitor stores the 8-digit id `09864469` (#1).

### Changed
- Company identity changed to MINON INVESTMENT S.R.L.; repository links,
  config, docs and test fixtures rebranded (#1).
- Source identifier is now
  `mediere.anofm.ro, jobrapid.ro, bebee.com, emprego.com, horeo.ro` (#1).
- Stale-job scope extended to all five source URL prefixes (#1).

### Fixed
- Emprego pages are decoded as UTF-8, preserving Romanian diacritics in
  location and title fields (#1).

## [1.0.0] - 2026-11-19

### Added
- Python scraper for **MINON INVESTMENT S.R.L.** (CUI `9864469`), reading jobs from ANOFM (`mediere.anofm.ro`).
- Publisher to peviitor v1 API: company upsert, job upload, stale-job delete.
- ANAF company validation with CUIScan fallback and cache.
- ANOFM job search mirroring the Node.js template.
- `validate_jobs.py` CLI for head/content URL validation.
- Unit, integration, e2e, and consistency tests.
- GitHub Actions workflows: `job-seeker-ro-spider`, `automation-testing`, deep-validate, recovery.
- GitHub Pages (`docs/`) with generated `jobs.md` and `company.json`.
- AI documentation under `ai/`.

### Fixed
- Location normalization: common spellings (`Bucuresti`, `Turda`, etc.) and case/diacritic variants are no longer dropped to `România`.
- Stale-job deletion is scoped to this scraper's job URLs, so jobs published by other peviitor scrapers under the same CIF are never removed.
- E2E `EXPECTED_MIN_JOBS` and integration tests reflect ANOFM and CIF `09864469`.
