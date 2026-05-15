# Problem Statement: AI-Powered Restaurant Recommendations (Zomato-Inspired)

## Summary

Build a restaurant recommendation service that blends structured restaurant data with a large language model (LLM). The system takes explicit user preferences, narrows candidates from a real dataset, then uses the LLM to rank options and explain why each pick fits—similar in spirit to discovery experiences on platforms like Zomato.

---

## Goals

1. Preference-driven search — location, budget band, cuisine, minimum rating, and free-text constraints (e.g. family-friendly, fast service).
2. Data-grounded suggestions — recommendations must come from the ingested dataset, not invented venues.
3. LLM-assisted reasoning — rank candidates and produce short, personalized explanations (optionally a brief summary of the shortlist).
4. Clear presentation — a small set of top results with consistent fields and readable copy.

---

## Dataset

- Source: [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) on Hugging Face.
- Ingestion: load the dataset, normalize or select fields needed for filtering and display (e.g. name, area/city, cuisines, approximate cost, aggregate rating, and any fields useful for “extras” such as ambience or known_for if present).

---

## User inputs (minimum)

| Input | Example | Role |
|--------|---------|------|
| Location | Delhi, Bangalore | Geographic or regional filter |
| Budget | Low / medium / high | Cost band filter |
| Cuisine | Italian, Chinese | Tag or text match on cuisine |
| Minimum rating | e.g. 3.5+ | Quality floor |
| Optional notes | “kid-friendly”, “under 30 minutes” | Passed to the LLM and/or used in heuristics |

---

## System workflow

### 1. Data ingestion and preprocessing

- Fetch or load the Hugging Face dataset.
- Clean missing values, unify cuisine/cost/rating representations, and keep a schema stable enough for both programmatic filters and prompt serialization.

### 2. User preference collection

- Collect the fields above via CLI, web form, API, or equivalent; implementation is open, but the input contract should match this document.

### 3. Integration layer (retrieve → pack → prompt)

- Filter restaurants to a manageable candidate set (e.g. top *N* by rating/relevance after hard filters).
- Serialize structured rows (JSON or tables) for the LLM.
- Prompt the model to rank, compare, and justify—without fabricating restaurants outside the provided list.

### 4. Recommendation engine (LLM)

- Rank the provided candidates.
- Explain each top pick in plain language tied to user preferences and observable fields.
- Optional: one-paragraph summary of the shortlist or trade-offs (e.g. “best value vs. highest rated”).

### 5. Output

For each recommended restaurant, show at least:

- Name  
- Cuisine(s)  
- Rating  
- Estimated cost (or cost band)  
- AI-generated explanation (why this option fits this user)

---

## Non-goals (suggested)

- Owning payments, reservations, or live Zomato APIs unless explicitly extended later.
- Guaranteeing real-time accuracy of prices or hours (dataset is static).

---

## Success criteria

- Recommendations are a subset of the ingested dataset after filtering.
- Explanations reference user preferences and dataset fields, not generic filler.
- End-to-end path: input → filter → LLM → ranked list with explanations.

---

## Open design choices (document in README or an ADR)

- Hosting and stack (e.g. Python + local LLM vs. hosted API).
- How budget maps to dataset cost fields.
- Maximum candidate count sent to the LLM (latency, cost, quality).
