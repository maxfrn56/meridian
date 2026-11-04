from services.auditor import analyze_schema, audit_documents, parse_robots
from bs4 import BeautifulSoup

from seed import build_sample_site


def test_robots_parser_respects_specific_groups():
    robots = (
        "User-agent: *\nAllow: /\n\n"
        "User-agent: GPTBot\nDisallow: /\n\n"
        "User-agent: PerplexityBot\nAllow: /\n"
    )
    status = parse_robots(robots)
    assert status["GPTBot"] == "disallowed"
    assert status["PerplexityBot"] == "allowed"
    assert status["ClaudeBot"] == "allowed"


def test_invalid_jsonld_is_flagged():
    html = '<script type="application/ld+json">{not json}</script>'
    score, check, found = analyze_schema(BeautifulSoup(html, "html.parser"))
    assert score == 0
    assert found == []
    assert check.status == "fail"


def test_sample_site_score_improves_and_stays_bounded():
    early = audit_documents([("https://northwind.io/", build_sample_site(0)[0])], *build_sample_site(0)[1:], "https://northwind.io/")
    latest_html, latest_robots, latest_llms = build_sample_site(7)
    latest = audit_documents([("https://northwind.io/", latest_html)], latest_robots, latest_llms, "https://northwind.io/")
    assert 0 <= early.score < latest.score <= 100
    assert "GPTBot" in latest.bots and latest.bots["GPTBot"] == "disallowed"
    assert "Product" not in latest.found_schema_types
    assert latest.llms_txt is True
