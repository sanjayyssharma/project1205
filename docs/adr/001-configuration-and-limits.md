# ADR 001: Configuration, limits, and guardrails

## Status

Accepted (Phase 6).

## Context

The product blends a **static Parquet snapshot**, **deterministic filters**, and a **hosted LLM (Groq)**. Operators need predictable behavior for:

- Cost and latency (prompt size, candidate count, tokens).
- Reliability (timeouts, retries on transient Groq errors).
- Safety (no secrets to browsers; minimal PII in logs).

## Decision

1. **Candidate cap** — `MAX_CANDIDATES_FOR_LLM` (default 50, max 500) bounds how many rows enter the LLM after Phase 2. The HTTP API may set `max_candidates` per request within the same bounds.

2. **Prompt size** — `LLM_MAX_PROMPT_CHARS` caps the total size of system + user messages built in `phase3.prompts.build_messages`. If exceeded, the API returns **413** with structured details instead of calling Groq. This ties operational control to the same knob as candidate count without silently truncating model input.

3. **Groq HTTP client** — `GROQ_TIMEOUT_SECONDS` and `GROQ_MAX_RETRIES` are passed to the official OpenAI Python client (Groq-compatible), which applies timeouts and exponential backoff on retriable errors.

4. **Budget mapping** — INR bands for `low` / `medium` / `high` remain implemented in `phase2/budget.py` (single source of truth). Changes are code changes, not env-only toggles, so behavior stays reviewable in PRs.

5. **Rate limiting** — Optional `API_RATE_LIMIT_PER_MINUTE` applies only to `POST /v1/recommendations`, in-process, for basic abuse protection. Production clusters that need global limits should add an edge rate limiter.

6. **Observability** — Request IDs, access logs, optional Groq token usage in logs and JSON responses, and a simple `/metrics` endpoint satisfy Phase 6 “metrics + correlation id” without mandating a specific vendor (Prometheus-compatible text).

## Consequences

- Operators tune caps and timeouts via **environment variables** and restart processes.
- **413** responses require clients (including the Next.js UI) to surface a clear message: reduce scope or ask ops to raise `LLM_MAX_PROMPT_CHARS`.
- Per-process rate limits are **approximate** under horizontal scaling.

## Alternatives considered

- **Circuit breaker** for Groq — deferred; retries + fallback ranking cover most degradation modes today.
- **Centralized metrics (OTEL/Prometheus agent)** — deferred; `/metrics` text is scrape-friendly without extra dependencies.
