# How This Project Works (RAG + ChromaDB Explained)

This file exists separately from the README so the *concepts* are explained
clearly, not just the setup steps. Use this to write your own assignment
documentation, or to explain the project in an interview.

## 1. The core idea: don't let the AI guess

A plain LLM call for "write me a tennis quiz" relies entirely on what the
model memorized during training. It might be right, or it might
confidently make up a fact (hallucination) — there's no way to tell from
the output alone.

**RAG (Retrieval-Augmented Generation)** fixes this by doing two things
*before* calling the LLM:
1. Retrieve real facts from a trusted source.
2. Force the LLM to only use those facts, not its own memory.

So the LLM's job shrinks from "know sports trivia" to "phrase these
specific facts as quiz questions" — a much narrower, more checkable task.

## 2. Where the two knowledge sources come from

This project pulls facts from two places, for two different reasons:

| Source | What it's good for | What it's bad for |
|---|---|---|
| ChromaDB (offline JSON) | Stable historical facts (who won what, when) | Anything from the last few months |
| DuckDuckGo (live search) | Recent news, current events | Noisy — often pulls in site descriptions, not facts |

Neither source is trustworthy alone — the offline data goes stale, and the
live search is noisy. Combining them, with a filter on the noisy one, is
the actual design decision worth explaining if asked "why two sources?"

## 3. What ChromaDB is actually doing

ChromaDB is a **vector database**. The short version:

- Every fact gets converted into a list of numbers (an "embedding") that
  represents its *meaning*, not its exact words.
- Facts with similar meaning end up close together in that number-space.
- When you search, your query also gets converted into numbers, and
  ChromaDB returns whichever stored facts are numerically closest.

This is different from a normal database search (`WHERE fact LIKE '%cup%'`)
because it matches on meaning, not exact keywords. Asking "who won the
tournament" can still match a fact that says "claimed the title" even
though no words overlap.

**In this project specifically:**
- `load_facts_into_db()` in `database.py` is the one-time step that turns
  `sports_facts.json` into embeddings and stores them.
- `search_facts()` is the lookup step — it also filters by the `sport`
  metadata field first, so a Tennis query can never accidentally return a
  Cricket fact, even if the wording is similar.

## 4. What "grounding" means in the prompt

Look at `make_prompt()` in `generator.py`. The system message doesn't just
ask for a quiz — it explicitly says:

- Only use facts in the given context
- Don't invent stats, names, or dates
- Ignore the web section entirely if it's flagged as weak

This is the actual grounding mechanism. It's not a separate system — it's
just very specific instructions plus the context text attached to every
request. If asked "how do you prevent hallucination," the honest answer
is: *you can't fully prevent it, you constrain it* — by narrowing what the
model is allowed to draw from and telling it explicitly not to guess.

## 5. Why the web results get filtered twice

There are two separate filtering steps, and they catch different things:

1. **`search.py` → `looks_like_junk()`** — rejects one snippet at a time,
   right when it's fetched, based on keyword match (`.com`, `odds`, etc.)
2. **`generator.py` → `looks_thin()`** — looks at *all* the snippets that
   survived step 1, together, and decides whether the whole batch is still
   too weak to trust (e.g. only 1 of 3 snippets was rejected, but the
   other 2 are still score-table spam).

Two layers because a single snippet can look fine on its own but the
whole batch can still be low quality once you see it together.

## 6. How to describe this in one paragraph (interview-ready)

> "The app retrieves grounding facts from two sources — a local ChromaDB
> vector store for stable historical facts, and a live DuckDuckGo search
> for recent news. The web results get filtered for quality before being
> combined with the database facts into a single context block. That
> context is passed to Gemini with an explicit instruction to only use
> what's provided, which is what keeps the quiz factually grounded
> instead of relying on the model's own training data."

## 7. Tips for writing your own documentation

- Explain the *why* before the *how* — a grader already knows what
  ChromaDB is; they want to know why you used metadata filtering
  specifically, or why you filter web results twice.
- Use one small example end-to-end (e.g. trace a single "Tennis, Hard"
  request through every file) instead of describing every function in
  isolation — it reads as understanding, not just documentation-copying.
- Call out limitations honestly (e.g. "if Gemini doesn't return valid
  JSON, this currently isn't caught") — graders read this as engineering
  maturity, not as a weakness.
