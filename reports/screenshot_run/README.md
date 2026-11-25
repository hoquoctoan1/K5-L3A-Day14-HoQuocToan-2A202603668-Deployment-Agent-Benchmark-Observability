# Additional run for screenshots

This directory contains a new, real observability capture after the original
benchmark had been completed and its Docker stack removed. The original JSON,
CSV and benchmark numbers are preserved in their existing paths.

The stack was restarted with three agent instances. Locust's web API started
30 users at a spawn rate of 5 users/second against Nginx. Agent settings use
the original defaults (v2, mock-llm-small, error rate 0.01, slow rate 0.03).

- Slow trace: `a92f6b9bd87601a2aba5714649c4dfb2`
- Error trace: `3f980a8eb73f61ae72f9e3b413d510ed`
- `observability_evidence.json` records the actual capture timestamp, PromQL,
  Grafana health/dashboard metadata, public metrics status and matching logs.
- `jaeger_*_trace.json` preserves the selected raw OTLP spans.

These traces support the new screenshots; they are a separate run from the
traces and timing measurements discussed in the original benchmark report.
