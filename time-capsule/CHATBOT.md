# Discourse Dial — Chatbot Plan (Option B)

Static frontend on GitHub Pages + RAG/LLM API on a self-hosted cloud instance.

## Constraints

GitHub Pages cannot run backend code or hold secrets. It **can** serve static assets and run browser JavaScript that calls external APIs.

| Limitation | Implication |
|------------|-------------|
| No server on GH Pages | LLM API keys must live on the cloud instance only |
| Corpus size | Cannot load all years into the browser at once for RAG |
| Talk detail UI | Keep loading per-year JSON from `data/unified/` on GH Pages |

## Architecture

```
┌─────────────────────────────┐         ┌──────────────────────────────┐
│  GitHub Pages               │  POST   │  Cloud instance              │
│  Discourse Dial (app.js)    │ ──────► │  /discourse-dial/chat        │
│  + data/unified/*.json      │ ◄────── │    → retriever → LLM         │
│    (talk detail modal)      │  JSON   │    → citations               │
└─────────────────────────────┘         └──────────────────────────────┘
```

**GH Pages responsibilities**

- Timeline, prophet card, talk detail overlay (unchanged)
- Chat UI (bubbles, quick questions, loading states)
- `fetch()` to the chat API

**Cloud instance responsibilities**

- HTTPS endpoint with CORS for GH Pages origin(s)
- Retrieve relevant talk chunks (RAG)
- Call LLM with context; return answer + citations
- Rate limiting and API key storage

## API contract (v1)

### `POST /discourse-dial/chat`

**Request**

```json
{
  "question": "What did Lorenzo Snow teach about tithing?",
  "year": 1900,
  "history": []
}
```

- `year` — selected slider year (v1 retrieval scoped to this year)
- `history` — optional last N turns for follow-up questions (v2)

**Response**

```json
{
  "answer": "In 1900, several speakers addressed...",
  "sources": [
    {
      "year": 1900,
      "session": "April",
      "speaker": "Lorenzo Snow",
      "title": "Talk title",
      "excerpt": "First paragraph or snippet...",
      "talkIndex": 3
    }
  ]
}
```

`talkIndex` maps to the index in that year's talk array so the frontend can open the existing talk detail modal.

## RAG phases

### Phase 1 — Keyword retrieval (ship first)

- Ingest `data/unified/*.json` on the server (sync from `~/conference-reports` merge pipeline)
- Rank chunks by keyword overlap (same idea as client `searchTalks`, server-side)
- Prompt: answer only from excerpts; cite speaker and year; say when unsure

No embeddings required. Validates the full loop quickly.

### Phase 2 — Better retrieval

- Chunk talks into paragraphs (~500 tokens)
- BM25 (e.g. Python `rank-bm25`) or embeddings (SQLite/pgvector)
- Improves semantic-style queries ("faith", "repentance") without exact keyword match

### Phase 3 — Cross-year / thematic

- Index all years; optional `year` filter on the request
- Enables questions like "How did teachings on X change over time?"

## Server requirements

- **HTTPS** (Let's Encrypt)
- **CORS** — allow `https://drewgalbraith.github.io` and any custom domain
- **Rate limiting** — per IP (e.g. 20 requests/hour) to control LLM cost
- **Env vars** — `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or similar (never in frontend)
- **Optional** — lightweight shared header secret (blocks casual abuse; not truly secret in JS)

Suggested stack if starting fresh: **FastAPI + uvicorn** (fits existing Python corpus tooling). Use whatever is already running on the instance if easier.

## Frontend integration

Changes mostly in `app.js` `handleChat`:

1. Show user bubble (already done)
2. `POST` to chat API with `{ question, year: currentYear }`
3. Show loading state in agent bubble
4. Render `answer` in agent bubble
5. Render `sources` as clickable talk cards (reuse `.talk-result` + `showTalkDetail`)
6. Keep quick-question chips — they send the same API with canned `question` strings
7. Keep local keyword search as **fallback** if the API is unreachable

## Corpus sync

Single source of truth, two consumers:

```bash
# Existing pipeline
python3 ~/conference-reports/merge-corpus.py
cp ~/conference-reports/unified/*.json time-capsule/data/unified/
```

On the server: rsync, git pull, or cron job to rebuild the search index from the same unified JSON files whenever the corpus updates.

- **GH Pages** — JSON for talk detail modals
- **Chat API** — search index for RAG

## Build order

1. **Stub API** — echo response + fake citations; prove CORS and frontend wiring
2. **Keyword RAG** — real retrieval for one year + real LLM answers
3. **Citations** — wire `sources` to talk detail overlay
4. **History** — pass last 2–3 turns for follow-ups
5. **Better index** — BM25 or embeddings; then cross-year if needed

## Security & cost notes

- Never commit API keys; use server environment variables only
- Log questions and token usage, not secrets
- Instruct the model to quote cautiously — older talks are OCR'd and may have errors
- Prefer answers that cite specific talks (speaker, year, session)

## Open decisions

- [ ] Cloud stack (Python / Node / Docker / nginx reverse proxy)
- [ ] LLM provider (OpenAI, Anthropic, etc.)
- [ ] v1 scope: selected year only vs cross-year
- [ ] API base URL and domain
- [ ] Auth beyond CORS + rate limit (optional header secret)
