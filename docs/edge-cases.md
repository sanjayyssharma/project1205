# Edge cases: AI restaurant recommendations

This document lists **detailed edge cases** for the system described in [problemstatement.md](./problemstatement.md), mapped to the build phases in [architecture-phases.md](./architecture-phases.md). Use it for test design, API contracts, and incident playbooks.

**Conventions**

- **Phase tags** (P0–P5) point to where the case is owned or first surfaced.
- **Expected behavior** is normative for a production-minded MVP unless marked optional.
- **Risk** summarizes user trust, correctness, or operability impact if unhandled.

---

## 1. Cross-cutting (multiple phases)

| # | Scenario | Expected behavior | Risk |
|---|----------|-------------------|------|
| C1 | Hugging Face or LLM provider returns HTTP 5xx or TLS errors | Surface a clear “upstream unavailable” message; do not return partial fake results; optional bounded retry with backoff (P5). | Users see wrong data or endless spinners. |
| C2 | Partial pipeline success (e.g. data loaded, LLM fails) | API returns structured error; UI shows recoverable state; logs include stage and correlation id. | Silent degradation breaks success criteria (grounded explanations). |
| C3 | Very large `MAX_CANDIDATES_FOR_LLM` or huge serialized prompt | Enforce hard cap before LLM call; reject or trim with documented policy; log truncation. | Context overflow, cost blow-up, timeouts. |
| C4 | Dataset revision changes without code update | Pin revision or snapshot (P1); detect schema drift in ingest tests; fail fast with actionable message. | Subtle filter bugs or wrong column mapping. |
| C5 | Clock skew, locale, or Unicode in restaurant names and user text | Normalize Unicode NFC; consistent string comparison for joins LLM output → canonical rows; document locale for number formatting in UI. | Mismatched joins, “ghost” validation failures. |

---

## 2. Phase 0 — Foundations

| # | Edge case | Detail | Expected behavior | Risk |
|---|-----------|--------|-------------------|------|
| P0.1 | Missing `.env` or required env vars | e.g. API key absent in dev | Fail at startup or first request with explicit variable name; `.env.example` lists all keys. | Cryptic runtime failures. |
| P0.2 | Invalid config types | `MAX_CANDIDATES_FOR_LLM=abc` | Validate on load; reject with parse error. | Undefined cap behavior. |
| P0.3 | Wrong runtime version | Python or Node mismatch | Document supported versions; CI checks version. | “Works on my machine” breakage. |
| P0.4 | Secrets committed or logged | Copy-paste from tutorials | Pre-commit or CI secret scan; never log raw keys. | Credential leak. |

---

## 3. Phase 1 — Data plane

### 3.1 Ingest and availability

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P1.1 | HF dataset download interrupted | Resume or clean retry; checksum or size check; user-visible “data not ready” if startup depends on cache. | Corrupt local cache, random parse errors. |
| P1.2 | Rate limiting from Hugging Face | Backoff; cache artifact; optional offline mode using Parquet/JSONL snapshot. | Flaky CI and local dev. |
| P1.3 | Empty dataset or zero rows after split | Ingest asserts non-empty for required split; fail with message. | Empty filters propagate to confusing UX. |
| P1.4 | Dataset larger than RAM | Stream or chunked read; document memory profile; optional pre-aggregated snapshot for dev. | OOM kills. |

### 3.2 Schema, types, and normalization

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P1.5 | Missing `rating`, `cost`, `cuisine`, or `location` in many rows | Define per-field policy: drop row, impute band, or keep with “unknown” and exclude from strict filters; document in ADR. | Silent exclusion skews results. |
| P1.6 | Rating out of expected range | e.g. 0–5 vs 0–10; strings like `"4.2/5"` | Parse and clamp or normalize to a single scale used everywhere (filters + UI + LLM). | Wrong min-rating semantics. |
| P1.7 | Cost as free text | `"$$"`, `"for two"`, `"800"` | Map to canonical cost band with explicit fallback “unknown”; budget filter behavior for unknown must be defined (include vs exclude). | Users get empty sets or wrong budget matches. |
| P1.8 | Multiple cuisines in one cell | `"Italian, Chinese"` vs list type | Split, trim, lowercase for matching; preserve display string for UI. | Cuisine filter misses valid rows. |
| P1.9 | Duplicate restaurant rows | Same name and location | Dedupe rule: keep highest rating, merge, or stable `id` from row index; stable id required for LLM join-back. | Double cards or ambiguous LLM references. |
| P1.10 | Leading/trailing whitespace and inconsistent city names | `" Delhi "` vs `Delhi` | Trim and normalize location tokens; consider alias map for known variants later. | False empty results after filter. |
| P1.11 | Special characters and emoji in names | Sanitize for logs; preserve for display and LLM. | Log or JSON encoding errors. |

---

## 4. Phase 2 — Retrieval (filter + cap)

### 4.1 Location

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P2.1 | User location string matches no row | Return empty candidate set with clear copy; optional “did you mean” only if you add fuzzy logic; do not call LLM on empty set (per architecture exit criteria). | Wasted LLM cost; nonsense explanations. |
| P2.2 | User enters region vs locality vs typo | Exact match policy vs substring: document behavior; overly loose match pollutes results. | Wrong city results or empty sets. |
| P2.3 | Case and script variants | Unicode casefold for Latin; document policy for non-Latin scripts. | Inconsistent matches. |

### 4.2 Budget and cuisine

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P2.4 | Budget band has no rows after mapping | Empty set + message; do not relax budget silently without UI disclosure. | Mistrust if results ignore stated budget. |
| P2.5 | Row cost unknown | Policy: treat as excluded under strict budget, or included with tag “budget unknown” in UI. | Confusing “why did this appear?” |
| P2.6 | User cuisine `"Asian"` but data only has `"Chinese"` | Unless semantic expansion is in scope, no match is correct; optional notes to LLM cannot invent new rows. | User expects broader matching—product copy should set expectations. |
| P2.7 | User selects multiple cuisines (if UI allows later) | AND vs OR semantics must be explicit and tested. | Surprising inclusion/exclusion. |

### 4.3 Rating and thresholds

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P2.8 | `min_rating` above max in dataset for that filter | Empty set; helpful message. | User thinks system is broken. |
| P2.9 | `min_rating` negative or absurdly high | API validation: 400 with field errors; clamp only if product explicitly allows sliders with bounds. | Invalid filter state. |
| P2.10 | Tie on deterministic sort | Stable secondary key (e.g. name, then id) so tests and LLM input order are reproducible. | Flaky tests and non-reproducible rankings. |

### 4.4 Candidate cap and optional notes

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P2.11 | Filter returns fewer than top-K | Return all; LLM asked for top `min(k, len)`; UI shows fewer cards. | Error if code assumes exactly K. |
| P2.12 | Filter returns exactly one restaurant | Still valid; LLM can rank one; copy should not imply “comparison” if only one. | Awkward UX copy. |
| P2.13 | Optional notes contain only whitespace | Treat as null; do not send empty noise to LLM. | Token waste, odd prompts. |
| P2.14 | Optional notes extremely long | Max length on API and UI; truncate with indicator or reject with 400. | Prompt bloat, cost, abuse. |

---

## 5. Phase 3 — LLM integration

### 5.1 Grounding and validation

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P3.1 | Model outputs a restaurant not in candidate list | Validator rejects; retry once with stricter prompt or fall back to deterministic order + template explanation citing only allowed fields. | Violates core success criterion (subset grounded in dataset). |
| P3.2 | Model duplicates the same venue twice in ranked list | Deduplicate by stable id; warn in logs. | Confusing UI. |
| P3.3 | Model omits explanation for one item | Retry slice or fill with controlled template “Matches your cuisine and rating preferences” only if allowed by product—prefer retry. | Generic filler violates success criteria if overused. |
| P3.4 | Model outputs right venues but wrong ratings/cost in prose | Prefer displaying ratings/cost from canonical data in UI, not from model prose; prompt says “do not invent numeric facts.” | User sees contradictions. |
| P3.5 | Join key ambiguous (same name, different areas) | Prefer stable internal id in prompt and in model JSON; never rely on name alone. | Wrong restaurant joined to explanation. |

### 5.2 Parsing, format, and provider behavior

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P3.6 | Truncated JSON / markdown fence drift | Parser errors surfaced; bounded repair attempt or fallback path. | 500s or blank UI. |
| P3.7 | Model returns valid JSON but wrong schema | 400-level internal classification → user-safe message; log schema diff. | Silent data loss. |
| P3.8 | Model returns extra keys or wrong types | Strict parse with coercion rules or reject. | Subtle UI bugs. |
| P3.9 | Empty model content | Treat as LLM failure; same as timeout path for UX. | Spinner forever. |
| P3.10 | Content filter / refusal (“I can’t help”) | Map to structured error; offer non-LLM fallback (deterministic list + short static blurb). | Dead-end for user. |

### 5.3 Timeouts, limits, and abuse

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P3.11 | LLM latency exceeds HTTP timeout | Server timeout with clear code; UI timeout message; avoid double-submit creating duplicate LLM calls (idempotency or disable button). | Double charges, duplicate rows. |
| P3.12 | Rate limit from provider | Backoff; queue or 429 to client with `Retry-After` if appropriate. | Thundering herd on retry. |
| P3.13 | Prompt injection in optional notes | Treat notes as untrusted data; system prompt instructs model to ignore instructions inside user notes; strip or escape if rendering model output as HTML (P4). | Policy bypass, XSS if echoed. |

---

## 6. Phase 4 — Surface (web UI + HTTP API)

### 6.1 API contract

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P4.1 | Malformed JSON body | 400 with validation detail array. | Generic 500 hides client bugs. |
| P4.2 | Unknown fields in body | Ignore or reject based on policy; document (strict vs loose). | Forward compatibility vs silent typos. |
| P4.3 | `Content-Type` missing or wrong | 415 or 400. | Accidental HTML form posts. |
| P4.4 | Huge request bodies | Limit body size at reverse proxy and app. | DoS vector. |
| P4.5 | Concurrent duplicate submissions | Idempotency key optional; at minimum disable submit until response. | Duplicate LLM spend. |

### 6.2 Web client

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P4.6 | User navigates away during slow LLM | Abort fetch or ignore stale response via request id; no state corruption. | Wrong results shown for new search. |
| P4.7 | Network offline mid-request | Friendly offline message; retry when back. | Uncaught promise errors. |
| P4.8 | API returns empty list | Dedicated empty state per problem statement (no fake placeholders). | Confusion vs error. |
| P4.9 | API returns partial fields | UI handles nulls; never show “undefined” in production build. | Broken layout. |
| P4.10 | Long explanations overflow layout | Scroll, clamp with expand, or typography rules. | Unreadable UI. |
| P4.11 | XSS if future features render markdown or raw HTML from model | Sanitize or render as plain text only; CSP headers on API/static host. | Stored/reflected XSS if logs replayed. |
| P4.12 | CORS misconfiguration | Explicit allowed origins for dev/prod; no `*` with credentials. | Broken front-end or insecure deployment. |

### 6.3 Accessibility and input UX

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P4.13 | Keyboard-only users | Forms operable, focus order, visible focus rings. | Exclusion, compliance gaps. |
| P4.14 | Screen reader on loading and errors | `aria-live` for result region; associate labels with inputs. | Poor accessibility. |
| P4.15 | Autocomplete and browser autofill breaking selects | Names and autocomplete attributes set intentionally. | Wrong submissions. |

---

## 7. Phase 5 — Hardening and operations

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| P5.1 | Logs contain full optional notes or exact addresses | Redact or hash per observability plan; align with “no PII unless approved.” | Privacy incident. |
| P5.2 | Retry loop amplifies outage | Max retries, jitter, circuit breaker for LLM calls. | Provider-wide ban or cost spike. |
| P5.3 | Disk full for cache or logs | Monitor; graceful failure on write. | Silent ingest failure. |
| P5.4 | CI without network | Use small fixture file or cached snapshot for tests; skip HF integration test when offline. | Flaky CI. |

---

## 8. Product and domain (problem statement alignment)

| # | Edge case | Expected behavior | Risk |
|---|-----------|-------------------|------|
| PR.1 | User expects live prices or hours | UI copy references static dataset (non-goals in problem statement). | False expectations, support burden. |
| PR.2 | User asks for cuisine not in India-heavy dataset | Empty or weak matches; messaging should explain data coverage, not hallucinate venues. | Trust loss. |
| PR.3 | Explanation quality is subjective | Optional rubric in P5; do not claim human curation unless true. | Marketing vs reality mismatch. |

---

## 9. Suggested test matrix (priority)

High priority for correctness against [problemstatement.md](./problemstatement.md):

1. Empty filter → no LLM (or guarded path) + clear UX (P2, P4).  
2. Validator rejects hallucinated venue name (P3.1).  
3. Stable sort tie-break (P2.10).  
4. Join-back by id when names collide (P3.5).  
5. API validation for bad `min_rating` and oversized notes (P2.9, P2.14, P4.1).  
6. Stale response ignored after new search (P4.6).  

---

## 10. Traceability

| Document section | Primary edge-case sections |
|------------------|----------------------------|
| Data ingestion / preprocessing | §3.1–3.2 |
| User preferences | §4, §6.1 |
| Integration retrieve → cap N | §4.4, cross-cutting C3 |
| LLM rank + explain | §5 |
| Web output | §6 |
| Non-goals (static data) | PR.1–PR.2 |
| Open design choices (caps, budget map) | P2.4–P2.5, C3, P1.7 |

---

## 11. Document control

- **Sources of truth:** [problemstatement.md](./problemstatement.md), [architecture-phases.md](./architecture-phases.md).  
- **When to update this file:** After ADR changes for budget mapping, dedupe rules, LLM output schema, or API validation rules.
