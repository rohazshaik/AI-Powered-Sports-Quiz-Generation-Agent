# AI-Powered Sports Quiz Generation Agent

This project is a Streamlit app that generates grounded sports quizzes using Retrieval-Augmented Generation (RAG). It combines local sports facts stored in ChromaDB with live web snippets from DuckDuckGo, then asks Gemini to return a strict JSON quiz response.

## What it does

1. You choose a sport and difficulty level.
2. The app retrieves related historic facts from ChromaDB.
3. The app fetches recent live sports snippets from DuckDuckGo.
4. The LLM generates 4 to 5 multiple-choice questions using only that context.
5. Streamlit displays each question with answer feedback and explanation.

## Setup

### 1. Create and activate a virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Add your API key

Create a file named `.env` in the project root and add:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

## Run the app

```bash
streamlit run app.py
```

On first launch, the app seeds the local ChromaDB database from `data/sports_facts.json` and stores it in `chroma_db/`.

## Project structure

```text
sports-quiz-agent/
├── README.md
├── requirements.txt
├── app.py
├── data/
│   └── sports_facts.json
└── src/
    ├── __init__.py
    ├── config.py
    ├── database.py
    ├── generator.py
    └── search.py
```

## Notes

- ChromaDB uses a local embedding model, so there is no separate embedding API cost.
- If web search fails, the app still generates quizzes from the local database.
- The quiz output is strict JSON, which makes parsing and UI rendering more reliable.
- Gemini is called directly over the REST API, so there is no separate AI SDK dependency.
