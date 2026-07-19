"""
The core of the RAG agent. Pulls context from both knowledge
sources, builds a grounded prompt, calls the LLM, then parses the
structured reply into question objects the UI can render.
"""

import json
import re
from urllib import error, request

from src.config import gemini_api_key
from src.database import find_relevant_facts
from src.search import get_recent_news

GEMINI_MODEL = "gemini-flash-latest"
GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

LOW_VALUE_WEB_PATTERNS = (
    r"flashscore",
    r"livescore",
    r"scoreboard",
    r"odds",
    r"betting",
    r"fixtures",
    r"match results",
    r"live scores",
)


def is_weak_web_context(web_context):
    """Flags web snippets that are too generic or score-table heavy to trust."""
    if not web_context:
        return True

    lowered_context = web_context.lower()
    if "no live web results" in lowered_context or "no live web results found" in lowered_context:
        return True

    lines = [line.strip() for line in web_context.splitlines() if line.strip()]
    if not lines:
        return True

    low_value_hits = 0
    for line in lines:
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in LOW_VALUE_WEB_PATTERNS):
            low_value_hits += 1

    return low_value_hits >= max(1, len(lines) // 2)


def build_context(sport):
    """Gathers and merges facts from ChromaDB and the live web."""
    db_query = f"{sport} history championships records rules"
    stored_facts = find_relevant_facts(sport, db_query, max_results=3)
    db_context = "\n".join(stored_facts) if stored_facts else "No offline facts found."

    web_context = get_recent_news(sport)
    use_web_context = not is_weak_web_context(web_context)

    if not use_web_context:
        return (
            f"=== KNOWN HISTORICAL FACTS ===\n{db_context}\n\n"
            "=== LIVE WEB RESULTS ===\n"
            "Live web results were too generic or score-table heavy to trust, so ignore them and generate only from the historical facts above."
        )

    return (
        f"=== KNOWN HISTORICAL FACTS ===\n{db_context}\n\n"
        f"=== VERIFIED LIVE WEB RESULTS ===\n{web_context}"
    )


def build_prompt(sport, difficulty, question_count=4):
    context = build_context(sport)

    system_instruction = (
        "You are a sports quiz writer. Only use facts present in the context below. "
        "Prefer verified historical facts, official tournament records, and named winners over generic live-score snippets. "
        "Do not invent stats, scores, people, dates, or winners that are not supported by the context. "
        "If the live web section is labeled weak or unavailable, ignore it completely and use only the historical facts. "
        "Avoid writing questions from score tables, odds pages, or generic ranking snippets. "
        "Never write a question about a website, app, or news source itself — only about real sports events, records, or players. "
        "If the context is thin, keep the questions simple and factual rather than guessing.\n\n"
        f"CONTEXT:\n{context}"
    )

    user_instruction = (
        f"Generate exactly {question_count} unique multiple-choice questions about {sport} "
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

    return context, system_instruction, user_instruction


def parse_quiz_json(raw_text):
    """Turns the LLM reply into a list of normalized question dicts."""
    payload = json.loads(raw_text)
    questions = payload.get("questions", [])
    parsed_questions = []

    for item in questions:
        options = item.get("options", {})
        parsed_questions.append({
            "question": item.get("question", "").strip(),
            "options": {
                "A": options.get("A", "").strip(),
                "B": options.get("B", "").strip(),
                "C": options.get("C", "").strip(),
                "D": options.get("D", "").strip(),
            },
            "correct": item.get("correct_answer", "").strip(),
            "explanation": item.get("explanation", "").strip(),
        })

    return parsed_questions


def tokenize_words(text):
    """Converts text to a lowercase word set for overlap checks."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def explanations_are_too_similar(explanation_a, explanation_b, threshold=0.7):
    """Checks whether two explanations overlap enough to be treated as duplicates."""
    words_a = tokenize_words(explanation_a)
    words_b = tokenize_words(explanation_b)

    if not words_a or not words_b:
        return False

    overlap_ratio = len(words_a & words_b) / min(len(words_a), len(words_b))
    return overlap_ratio >= threshold


def drop_duplicate_questions(questions):
    """Keeps the first question and drops near-duplicates by explanation overlap."""
    unique_questions = []
    for question in questions:
        explanation = question.get("explanation", "")
        duplicate_found = any(
            explanations_are_too_similar(explanation, kept.get("explanation", ""))
            for kept in unique_questions
        )
        if not duplicate_found:
            unique_questions.append(question)
    return unique_questions


def call_gemini(system_instruction, user_instruction):
    """Calls Gemini directly through the REST API and returns raw JSON text."""
    if not gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    payload = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_instruction}],
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json",
        },
    }

    body = json.dumps(payload).encode("utf-8")
    http_request = request.Request(
        f"{GEMINI_ENDPOINT}?key={gemini_api_key}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(http_request, timeout=60) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Gemini request failed: {exc.code} {details}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Gemini request could not connect: {exc.reason}") from exc

    candidates = response_payload.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()

    if not text:
        raise RuntimeError("Gemini returned an empty response.")

    return text


def generate_quiz(sport, difficulty, question_count=4):
    """
    Runs the full pipeline: retrieve context, prompt the LLM, and
    return both the parsed questions and the raw context used
    (so the UI can show what grounded the answers).
    """
    context_used, system_instruction, user_instruction = build_prompt(
        sport,
        difficulty,
        question_count,
    )

    raw_text = call_gemini(system_instruction, user_instruction)
    questions = parse_quiz_json(raw_text)
    questions = drop_duplicate_questions(questions)

    return questions, context_used
