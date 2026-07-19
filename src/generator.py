import json
import re
from urllib import error, request

from src.config import gemini_api_key
from src.database import find_relevant_facts
from src.search import get_recent_news

MODEL = "gemini-flash-latest"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

WEAK_PATTERNS = (
    r"flashscore",
    r"livescore",
    r"scoreboard",
    r"odds",
    r"betting",
    r"fixtures",
    r"match results",
    r"live scores",
)


def looks_thin(web_text):
    if not web_text:
        return True

    lowered = web_text.lower()
    if "no live web results" in lowered:
        return True

    lines = [l.strip() for l in web_text.splitlines() if l.strip()]
    if not lines:
        return True

    junk_count = sum(
        1 for line in lines if any(re.search(p, line, re.IGNORECASE) for p in WEAK_PATTERNS)
    )
    return junk_count >= max(1, len(lines) // 2)


def get_context(sport):
    db_query = f"{sport} history championships records rules"
    stored = find_relevant_facts(sport, db_query, max_results=3)
    db_context = "\n".join(stored) if stored else "No offline facts found."

    web_context = get_recent_news(sport)

    if looks_thin(web_context):
        return (
            f"=== KNOWN HISTORICAL FACTS ===\n{db_context}\n\n"
            "=== LIVE WEB RESULTS ===\n"
            "Live web results were too generic or score-table heavy to trust, "
            "so ignore them and generate only from the historical facts above."
        )

    return (
        f"=== KNOWN HISTORICAL FACTS ===\n{db_context}\n\n"
        f"=== VERIFIED LIVE WEB RESULTS ===\n{web_context}"
    )


def make_prompt(sport, difficulty, q_count=4):
    context = get_context(sport)

    system_msg = (
        "You are a sports quiz writer. Only use facts present in the context below. "
        "Prefer verified historical facts, official tournament records, and named winners over generic live-score snippets. "
        "Do not invent stats, scores, people, dates, or winners that are not supported by the context. "
        "If the live web section is labeled weak or unavailable, ignore it completely and use only the historical facts. "
        "Avoid writing questions from score tables, odds pages, or generic ranking snippets. "
        "Never write a question about a website, app, or news source itself — only about real sports events, records, or players. "
        "If the context is thin, keep the questions simple and factual rather than guessing.\n\n"
        f"CONTEXT:\n{context}"
    )

    user_msg = (
        f"Generate exactly {q_count} unique multiple-choice questions about {sport} "
        f"at {difficulty} difficulty.\n\n"
        "Return only valid JSON with this shape:\n"
        "{\n"
        '  "sport": "...",\n'
        '  "difficulty": "...",\n'
        '  "questions": [\n'
        "    {\n"
        '      "question": "...",\n'
        '      "options": {"A": "...", "B": "...", "C": "...", "D": "..."},\n'
        '      "correct_answer": "A",\n'
        '      "explanation": "..."\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Use exactly 4 answer options labeled A, B, C, and D.\n"
        "- Make the questions fresh and not repetitive.\n"
        "- Keep explanations short and tied to the retrieved context.\n"
        "- Prefer official records, tournament history, and governing-body facts over live score pages.\n"
        "- Do not include markdown fences or extra commentary."
    )

    return context, system_msg, user_msg


def parse_reply(raw_text):
    payload = json.loads(raw_text)
    items = payload.get("questions", [])
    out = []

    for item in items:
        opts = item.get("options", {})
        out.append({
            "question": item.get("question", "").strip(),
            "options": {
                "A": opts.get("A", "").strip(),
                "B": opts.get("B", "").strip(),
                "C": opts.get("C", "").strip(),
                "D": opts.get("D", "").strip(),
            },
            "correct": item.get("correct_answer", "").strip(),
            "explanation": item.get("explanation", "").strip(),
        })

    return out


def to_word_set(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def too_similar(exp_a, exp_b, threshold=0.7):
    words_a = to_word_set(exp_a)
    words_b = to_word_set(exp_b)

    if not words_a or not words_b:
        return False

    overlap = len(words_a & words_b) / min(len(words_a), len(words_b))
    return overlap >= threshold


def dedupe(questions):
    kept = []
    for q in questions:
        exp = q.get("explanation", "")
        is_dupe = any(too_similar(exp, k.get("explanation", "")) for k in kept)
        if not is_dupe:
            kept.append(q)
    return kept


def ask_gemini(system_msg, user_msg):
    if not gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    payload = {
        "systemInstruction": {"parts": [{"text": system_msg}]},
        "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json",
        },
    }

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{ENDPOINT}?key={gemini_api_key}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini request failed: {exc.code} {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Gemini request could not connect: {exc.reason}") from exc

    candidates = resp_data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()

    if not text:
        raise RuntimeError("Gemini returned an empty response.")

    return text


def generate_quiz(sport, difficulty, q_count=4):
    context_used, system_msg, user_msg = make_prompt(sport, difficulty, q_count)

    raw = ask_gemini(system_msg, user_msg)
    questions = parse_reply(raw)
    questions = dedupe(questions)

    return questions, context_used
