from services.auditor import audit_documents
from services.recommender import DomainGap, build_recommendations
from seed import build_sample_site


def test_recommendations_cover_failures_and_authority_gaps():
    html, robots, llms = build_sample_site(7)
    draft = audit_documents([("https://northwind.io/", html)], robots, llms, "https://northwind.io/")
    gaps = [DomainGap(domain="g2.com", citations=8, runs_without_brand=5)]
    items = build_recommendations(draft, gaps)
    ids = [item.id for item in items]
    assert "allow-gptbot" in ids
    assert "schema-product" in ids
    assert "authority-g2-com" in ids
    assert items[0].priority == "P1"


def test_missing_llms_is_a_priority_fix():
    html, robots, _llms = build_sample_site(1)
    draft = audit_documents([("https://northwind.io/", html)], robots, None, "https://northwind.io/")
    items = build_recommendations(draft, [])
    llms = next(item for item in items if item.id == "llms-txt")
    assert llms.priority == "P1"
    assert any("llms.txt" in step for step in llms.steps)


def test_unlisted_names_become_a_task():
    html, robots, llms = build_sample_site(7)
    draft = audit_documents([("https://northwind.io/", html)], robots, llms, "https://northwind.io/")
    items = build_recommendations(draft, [], ["Amplitude", "Mixpanel"])
    task = next(item for item in items if item.id == "unlisted-competitors")
    assert "Amplitude" in task.detail
    assert task.steps
