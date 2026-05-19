# ADR-0001: Framework Principles

## Status

Accepted

## Context

Fabric Foundry needs to support repeatable dataset onboarding across Fabric, ADLS, Databricks, and future targets without creating one-off pipelines for each dataset.

## Decision

The framework will use metadata-first delivery, thin orchestration drivers, deterministic runtime code, target writer adapters, and human review for material data changes.

The LLM coding agent is build-time only. It may generate code, tests, and documentation, but it must not make runtime production decisions, access secrets, deploy directly, or approve its own output.

## Consequences

Dataset-specific behaviour must be expressed in contracts or metadata before it becomes runtime code. Pipelines and notebook drivers stay generic. Governance controls can be introduced as pluggable gates without changing dataset business logic.
