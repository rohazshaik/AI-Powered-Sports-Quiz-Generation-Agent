"""
Pulls fresh, recent sports info from the live web so quizzes aren't
limited to whatever's in our small offline JSON file.
"""

import re
from duckduckgo_search import DDGS

REJECT_SNIPPET_TERMS = (
    "live scores",
    "official site",
    ".com",
    "odds",
    "rankings & news",
)


def should_reject_snippet(text):
    """Rejects snippet text that looks like website promo or generic listing copy."""
    lowered_text = text.lower()
    return any(term in lowered_text for term in REJECT_SNIPPET_TERMS)


def get_recent_news(sport_name, max_results=3):
    """
    Searches DuckDuckGo for recent news about a sport and returns a
    single text block combining the top snippets.
    """
    search_query = f"{sport_name} recent tournament results winners news 2026"
    snippets = []

    try:
        with DDGS() as search_engine:
            hits = search_engine.text(search_query, max_results=max_results)
            for i, hit in enumerate(hits, start=1):
                headline = hit.get("title", "Untitled")
                body = hit.get("body", "")
                snippet_text = f"Source {i} - {headline}: {body}"
                if should_reject_snippet(snippet_text):
                    continue
                # Keep only snippets likely to contain real sports facts.
                cleaned_text = re.sub(r"\s+", " ", snippet_text).strip()
                snippets.append(cleaned_text)
    except Exception as error:
        print(f"Web search failed: {error}")
        return "No live web results available right now."

    if not snippets:
        return "No live web results found for this sport."

    return "\n\n".join(snippets)
