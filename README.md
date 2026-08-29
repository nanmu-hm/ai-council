# AI Council

Multi-model AI orchestration and consensus engine.

AI Council is an orchestration layer above OpenAI-compatible gateways such as WebModel, official APIs, and local runtimes such as Ollama.

## Phase 1

- provider abstraction
- WebModel-compatible gateway adapter
- Ollama adapter
- concurrent dispatch
- normalized streaming events
- health checks and failure isolation
- HTTP API for the future web UI

Cross-feed, judge, evidence verification, and visual browser mode will be added incrementally.

## Architecture

```text
                     AI Council
                          |
                    Orchestrator
             +------------+------------+
             |            |            |
          Scheduler    StreamMux    Consensus
             |            |            |
             +------------+------------+
                          |
                Provider abstraction
                   /             \
              WebModel          Ollama
                  |                |
              Web AI          Local models
```

## Design principles

1. Keep WebModel as an external gateway rather than forking its provider implementations.
2. Keep provider/session concerns separate from orchestration.
3. Treat partial provider failure as normal and isolate it with timeouts and circuit breaking.
4. Normalize model output into a provider-independent event protocol.
5. Keep the first implementation small enough to test locally before adding advanced council behavior.

## License

Apache-2.0
