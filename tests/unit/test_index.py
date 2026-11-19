"""Unit tests for the multi-source index pipeline."""

import json

from scraper import index


def test_map_to_job_model_adds_company_and_status():
    index.COMPANY_NAME = "MINON INVESTMENT S.R.L."
    raw = {
        "url": "https://mediere.anofm.ro/app/module/mediere/job/1",
        "title": "Lucrător comercial",
        "location": ["Voluntari"],
    }
    job = index.map_to_job_model(raw, "9864469")
    assert job["company"] == "MINON INVESTMENT S.R.L."
    assert job["cif"] == "9864469"
    assert job["status"] == "scraped"
    assert job["location"] == ["Voluntari"]
    assert job["date"]


def test_map_to_job_model_without_location():
    raw = {"url": "https://mediere.anofm.ro/app/module/mediere/job/2",
           "title": "Vânzător"}
    job = index.map_to_job_model(raw, "9864469", company_name="MINON INVESTMENT S.R.L.")
    assert "location" not in job


def test_map_to_job_model_keeps_optional_fields():
    raw = {
        "url": "https://mediere.anofm.ro/app/module/mediere/job/3",
        "title": "SUDOR",
        "salary": "4000-5000 RON",
        "tags": ["sudor", "cu-norma-intreaga"],
        "workmode": "on-site",
        "expirationdate": "2027-01-31",
    }
    job = index.map_to_job_model(raw, "9864469", company_name="MINON INVESTMENT S.R.L.")
    assert job["salary"] == "4000-5000 RON"
    assert job["tags"] == ["sudor", "cu-norma-intreaga"]
    assert job["workmode"] == "on-site"
    assert job["expirationdate"] == "2027-01-31"


def test_transform_jobs_for_solr_uppercases_company():
    jobs = [{"url": "https://x/job", "title": "Test", "location": ["Cluj-Napoca"]}]
    transformed = index.transform_jobs_for_solr({"company": "Minon Investment S.R.L.", "jobs": jobs})
    assert transformed["company"] == "MINON INVESTMENT S.R.L."
    assert transformed["jobs"][0]["location"] == ["Cluj-Napoca"]


def test_transform_jobs_for_solr_location_fallback():
    jobs = [{"url": "https://x/job", "title": "Test", "location": []}]
    transformed = index.transform_jobs_for_solr({"company": "MINON INVESTMENT S.R.L.", "jobs": jobs})
    assert transformed["jobs"][0]["location"] == ["România"]


def test_transform_jobs_for_solr_missing_location_fallback():
    jobs = [{"url": "https://x/job", "title": "Test"}]
    transformed = index.transform_jobs_for_solr({"company": "MINON INVESTMENT S.R.L.", "jobs": jobs})
    assert transformed["jobs"][0]["location"] == ["România"]


def _stub_main(monkeypatch, tmp_path, raw_jobs):
    monkeypatch.setattr(index, "query_solr", lambda cif: {"numFound": 0, "docs": []})
    monkeypatch.setattr(index, "upsert_jobs", lambda jobs: None)
    monkeypatch.setattr(index, "delete_job_by_url", lambda url: None)
    monkeypatch.setattr(index, "upsert_company", lambda cfg: None)
    monkeypatch.setattr(index, "validate_and_get_company", lambda: {
        "company": "MINON INVESTMENT S.R.L.", "cif": "09864469", "address": "VOLUNTARI"})
    monkeypatch.setattr(index, "search_anofm_jobs", lambda cif: raw_jobs)
    monkeypatch.setattr(index, "search_jobrapid", lambda company: [])
    monkeypatch.setattr(index, "search_jsonld_mirrors", lambda jobs, company: [])
    monkeypatch.setattr(index, "drop_dead_urls", lambda jobs: jobs)
    return tmp_path


def test_main_writes_summary(tmp_path, monkeypatch):
    fake_jobs = [
        {"url": f"https://mediere.anofm.ro/app/module/mediere/job/{i}",
         "title": f"Job {i}", "location": ["Voluntari"]}
        for i in range(3)
    ]
    root = _stub_main(monkeypatch, tmp_path, fake_jobs)

    index.main(root=root)

    out = tmp_path / "scraper" / "jobs.json"
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["jobs"]) == 3
    assert data["company"] == "MINON INVESTMENT S.R.L."
    assert (tmp_path / "docs" / "jobs.md").exists()


def test_main_preserves_enriched_fields(tmp_path, monkeypatch):
    fake_jobs = [{
        "url": "https://mediere.anofm.ro/app/module/mediere/job/3447055",
        "title": "SUDOR",
        "location": ["BUCURESTI"],
        "salary": "4000-5000 RON",
        "tags": ["sudor", "cu-norma-intreaga"],
        "workmode": "on-site",
        "expirationdate": "2027-01-31",
    }]
    root = _stub_main(monkeypatch, tmp_path, fake_jobs)

    index.main(root=root)

    data = json.loads((tmp_path / "scraper" / "jobs.json").read_text(encoding="utf-8"))
    job = data["jobs"][0]
    assert job["salary"] == "4000-5000 RON"
    assert job["tags"] == ["sudor", "cu-norma-intreaga"]
    assert job["workmode"] == "on-site"
    assert job["expirationdate"] == "2027-01-31"


def test_main_dedupes_anofm_urls(tmp_path, monkeypatch):
    job = {"url": "https://mediere.anofm.ro/app/module/mediere/job/1", "title": "Job"}
    root = _stub_main(monkeypatch, tmp_path, [job, dict(job)])

    index.main(root=root)

    data = json.loads((tmp_path / "scraper" / "jobs.json").read_text(encoding="utf-8"))
    assert len(data["jobs"]) == 1


def test_main_canary_aborts_before_any_write(tmp_path, monkeypatch):
    upserted = []
    root = _stub_main(monkeypatch, tmp_path, [])
    monkeypatch.setattr(index, "upsert_jobs", lambda jobs: upserted.append(jobs))
    monkeypatch.setattr(index, "upsert_company", lambda cfg: (_ for _ in ()).throw(AssertionError("no write")))

    index.main(root=root)

    assert upserted == []
    assert not (tmp_path / "scraper" / "jobs.json").exists()


def test_drop_dead_urls_drops_soft_404(monkeypatch):
    good = {"url": "https://x/good", "title": "Good"}
    old = {"url": "https://x/old", "title": "Old"}
    monkeypatch.setattr(index, "validate_by_content", lambda url: {
        "url": url, "status": "active" if url.endswith("good") else "expired",
        "http_status": 200, "error": None})

    assert index.drop_dead_urls([good, old]) == [good]


def _anofm_row(job_id=1, **overrides):
    row = {
        "id": job_id,
        "employer_tax_code": "9864469",
        "occupation": "SUDOR",
        "address_locality_name": "București > MUNICIPIUL BUCURESTI > BUCURESTI",
        "minimum_salary": "4000.00",
        "maximum_salary": "5000.00",
        "work_regime_name": "Sediu",
        "job_expiry_date": "2099-01-31",
        "job_domain_name": "Producție și logistică",
        "job_posting_target_name": "PCLM",
        "work_type_name": "Cu normă întreagă",
        "contact_name": "PERSOANA DE CONTACT",
        "contact_email": "contact@example.com",
        "contact_phone": "0700000000",
        "description": "Descriere care nu trebuie stocată",
    }
    row.update(overrides)
    return row


def test_search_anofm_jobs_maps_non_personal_fields(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"rows": [_anofm_row()]}

    jobs = index.search_anofm_jobs("9864469")

    assert len(jobs) == 1
    job = jobs[0]
    assert job["url"] == "https://mediere.anofm.ro/app/module/mediere/job/1"
    assert job["title"] == "SUDOR"
    assert job["location"] == ["BUCURESTI"]
    assert job["salary"] == "4000-5000 RON"
    assert job["workmode"] == "on-site"
    assert job["expirationdate"] == "2099-01-31"
    assert "productie-si-logistica" in job["tags"]
    assert "cu-norma-intreaga" in job["tags"]
    assert not {"contact_name", "contact_email", "contact_phone", "description"} & job.keys()


def test_search_anofm_jobs_sends_cif_filter(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"rows": []}

    index.search_anofm_jobs("9864469")

    payload = mock_post.call_args.kwargs["json"]
    assert payload["employer_tax_code"] == "9864469"
    assert payload["current"] == 1
    assert payload["rowCount"] == 250
    assert payload["sort"] == {"created_at": "desc"}


def test_search_anofm_jobs_dedupes_and_filters_wrong_cif(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"rows": [
        _anofm_row(1), _anofm_row(1), _anofm_row(2, employer_tax_code="99999999"),
    ]}

    jobs = index.search_anofm_jobs("9864469")

    assert [job["url"].rsplit("/", 1)[-1] for job in jobs] == ["1"]


def test_search_anofm_jobs_skips_expired_and_placeholders(mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"rows": [
        _anofm_row(1, job_expiry_date="2020-01-01"),
        _anofm_row(2, occupation="N/A"),
        _anofm_row(3),
    ]}

    jobs = index.search_anofm_jobs("9864469")

    assert len(jobs) == 1
    assert jobs[0]["url"].endswith("/3")


def test_search_anofm_jobs_empty_on_http_error(mock_post):
    mock_post.return_value.status_code = 503
    assert index.search_anofm_jobs("9864469") == []


def test_search_anofm_jobs_empty_on_network_error(mock_post):
    mock_post.side_effect = RuntimeError("network")
    assert index.search_anofm_jobs("9864469") == []


def test_salary_variants():
    assert index._salary({"minimum_salary": "4325.00"}) == "4325 RON"
    assert index._salary({"maximum_salary": "6000.00"}) is None
    assert index._salary({"minimum_salary": "abc"}) is None


def test_anofm_cif_strips_peviitor_padding():
    assert index._anofm_cif("09864469") == "9864469"
    assert index._anofm_cif("41873878") == "41873878"


def test_workmode_variants():
    assert index._workmode({"work_regime_name": "Telemuncă"}) == "remote"
    assert index._workmode({"work_regime_name": "Muncă la distanță"}) == "remote"
    assert index._workmode({"work_regime_name": "Hibrid"}) == "hybrid"
    assert index._workmode({"work_regime_name": "Sediu"}) == "on-site"
    assert index._workmode({}) is None


def test_tags_are_lowercase_without_diacritics_and_capped():
    row = {field: "Școală profesională" for field in index.TAG_SOURCE_FIELDS}
    assert index._tags(row) == ["scoala-profesionala"]
    many = {field: f"tag {i}" for i, field in enumerate(index.TAG_SOURCE_FIELDS)}
    assert len(index._tags(many)) <= 20


def test_jobrapid_salary_range_and_single():
    base = {"currency": "RON", "value": {"minValue": 3250, "maxValue": 4000}}
    assert index._jobrapid_salary(base) == "3250-4000 RON"
    assert index._jobrapid_salary({"currency": "EUR", "value": {"maxValue": 100}}) == "100 EUR"
    assert index._jobrapid_salary(None) is None


def test_parse_jobrapid_posting_extracts_fields():
    posting = {
        "@type": "JobPosting",
        "url": "https://www.jobrapid.ro/locuri-de-munca/sudor-in-targu-jiu-1732973.html",
        "title": "Sudor",
        "datePosted": "2026-11-13T14:36:03+02:00",
        "baseSalary": {"currency": "RON", "value": {"minValue": 4000, "maxValue": 5000}},
        "jobLocation": {"address": {"addressLocality": "Voluntari", "addressRegion": "Ilfov"}},
    }
    page = f'<script type="application/ld+json">{json.dumps(posting)}</script>'
    job = index.parse_jobrapid_posting(page, "https://www.jobrapid.ro/fallback")

    assert job["url"].endswith("1732973.html")
    assert job["title"] == "Sudor"
    assert job["location"] == ["Voluntari"]
    assert job["salary"] == "4000-5000 RON"
    assert job["date"] == "2026-11-13T12:36:03Z"


def test_search_jobrapid_filters_by_company_and_fetches_details(mock_post, mock_get):
    def card(company, href):
        return (f'<div class="container_lista_continut" '
                f'data-company="{company}" data-href="{href}"></div>')

    mock_post.return_value.text = (
        card("Minon Investment SRL", "/locuri-de-munca/a.html")
        + card("Other Firm SRL", "/locuri-de-munca/b.html")
    )
    posting = {
        "@type": "JobPosting",
        "url": "https://www.jobrapid.ro/locuri-de-munca/a.html",
        "title": "Sudor",
    }
    mock_get.return_value.text = f'<script type="application/ld+json">{json.dumps(posting)}</script>'

    jobs = index.search_jobrapid("Minon Investment")

    assert len(jobs) == 1
    assert jobs[0]["url"].endswith("/a.html")
    assert mock_get.call_count == 1


def test_main_includes_jobrapid_jobs_and_dedupes_by_url(tmp_path, monkeypatch):
    anofm = [{"url": "https://mediere.anofm.ro/app/module/mediere/job/1", "title": "SUDOR"}]
    jobrapid = [
        {"url": "https://www.jobrapid.ro/locuri-de-munca/sudor-in-targu-jiu-1732973.html",
         "title": "Sudor", "salary": "4000-5000 RON"},
        {"url": "https://mediere.anofm.ro/app/module/mediere/job/1", "title": "duplicate"},
    ]
    root = _stub_main(monkeypatch, tmp_path, anofm)
    monkeypatch.setattr(index, "search_jobrapid", lambda company: jobrapid)

    index.main(root=root)

    data = json.loads((tmp_path / "scraper" / "jobs.json").read_text(encoding="utf-8"))
    assert len(data["jobs"]) == 2
    urls = [job["url"] for job in data["jobs"]]
    assert len(set(urls)) == 2
    assert any("jobrapid.ro" in url for url in urls)


def _ldjson_page(posting, graph=False):
    if graph:
        posting = {"@context": "https://schema.org", "@graph": [posting]}
    return f'<script type="application/ld+json">{json.dumps(posting)}</script>'


def test_parse_jsonld_posting_supports_graph_and_employer_check():
    posting = {
        "@type": "JobPosting",
        "url": "https://emprego.com/jobs/barista-uuid",
        "title": "Barman Preparator de Cafea (Barista)",
        "datePosted": "2026-11-16",
        "validThrough": "2026-11-27T00:00:00+00:00",
        "baseSalary": {"currency": "RON", "value": {"minValue": 2800, "maxValue": 3500}},
        "jobLocation": {"address": {"addressLocality": "București"}},
        "hiringOrganization": {"@type": "Organization", "name": "MINON INVESTMENT SRL"},
    }
    job = index.parse_jsonld_posting(
        _ldjson_page(posting, graph=True), "https://emprego.com/jobs/fallback",
        "MINON INVESTMENT S.R.L.")

    assert job["url"] == "https://emprego.com/jobs/barista-uuid"
    assert job["title"] == "Barman Preparator de Cafea (Barista)"
    assert job["location"] == ["București"]
    assert job["salary"] == "2800-3500 RON"
    assert job["date"] == "2026-11-16T00:00:00Z"
    assert job["expirationdate"] == "2026-11-27"
    assert index.parse_jsonld_posting(
        _ldjson_page(posting, graph=True), "https://emprego.com/jobs/fallback", "ALTĂ FIRMĂ SRL") is None


def test_search_jsonld_mirrors_builds_derived_urls_and_dedupes(mock_get):
    anofm = [{
        "url": "https://mediere.anofm.ro/app/module/mediere/job/3448506",
        "title": "barman preparator de cafea (barista)",
        "location": ["BUCURESTI SECTORUL 1"],
    }]

    def posting(url):
        return {
            "@type": "JobPosting", "url": url, "title": "barman preparator de cafea (barista)",
            "hiringOrganization": {"name": "MINON INVESTMENT S.R.L."},
        }

    class _Response:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            pass

    def fake_get(url, **kwargs):
        if url == index.EMPREGO_COMPANY_URL:
            return _Response('<a href="/jobs/barman-barista-uuid">job</a>')
        if "bebee.com/ro/jobs/" in url:
            expected = ("https://bebee.com/ro/jobs/barman-preparator-de-cafea-barista-"
                        "minon-investment-srl-bucuresti--techmap_ro_3448506")
            return _Response(_ldjson_page(posting(expected)) if url == expected else "")
        if "horeo.ro/job/" in url:
            return _Response(_ldjson_page(posting(url)))
        if "emprego.com/jobs/" in url:
            return _Response(_ldjson_page(posting(url), graph=True))
        return _Response("")

    mock_get.side_effect = fake_get

    jobs = index.search_jsonld_mirrors(anofm, "MINON INVESTMENT S.R.L.")

    assert len(jobs) == 3
    urls = {job["url"] for job in jobs}
    assert ("https://bebee.com/ro/jobs/barman-preparator-de-cafea-barista-"
            "minon-investment-srl-bucuresti--techmap_ro_3448506") in urls
    assert "https://horeo.ro/job/barman-preparator-de-cafea-barista-3448506" in urls
    assert "https://emprego.com/jobs/barman-barista-uuid" in urls
