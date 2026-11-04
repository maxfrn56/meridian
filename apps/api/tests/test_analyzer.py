from services.analyzer import Citation, Entity, brand_is_cited, citation_rate, extract_mentions, named_organisations, share_of_voice

BRAND = Entity("Northwind", "northwind.io", "brand")
RIVAL = Entity("Lumenboard", "lumenboard.com", "competitor")


def test_mentions_keep_reading_order_and_sentiment():
    text = (
        "1. Lumenboard (lumenboard.com) — jugé coûteux pour une petite équipe. "
        "2. Northwind (northwind.io) — souvent recommandé pour des tableaux clairs."
    )
    mentions = extract_mentions(text, [BRAND, RIVAL])
    assert [item.entity_name for item in mentions] == ["Lumenboard", "Northwind"]
    assert [item.position for item in mentions] == [1, 2]
    northwind = mentions[1]
    lumenboard = mentions[0]
    assert northwind.sentiment > 0
    assert lumenboard.sentiment < 0
    assert brand_is_cited(mentions, [], BRAND)


def test_domain_citation_counts_when_the_name_is_absent():
    citations = [Citation("https://northwind.io/blog/analytics", "northwind.io", "Blog", 1)]
    assert brand_is_cited([], citations, BRAND)


def test_named_organisations_keep_name_and_domain():
    text = "1. Amplitude (amplitude.com) — souvent cité.\n2. Northwind (northwind.io) — recommandé."
    assert named_organisations(text) == [("Amplitude", "amplitude.com"), ("Northwind", "northwind.io")]


def test_share_and_citation_rate():
    assert share_of_voice({"Northwind": 1, "Lumenboard": 3})["Northwind"] == 0.25
    assert citation_rate([True, False, True, False]) == 0.5
    assert citation_rate([]) is None
