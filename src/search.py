import re

from duckduckgo_search import DDGS

NOISE_TERMS = (
    "live scores",
    "official site",
    ".com",
    "odds",
    "rankings & news",
)


def looks_like_noise(text):
    lowered_text = text.lower()
    return any(term in lowered_text for term in NOISE_TERMS)


def get_recent_news(sport_name, max_results=3):
    search_query = f"{sport_name} recent tournament results winners news 2026"
    snippets = []

    try:
        with DDGS() as engine:
            hits = engine.text(search_query, max_results=max_results)
            for i, hit in enumerate(hits, start=1):
                headline = hit.get("title", "Untitled")
                body = hit.get("body", "")
                snippet_text = f"Source {i} - {headline}: {body}"
                if looks_like_noise(snippet_text):
                    continue
                snippets.append(re.sub(r"\s+", " ", snippet_text).strip())
    except Exception as exc:
        print(f"Web search failed: {exc}")
        return "No live web results available right now."

    if not snippets:
        return "No live web results found for this sport."

    return "\n\n".join(snippets)
