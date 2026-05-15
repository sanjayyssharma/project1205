"use client";

import { useMemo, useState } from "react";
import { postRecommendations, RecommendationApiError } from "@/lib/api";
import type { Budget, RankedRestaurant, RecommendationResponse } from "@/lib/types";

function formatCost(cost: number | null | undefined): string {
  if (cost === null || cost === undefined) return "—";
  return `₹${cost.toLocaleString("en-IN")} for two`;
}

function formatRating(rating: number | null | undefined, votes: number | null | undefined): string {
  if (rating === null || rating === undefined) return "—";
  const v = votes != null ? ` (${votes} votes)` : "";
  return `${rating.toFixed(1)}${v}`;
}

function RestaurantCard({ item }: { item: RankedRestaurant }) {
  const cuisines = Array.isArray(item.cuisines) ? item.cuisines.join(", ") : "—";
  const area = [item.locality, item.city_area].filter(Boolean).join(", ") || "—";

  return (
    <article className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">#{item.rank}</p>
          <h3 className="text-lg font-semibold text-zinc-900">{item.name}</h3>
          <p className="mt-1 text-sm text-zinc-600">{area}</p>
        </div>
        <div className="text-right text-sm text-zinc-700">
          <p className="font-medium">{formatRating(item.rating, item.votes)}</p>
          <p className="text-zinc-600">{formatCost(item.cost_for_two_inr as number | null | undefined)}</p>
        </div>
      </div>
      <p className="mt-3 text-sm text-zinc-600">
        <span className="font-medium text-zinc-800">Cuisines: </span>
        {cuisines}
      </p>
      <p className="mt-4 text-sm leading-relaxed text-zinc-800">{item.explanation}</p>
    </article>
  );
}

export default function HomePage() {
  const [location, setLocation] = useState("Bangalore");
  const [budget, setBudget] = useState<Budget | "">("");
  const [cuisine, setCuisine] = useState("North Indian");
  const [minRating, setMinRating] = useState(3.5);
  const [optionalNotes, setOptionalNotes] = useState("");
  const [includeUnknownCost, setIncludeUnknownCost] = useState(true);
  const [maxCandidates, setMaxCandidates] = useState<number | "">("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RecommendationResponse | null>(null);

  const canSubmit = useMemo(() => location.trim().length > 0 && cuisine.trim().length > 0, [location, cuisine]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!canSubmit) return;

    setLoading(true);
    try {
      const data = await postRecommendations({
        location: location.trim(),
        budget: budget === "" ? null : budget,
        cuisine: cuisine.trim(),
        min_rating: minRating,
        optional_notes: optionalNotes.trim(),
        include_unknown_cost: includeUnknownCost,
        max_candidates: maxCandidates === "" ? null : maxCandidates,
      });
      setResult(data);
    } catch (err) {
      if (err instanceof RecommendationApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Something went wrong.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900">Restaurant recommendations</h1>
        <p className="mt-2 text-sm text-zinc-600">
          Phase 5 UI — browser only. Requests go through <code className="rounded bg-zinc-200 px-1 py-0.5 text-xs">/api/backend</code> in dev
          (Next rewrites to your FastAPI server).
        </p>
      </header>

      <form onSubmit={onSubmit} className="space-y-5 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block sm:col-span-2">
            <span className="text-sm font-medium text-zinc-800">Location</span>
            <input
              className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm shadow-sm focus:border-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              required
              autoComplete="address-level2"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-zinc-800">Budget</span>
            <select
              className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm shadow-sm focus:border-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10"
              value={budget}
              onChange={(e) => setBudget(e.target.value as Budget | "")}
            >
              <option value="">Any</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </label>

          <label className="block">
            <span className="text-sm font-medium text-zinc-800">Cuisine</span>
            <input
              className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm shadow-sm focus:border-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10"
              value={cuisine}
              onChange={(e) => setCuisine(e.target.value)}
              required
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-zinc-800">Minimum rating</span>
            <input
              type="number"
              step="0.1"
              min={0}
              max={5}
              className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm shadow-sm focus:border-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10"
              value={minRating}
              onChange={(e) => setMinRating(Number(e.target.value))}
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-zinc-800">Max candidates (optional)</span>
            <input
              type="number"
              min={1}
              max={500}
              placeholder="Default from server"
              className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm shadow-sm focus:border-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10"
              value={maxCandidates}
              onChange={(e) => {
                const v = e.target.value;
                setMaxCandidates(v === "" ? "" : Number(v));
              }}
            />
          </label>
        </div>

        <label className="block">
          <span className="text-sm font-medium text-zinc-800">Optional notes</span>
          <textarea
            rows={3}
            className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm shadow-sm focus:border-zinc-900 focus:outline-none focus:ring-2 focus:ring-zinc-900/10"
            value={optionalNotes}
            onChange={(e) => setOptionalNotes(e.target.value)}
            placeholder="e.g. quiet place, outdoor seating, kid-friendly…"
          />
        </label>

        <label className="flex items-center gap-2 text-sm text-zinc-800">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900"
            checked={includeUnknownCost}
            onChange={(e) => setIncludeUnknownCost(e.target.checked)}
          />
          Include restaurants with unknown cost
        </label>

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={!canSubmit || loading}
            className="inline-flex items-center justify-center rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Getting recommendations…" : "Get recommendations"}
          </button>
          {loading ? <span className="text-sm text-zinc-600">Calling Groq ranking…</span> : null}
        </div>
      </form>

      {error ? (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-900" role="alert">
          {error}
        </div>
      ) : null}

      {result ? (
        <section className="mt-10 space-y-4">
          <div className="rounded-xl border border-zinc-200 bg-white p-4 text-sm text-zinc-700 shadow-sm">
            <p>
              <span className="font-medium text-zinc-900">Snapshot:</span> {result.snapshot}
            </p>
            <p className="mt-1">
              <span className="font-medium text-zinc-900">Pipeline:</span> {result.source_count} restaurants in source →{" "}
              {result.candidate_count} candidates after filters
              {typeof result.llm_latency_ms === "number" ? (
                <>
                  {" "}
                  · <span className="font-medium text-zinc-900">LLM:</span> {result.llm_latency_ms} ms
                </>
              ) : null}
            </p>
            {result.summary ? (
              <p className="mt-3 text-zinc-800">
                <span className="font-medium">Summary:</span> {result.summary}
              </p>
            ) : null}
            {result.groq?.used_fallback ? (
              <p className="mt-2 text-amber-800">
                Ranking used fallback ordering (Groq returned no usable JSON). Check server logs for details.
              </p>
            ) : null}
          </div>

          {result.ranked.length === 0 ? (
            <div className="rounded-xl border border-zinc-200 bg-white p-6 text-center text-sm text-zinc-700 shadow-sm">
              {result.empty_message ?? "No restaurants matched your filters."}
            </div>
          ) : (
            <div className="space-y-4">
              {result.ranked.map((item) => (
                <RestaurantCard key={`${item.id}-${item.rank}`} item={item} />
              ))}
            </div>
          )}
        </section>
      ) : null}
    </main>
  );
}
