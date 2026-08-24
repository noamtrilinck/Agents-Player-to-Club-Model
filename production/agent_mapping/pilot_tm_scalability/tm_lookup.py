"""
PILOT / EXPERIMENT -- not part of the production Stage 2 pipeline.

Tests whether Transfermarkt player profiles can be located and verified
programmatically (HTTP + HTML parsing), rather than via per-player manual
web research, as a scalability test for mapping ~4,000 players to agents.

This module is self-contained and touches nothing outside this pilot
directory: sibling scripts in this folder (not this module itself) READ the
canonical mapping file (mapping_config.MAPPING_CSV --
results/agency_player_mapping_corrected.csv as of 2026-08-20, read-only, to
sample players) and WRITE to files inside pilot_tm_scalability/. Nothing in
this folder writes to the canonical mapping file, the shared warehouse, or
NTS.

Discovery: Transfermarkt's own quick-search endpoint
    https://www.transfermarkt.us/schnellsuche/ergebnis/schnellsuche?query=<name>
returns an HTML results grid for players that already includes name,
position, club, age, nationality, and (when set) the listed agent/agency --
so in many cases no second request is needed to see who the agent is. A
second request (the player's own profile page) is used here anyway, for
every serious candidate, to cross-check the exact date of birth -- the
strongest identity signal -- rather than trusting age-only search-grid data.
"""
import re
import time
import unicodedata
import urllib.parse
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.transfermarkt.us"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}
REQUEST_DELAY_S = 1.5  # polite delay between every outbound request
REQUEST_TIMEOUT_S = 15

NAME_SIM_THRESHOLD = 0.90  # below this, a search-grid row isn't even considered a candidate


# --------------------------------------------------------------------------- name normalization
# (kept local/duplicated rather than importing production's name_matching.py,
# so this experimental module has zero import-time coupling to production code)

def normalize_name(name):
    if name is None:
        return ""
    n = unicodedata.normalize("NFKD", str(name))
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.lower()
    n = re.sub(r"[^a-z0-9\s]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def name_similarity(a, b):
    import difflib
    return difflib.SequenceMatcher(None, a, b).ratio()


def parse_our_dob(dob_str):
    """Our canonical CSV stores DOB as DD/MM/YY (e.g. '09/03/94'). %y follows
    the POSIX pivot (00-68 -> 20xx, 69-99 -> 19xx), which is correct for the
    realistic pro-footballer birth-year range this project covers."""
    if not dob_str or (isinstance(dob_str, float)):
        return None
    try:
        return datetime.strptime(str(dob_str).strip(), "%d/%m/%y").date()
    except ValueError:
        return None


# --------------------------------------------------------------------------- HTTP layer

class RequestLog:
    def __init__(self):
        self.entries = []

    def record(self, url, status, elapsed_s, purpose):
        self.entries.append({
            "url": url, "status": status, "elapsed_s": round(elapsed_s, 2), "purpose": purpose,
        })

    def summary(self):
        n = len(self.entries)
        ok = sum(1 for e in self.entries if e["status"] == 200)
        non200 = [e for e in self.entries if e["status"] != 200]
        total_time = sum(e["elapsed_s"] for e in self.entries)
        return {
            "total_requests": n,
            "status_200": ok,
            "non_200": non200,
            "total_fetch_time_s": round(total_time, 1),
        }


BLOCK_MARKERS = ("captcha", "cf-chl", "just a moment", "access denied", "are you a robot")


def _looks_blocked(html):
    if not html:
        return False
    low = html.lower()
    return any(marker in low for marker in BLOCK_MARKERS)


def fetch(url, purpose, log):
    t0 = time.time()
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_S)
        elapsed = time.time() - t0
        # A CAPTCHA/challenge page can come back as HTTP 200 with a fake-success
        # body -- treat that the same as a real HTTP failure for logging/circuit
        # -breaker purposes, so it isn't silently swallowed as a normal parse miss.
        if resp.status_code == 200 and _looks_blocked(resp.text):
            log.record(url, "BLOCKED_200", elapsed, purpose)
            time.sleep(REQUEST_DELAY_S)
            return None, "BLOCKED_200"
        log.record(url, resp.status_code, elapsed, purpose)
        time.sleep(REQUEST_DELAY_S)
        if resp.status_code != 200:
            return None, resp.status_code
        return resp.text, resp.status_code
    except requests.RequestException as e:
        elapsed = time.time() - t0
        log.record(url, f"ERROR:{type(e).__name__}", elapsed, purpose)
        time.sleep(REQUEST_DELAY_S)
        return None, f"ERROR:{type(e).__name__}"


# --------------------------------------------------------------------------- search-grid parsing

def search_player(name, log):
    q = urllib.parse.quote(name)
    url = f"{BASE}/schnellsuche/ergebnis/schnellsuche?query={q}"
    html, status = fetch(url, f"search:{name}", log)
    if html is None:
        return [], status
    return parse_search_results(html), status


def parse_search_results(html):
    """Returns a list of candidate dicts from the 'Search results for players'
    grid: tm_name, profile_url, club, position, age, agent_name, agent_url."""
    soup = BeautifulSoup(html, "lxml")
    grid = soup.find("div", id="player-grid")
    if grid is None:
        return []
    table = grid.find("table", class_="items")
    if table is None or table.find("tbody") is None:
        return []

    candidates = []
    for tr in table.find("tbody").find_all("tr", recursive=False):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 7:
            continue
        inline = tds[0].find("table", class_="inline-table")
        if inline is None:
            continue
        # Row layout: tr[0] = portrait link (href="#") + the actual name link
        # (the one whose href contains /profil/spieler/); tr[1] = current club link.
        inline_rows = inline.find_all("tr")
        profile_a = inline_rows[0].find("a", href=re.compile(r"/profil/spieler/")) if inline_rows else None
        club_a = inline_rows[1].find("a") if len(inline_rows) > 1 else None

        tm_name = profile_a.get_text(strip=True) if profile_a else None
        profile_url = (BASE + profile_a["href"]) if (profile_a and profile_a.get("href")) else None
        club = club_a.get_text(strip=True) if club_a else None

        position = tds[1].get_text(strip=True)
        age_text = tds[3].get_text(strip=True)
        age = int(age_text) if age_text.isdigit() else None

        agent_a = tds[6].find("a") if len(tds) > 6 else None
        agent_name = agent_a.get_text(strip=True) if agent_a else None
        agent_url = (BASE + agent_a["href"]) if (agent_a and agent_a.get("href")) else None

        if tm_name is None or profile_url is None:
            continue
        candidates.append({
            "tm_name": tm_name, "profile_url": profile_url, "club": club,
            "position": position, "age": age,
            "agent_name": agent_name, "agent_url": agent_url,
        })
    return candidates


# --------------------------------------------------------------------------- profile-page parsing

def fetch_profile_details(profile_url, log):
    """Fetches a player's own profile page and returns
    (dob: date|None, club: str|None, agent_name: str|None, agent_url: str|None, status)."""
    html, status = fetch(profile_url, "profile_verify", log)
    if html is None:
        return None, None, None, None, status
    return parse_profile_details(html) + (status,)


def parse_profile_details(html):
    soup = BeautifulSoup(html, "lxml")

    dob = None
    span = soup.find("span", attrs={"itemprop": "birthDate"})
    if span:
        text = span.get_text(strip=True)
        m = re.match(r"([A-Za-z]{3}) (\d{1,2}), (\d{4})", text)
        if m:
            try:
                dob = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%b %d %Y").date()
            except ValueError:
                dob = None

    club = None
    club_span = soup.find("span", attrs={"itemprop": "affiliation"})
    if club_span:
        a = club_span.find("a")
        club = a.get_text(strip=True) if a else club_span.get_text(strip=True)

    agent_name, agent_url = None, None
    for li in soup.find_all("li", class_="data-header__label"):
        label_text = li.get_text(" ", strip=True)
        if label_text.startswith("Agent"):
            a = li.find("a")
            if a:
                agent_name = a.get_text(strip=True)
                agent_url = (BASE + a["href"]) if a.get("href") else None
            break

    return dob, club, agent_name, agent_url
