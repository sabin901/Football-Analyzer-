"""Explicit publication allowlist. Accessibility is not a data license."""

from pathlib import Path
import json
import re
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OPEN = ROOT / "data/open"
RESULTS = OPEN / "results"
WORKBENCH = OPEN / "workbench"
SOURCES = {
    "openfootball": {
        "name": "OpenFootball",
        "license": "CC0-1.0",
        "url": "https://github.com/openfootball/football.json",
        "license_url": "https://github.com/openfootball/football.json/blob/master/LICENSE.md",
        "attribution": "OpenFootball contributors",
        "uses": ["display", "redistribution", "analysis", "commercial"],
    },
    "wyscout_research": {
        "name": "Pappalardo / Wyscout research dataset",
        "license": "CC-BY-4.0",
        "url": "https://doi.org/10.6084/m9.figshare.c.4415000",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Luca Pappalardo, Paolo Cintia, Alessio Rossi, Emanuele Massucco, Paolo Ferragina, Dino Pedreschi and Fosca Giannotti (2019). A public data set of spatio-temporal match events in soccer. Scientific Data 6, 236. Data provided by Wyscout. DOI: 10.1038/s41597-019-0247-7.",
        "uses": ["display", "redistribution", "analysis", "commercial"],
        "changes": "Normalized names and coordinates; derived action counts, regulation-minute estimates and grids. Original event and match IDs retained. No affiliation or endorsement implied.",
    },
}


def provenance(source_id):
    source = SOURCES[source_id]
    return {
        "source_id": source_id,
        "license": source["license"],
        "source": source["name"],
        "license_url": source["license_url"],
        "attribution": source["attribution"],
    }


def validate_public(payload):
    """Fail closed on missing provenance, denied sources or altered licenses."""
    sid = payload.get("source_id")
    if sid not in SOURCES or payload.get("license") != SOURCES[sid]["license"]:
        raise ValueError(f"Unapproved publication provenance: {sid!r}")
    if not payload.get("source_url") or not payload.get("source_sha256"):
        raise ValueError("Publication requires source URL and SHA-256")
    if not re.fullmatch(r"[a-f0-9]{64}", payload["source_sha256"]):
        raise ValueError("Invalid source fingerprint")
    url = urlparse(payload["source_url"])
    hosts = {
        "openfootball": {"raw.githubusercontent.com", "github.com"},
        "wyscout_research": {"ndownloader.figshare.com", "api.figshare.com"},
    }
    if url.scheme != "https" or url.hostname not in hosts[sid]:
        raise ValueError("Source URL is outside the approved provider")
    for match in payload.get("matches", []):
        if match.get("result_source") not in (None, "OpenFootball"):
            raise ValueError("Mixed-source result is not permitted")
    return payload


def load(path):
    return json.loads(Path(path).read_text(encoding="utf8"))
