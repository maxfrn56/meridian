from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from config import settings

QUESTION_RE = re.compile(
    r"^(comment|pourquoi|quel(?:le|s|les)?|quels|quelles|quoi|qui|quand|où|ou|combien|"
    r"how|what|why|when|where|which|who|can|does|do|is|are|should)\b",
    re.IGNORECASE,
)
STAT_RE = re.compile(
    r"(?:\b\d+(?:[.,]\d+)?\s?%)|(?:[$€£]\s?\d+(?:[.,]\d+)?)|(?:\b\d+(?:[.,]\d+)?\s?(?:ms|s|min|h|ko|Mo|Go|k|M|x)\b)",
    re.IGNORECASE,
)
SCHEMA_TYPES = ("Organization", "Product", "FAQPage", "Article")
BOTS = ("GPTBot", "PerplexityBot", "ClaudeBot")
USER_AGENT = "MeridianGEOBot/0.1 (audit requested by the site owner)"
MAX_PAGES = 5
MAX_BYTES = 2_000_000


@dataclass
class Check:
    id: str
    label: str
    status: str
    score: int
    detail: str


@dataclass
class AuditDraft:
    url: str
    score: int
    heading_score: int
    schema_score: int
    factual_score: int
    crawler_score: int
    pages_crawled: list[str]
    checks: list[Check]
    found_schema_types: list[str] = field(default_factory=list)
    llms_txt: bool = False
    bots: dict[str, str] = field(default_factory=dict)
    question_ratio: float = 0.0
    factual_detail: str = ""


def clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _schema_types(node: object) -> set[str]:
    found: set[str] = set()
    if isinstance(node, list):
        for item in node:
            found |= _schema_types(item)
        return found
    if not isinstance(node, dict):
        return found
    raw = node.get("@type", [])
    if isinstance(raw, str):
        found.add(raw)
    elif isinstance(raw, list):
        found.update(str(item) for item in raw)
    graph = node.get("@graph")
    if graph is not None:
        found |= _schema_types(graph)
    return found


def _normalize_schema(types: set[str]) -> set[str]:
    normalized = set(types)
    if "NewsArticle" in types or "BlogPosting" in types:
        normalized.add("Article")
    return normalized


def analyze_headings(soup: BeautifulSoup) -> tuple[int, Check]:
    headings = soup.find_all(["h2", "h3"])
    if not headings:
        return 0, Check(
            id="headings",
            label="Titres en forme de question",
            status="fail",
            score=0,
            detail="Aucun H2 ou H3. Les moteurs citent plus volontiers une page structurée en questions.",
        )
    questions = 0
    for heading in headings:
        text = heading.get_text(" ", strip=True)
        if text.endswith("?") or QUESTION_RE.match(text):
            questions += 1
    score = clamp(100 * questions / len(headings))
    status = "pass" if score >= 70 else "warn" if score >= 40 else "fail"
    return score, Check(
        id="headings",
        label="Titres en forme de question",
        status=status,
        score=score,
        detail=f"{questions} titre(s) interrogatif(s) sur {len(headings)} H2/H3.",
    )


def analyze_schema(soup: BeautifulSoup) -> tuple[int, Check, list[str]]:
    blocks = soup.find_all("script", attrs={"type": "application/ld+json"})
    types: set[str] = set()
    invalid = 0
    for block in blocks:
        raw = block.string or block.get_text() or ""
        try:
            types |= _normalize_schema(_schema_types(json.loads(raw)))
        except json.JSONDecodeError:
            invalid += 1
    found = [name for name in SCHEMA_TYPES if name in types]
    score = clamp(100 * len(found) / len(SCHEMA_TYPES))
    if invalid and score > 25:
        score = 25
    if not blocks:
        detail = "Aucun bloc JSON-LD. Organization, Product, FAQPage et Article sont absents."
        status = "fail"
    elif invalid and not found:
        detail = f"{invalid} bloc(s) JSON-LD illisible(s)."
        status = "fail"
    else:
        missing = [name for name in SCHEMA_TYPES if name not in found]
        detail = (
            f"Types trouvés : {', '.join(found) or 'aucun'}."
            + (f" Manquants : {', '.join(missing)}." if missing else " Couverture complète.")
        )
        if invalid:
            detail += f" {invalid} bloc(s) JSON-LD invalide(s)."
        status = "pass" if score >= 75 else "warn" if score >= 25 else "fail"
    return score, Check(id="schema", label="Données structurées JSON-LD", status=status, score=score, detail=detail), found


def analyze_factual(soup: BeautifulSoup) -> tuple[int, Check]:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    stats = len(STAT_RE.findall(text))
    items = len(soup.find_all("li"))
    tables = len(soup.find_all("table"))
    score = clamp(min(40, stats * 8) + min(30, items * 3) + (30 if tables else 0))
    status = "pass" if score >= 70 else "warn" if score >= 40 else "fail"
    detail = f"{stats} statistique(s), {items} puce(s), {tables} tableau(x)."
    return score, Check(id="factual", label="Densité factuelle", status=status, score=score, detail=detail)


def parse_robots(content: str) -> dict[str, str]:
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []

    def flush() -> None:
        nonlocal agents, rules
        if agents:
            groups.append((agents, rules))
        agents = []
        rules = []

    for raw in content.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            flush()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if rules:
                flush()
            agents.append(value)
        elif key in {"allow", "disallow"}:
            rules.append((key, value))
    flush()

    def state_of(ruleset: list[tuple[str, str]]) -> str:
        disallows_root = any(key == "disallow" and value == "/" for key, value in ruleset)
        allows_root = any(key == "allow" and value in {"/", ""} for key, value in ruleset)
        if disallows_root and not allows_root:
            return "disallowed"
        return "allowed"

    statuses: dict[str, str] = {}
    for bot in BOTS:
        specific = None
        wildcard = None
        for group_agents, group_rules in groups:
            names = [agent.lower() for agent in group_agents]
            state = state_of(group_rules)
            if bot.lower() in names:
                specific = state
            elif "*" in names and wildcard is None:
                wildcard = state
        statuses[bot] = specific or wildcard or "unspecified"
    return statuses


def analyze_crawlers(robots: str | None, llms: str | None) -> tuple[int, list[Check], dict[str, str], bool]:
    checks: list[Check] = []
    llms_ok = bool(llms and llms.strip())
    checks.append(
        Check(
            id="llms-txt",
            label="Fichier llms.txt",
            status="pass" if llms_ok else "fail",
            score=100 if llms_ok else 0,
            detail="Présent à la racine du domaine." if llms_ok else "Introuvable. Publiez /llms.txt pour orienter les moteurs génératifs.",
        )
    )
    bots = parse_robots(robots or "")
    points = 25 if llms_ok else 0
    for bot, status in bots.items():
        allowed = status != "disallowed"
        points += 25 if allowed else 0
        if robots is None:
            detail = "robots.txt introuvable : les robots restent autorisés par défaut."
            check_status = "warn"
        elif status == "disallowed":
            detail = f"{bot} est interdit par robots.txt."
            check_status = "fail"
        elif status == "unspecified":
            detail = f"{bot} n'est pas nommé : accès autorisé par défaut."
            check_status = "pass"
        else:
            detail = f"{bot} est autorisé."
            check_status = "pass"
        checks.append(
            Check(
                id=f"bot-{bot.lower()}",
                label=f"Accès {bot}",
                status=check_status,
                score=100 if allowed else 0,
                detail=detail,
            )
        )
    return clamp(points), checks, bots, llms_ok


def _average(values: list[int]) -> int:
    if not values:
        return 0
    return clamp(sum(values) / len(values))


def audit_documents(
    pages: list[tuple[str, str]],
    robots: str | None,
    llms: str | None,
    start_url: str,
) -> AuditDraft:
    heading_scores: list[int] = []
    factual_scores: list[int] = []
    schema_found: set[str] = set()
    heading_checks: list[Check] = []
    factual_checks: list[Check] = []
    schema_checks: list[Check] = []
    crawled: list[str] = []

    for url, html in pages:
        crawled.append(url)
        soup = BeautifulSoup(html, "html.parser")
        heading_score, heading_check = analyze_headings(soup)
        schema_score, schema_check, found = analyze_schema(BeautifulSoup(html, "html.parser"))
        factual_score, factual_check = analyze_factual(BeautifulSoup(html, "html.parser"))
        heading_scores.append(heading_score)
        factual_scores.append(factual_score)
        schema_found.update(found)
        heading_checks.append(heading_check)
        schema_checks.append(schema_check)
        factual_checks.append(factual_check)
        del schema_score

    heading_score = _average(heading_scores)
    factual_score = _average(factual_scores)
    schema_score = clamp(100 * len(schema_found) / len(SCHEMA_TYPES))
    crawler_score, crawler_checks, bots, llms_ok = analyze_crawlers(robots, llms)
    score = clamp(
        heading_score * 0.20 + schema_score * 0.30 + factual_score * 0.25 + crawler_score * 0.25
    )

    heading_detail = " · ".join(f"{page}: {check.detail}" for page, check in zip(crawled, heading_checks))
    factual_detail = " · ".join(check.detail for check in factual_checks)
    missing = [name for name in SCHEMA_TYPES if name not in schema_found]
    schema_detail = (
        f"Types trouvés sur le site : {', '.join(sorted(schema_found)) or 'aucun'}."
        + (f" Manquants : {', '.join(missing)}." if missing else "")
    )
    schema_status = "pass" if schema_score >= 75 else "warn" if schema_score >= 25 else "fail"
    heading_status = "pass" if heading_score >= 70 else "warn" if heading_score >= 40 else "fail"
    factual_status = "pass" if factual_score >= 70 else "warn" if factual_score >= 40 else "fail"

    checks = [
        Check("headings", "Titres en forme de question", heading_status, heading_score, heading_detail),
        Check("schema", "Données structurées JSON-LD", schema_status, schema_score, schema_detail),
        Check("factual", "Densité factuelle", factual_status, factual_score, factual_detail),
        *crawler_checks,
    ]
    questions = heading_score / 100
    return AuditDraft(
        url=start_url,
        score=score,
        heading_score=heading_score,
        schema_score=schema_score,
        factual_score=factual_score,
        crawler_score=crawler_score,
        pages_crawled=crawled,
        checks=checks,
        found_schema_types=sorted(schema_found),
        llms_txt=llms_ok,
        bots=bots,
        question_ratio=questions,
        factual_detail=factual_detail,
    )


def _private_host(hostname: str) -> bool:
    lowered = hostname.lower().rstrip(".")
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".local"):
        return True
    try:
        import ipaddress

        ip = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved


def assert_public_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL invalide. Utilisez une adresse http(s) publique.")
    if _private_host(parsed.hostname):
        raise ValueError("L'audit ne cible pas les adresses locales ou privées.")
    return url


def discover_links(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    origin = urlparse(page_url)
    found: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(page_url, anchor["href"]).split("#")[0]
        parsed = urlparse(href)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc != origin.netloc:
            continue
        if parsed.path.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".svg", ".webp")):
            continue
        if href not in found and href.rstrip("/") != page_url.rstrip("/"):
            found.append(href)

    def rank(url: str) -> tuple[int, str]:
        path = urlparse(url).path.lower()
        for index, key in enumerate(("faq", "pricing", "tarif", "product", "produit", "blog", "docs", "about")):
            if key in path:
                return index, path
        return 50, path

    return sorted(set(found), key=rank)[: MAX_PAGES - 1]


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        response = await client.get(url)
    except httpx.HTTPError:
        return None
    if response.status_code >= 400:
        return None
    return response.text[:MAX_BYTES]


async def _render_with_playwright(url: str) -> str | None:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            return await page.content()
        finally:
            await browser.close()


async def fetch_html(client: httpx.AsyncClient, url: str) -> str:
    response = await client.get(url)
    response.raise_for_status()
    html = response.text[:MAX_BYTES]
    text_length = len(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    if settings.use_playwright and text_length < 200:
        rendered = await _render_with_playwright(url)
        if rendered:
            return rendered[:MAX_BYTES]
    return html


async def crawl_site(start_url: str) -> AuditDraft:
    start_url = assert_public_http_url(start_url if "://" in start_url else f"https://{start_url}")
    origin = f"{urlparse(start_url).scheme}://{urlparse(start_url).netloc}"
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    timeout = httpx.Timeout(20.0, connect=8.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True) as client:
        try:
            first = await fetch_html(client, start_url)
        except httpx.HTTPError as error:
            raise ValueError(f"Impossible d'atteindre {start_url} ({error.__class__.__name__}).") from error
        collected = [(start_url, first)]
        for link in discover_links(first, start_url):
            try:
                html = await fetch_html(client, link)
            except httpx.HTTPError:
                continue
            collected.append((link, html))
        robots = await _fetch_text(client, urljoin(origin, "/robots.txt"))
        llms = await _fetch_text(client, urljoin(origin, "/llms.txt"))
    return audit_documents(collected, robots, llms, start_url)
