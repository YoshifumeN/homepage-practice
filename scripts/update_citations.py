import json
import re
import urllib.request
from datetime import date
from pathlib import Path

API_URL = (
    "https://api.semanticscholar.org/"
    "graph/v1/paper/batch?fields=title,citationCount,externalIds"
)

HTML_FILE = Path("publications.html")
DATA_FILE = Path("data/citations.json")

DOIS = [
    "10.2166/ws.2025.094",
    "10.1016/j.watres.2024.121396",
    "10.1016/j.watres.2023.120559",
    "10.1016/j.watres.2021.117550",
    "10.1016/j.watres.2020.116786",
    "10.1016/j.watres.2020.116093",
    "10.1016/j.watres.2018.10.008",
    "10.1016/j.watres.2018.03.046",
]


def load_old_data():
    if not DATA_FILE.exists():
        return {}

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_citations():
    request_body = json.dumps(
        {"ids": [f"DOI:{doi}" for doi in DOIS]}
    ).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "citation-updater/1.0",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def make_display_date(iso_date):
    d = date.fromisoformat(iso_date)

    months = [
        "Jan", "Feb", "Mar", "Apr",
        "May", "Jun", "Jul", "Aug",
        "Sep", "Oct", "Nov", "Dec",
    ]

    return f"{months[d.month - 1]} {d.day}, {d.year}"


def update_html(data):
    html = HTML_FILE.read_text(encoding="utf-8")

    for doi, record in data.items():
        count = record.get("count")
        retrieved = record.get("retrieved")

        if count is None or retrieved is None:
            continue

        display_date = make_display_date(retrieved)

        replacement = (
            f'<div class="citation-info" data-doi="{doi}">'
            f'Citations: {count} '
            f'(Semantic Scholar, retrieved {display_date})'
            f'</div>'
        )

        pattern = (
            rf'<div class="citation-info" '
            rf'data-doi="{re.escape(doi)}">.*?</div>'
        )

        html = re.sub(
            pattern,
            replacement,
            html,
            flags=re.DOTALL,
        )

    HTML_FILE.write_text(html, encoding="utf-8")


def main():
    old_data = load_old_data()

    # Always start from the previous successful values.
    new_data = old_data.copy()

    try:
        papers = fetch_citations()

        today = date.today().isoformat()

        for paper in papers:
            if not paper:
                continue

            external_ids = paper.get("externalIds") or {}
            doi = external_ids.get("DOI")
            count = paper.get("citationCount")

            if doi is None or count is None:
                continue

            doi = doi.lower()

            if doi not in DOIS:
                continue

            new_data[doi] = {
                "count": int(count),
                "retrieved": today,
            }

    except Exception as error:
        # Do not destroy old citation data when the API fails.
        print(f"Semantic Scholar update failed: {error}")
        print("Previous citation data will be retained.")

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            new_data,
            f,
            indent=2,
            ensure_ascii=False,
        )

    update_html(new_data)


if __name__ == "__main__":
    main()
