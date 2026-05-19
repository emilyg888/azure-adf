# Architecture

Fabric Foundry separates orchestration, metadata, deterministic transformation code, target writing, governance, and audit evidence.

## Layers

| Layer | Responsibility |
|---|---|
| Fabric pipeline | Orchestration, parameters, dependency flow, operational monitoring |
| Metadata repository | Dataset, source, target, mapping, rule, governance, and audit configuration |
| Notebook or job driver | Thin runtime driver that loads metadata and calls framework modules |
| Framework modules | Reusable ingestion, validation, transformation, writer, governance, and audit logic |
| Dataset transforms | Approved deterministic dataset-specific transformation functions |
| Target adapters | Delta, file, and future platform-specific writes |
| Agent workflow | Build-time generation of code, tests, and documentation only |

## MVP Runtime Flow

```text
Pipeline parameters
  -> environment config
  -> metadata/contracts
  -> generic ingestion
  -> landing validation
  -> generic transformation driver
  -> target writer
  -> audit evidence
```

## Non-Negotiables

- No secrets in repo, metadata seed files, notebooks, or generated code.
- No runtime LLM dependency.
- Material mapping, PII, DQ, and schema changes require human review.
- Environment-specific values live in environment config or managed platform configuration.
