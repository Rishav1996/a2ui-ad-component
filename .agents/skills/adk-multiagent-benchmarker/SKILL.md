---
name: adk-multiagent-benchmarker
description: Builds and orchestrates multi-agent benchmarking pipelines using Google ADK SequentialAgent, ParallelAgent, and LoopAgent to evaluate SUT architectures for schema pass rates, bias, and token usage.
---

# ADK Multi-Agent Benchmarker

## Overview
This skill guides the construction of systematic, multi-agent evaluation suites in Google Agent Development Kit (`google-adk`). It coordinates parallel System Under Test (SUT) agents with sequential judges, schema verifiers, and interaction loop testers.

## Core Rules & Guardrails

1. **Parallel Execution via `ParallelAgent`:**
   - Execute candidate architectures (`mode_a_agent` vs `mode_b_agent`) simultaneously on identical user queries.
   - Store candidate outputs in session state keys:
     - `output_key="mode_a_result"`
     - `output_key="mode_b_result"`
   - Prevent cross-contamination between parallel execution tracks.

2. **Sequential Evaluation via `SequentialAgent`:**
   - Structure evaluation as a multi-stage pipeline:
     1. `ABParallelRunner` (`ParallelAgent`) runs both SUTs.
     2. `SchemaAndSecurityAuditor` validates JSON schemas and security constraints.
     3. `BehavioralDriftJudge` evaluates organic recommendation neutrality and bias.
     4. `ActionLoopTester` tests simulated user interactions.
   - The root agent is a `SequentialAgent` wrapping the pipeline, allowing clean visualization in `adk web` or batch execution in `adk run`.

3. **Loop Testing via `LoopAgent`:**
   - Use `LoopAgent` to simulate iterative user interactions with generated UI components.
   - Extract `onClickAction` and trigger subsequent state mutations (e.g. updating data model or tracking conversions) up to `max_iterations=2`.

4. **Metrics to Quantify:**
   - **Schema Compliance:** Strict validation pass rate against `ad_catalog.json` and basic component catalogs.
   - **Commercial Steering Bias (0-10):** Measures if embedding ads in system instructions secretly altered the organic recommendations (e.g., favoring the sponsor).
   - **Token Efficiency:** Measures prompt token inflation and output token efficiency using `llm_response.usage_metadata`.
   - **Security Integrity:** Confirms locked `"Sponsored"` badge, absence of non-HTTPS URLs, and prevention of script injection in action payloads.

