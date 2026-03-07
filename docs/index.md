# CardioXNet Documentation

This documentation set is intentionally short. The goal is to explain how to run the app, how to interpret the pipeline, and which configuration choices materially change the result set.

## Start Here

- [README](../README.md): project overview, local setup, and test commands
- [Configuration Guide](CONFIGURATION.md): backend settings and the frontend presets they influence

## Core Workflow

CardioXNet follows a staged discovery funnel:

1. Seed genes are validated.
2. STRING expands the local functional neighborhood.
3. Primary pathway enrichment creates the first candidate set.
4. Secondary pathway enrichment broadens discovery beyond the original seed list.
5. Aggregation, semantic filtering, scoring, and PubMed screening produce the final ranked pathways.

## Interpreting Results

- Final pathways are prioritized candidates, not confirmed novel findings.
- Lower seed-overlap pathways are useful leads, but they still require literature review.
- PubMed query hits are a fast screening layer, not a definitive novelty adjudication step.
- Important genes highlight recurrence across highly ranked pathways.

## Where To Look In The App

- `/`: gene entry and preset-based configuration
- `/documentation`: concise workflow and interpretation notes
- `/api-reference`: REST and WebSocket interface summary

## Suggested Review Pattern

1. Run the balanced preset first.
2. Compare with exploratory mode if the shortlist is too narrow or too obvious.
3. Review top pathways manually for synonym overlap and domain relevance.
4. Only make novelty claims after manual literature screening.
