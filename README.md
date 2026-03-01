# ProFed

ProFed is a reference implementation of a federated professional social
network.

The goal of this project is to build an open, scalable, and high-availability
platform for professional networking that is not controlled by a single vendor,
and that supports federation between independent installations.

---

## Vision

ProFed aims to provide:

- Federated professional profiles
- Distributed job and opportunity exchange
- Decentralized identity and trust mechanisms
- High availability and horizontal scalability
- Replaceable infrastructure adapters (message bus, storage, API, etc.)

The architecture is intentionally modular and component-based, with a
message-driven core that allows future high-availability deployments and
multi-instance services.

---

## Current State

This repository currently contains:

- Configuration framework (in progress)
- PostgreSQL-backed message bus (in progress)
- Component lifecycle management framework (in progress)
- Unit test infrastructure
- Development environment setup

Functional components are not yet implemented.

---

## Roadmap (Rough Outline)

Planned development stages:

1. Finalize core runtime framework
2. Implement PostgreSQL message bus backend
3. Implement first components (profile ingestion, API, scraper)
4. Define protocol specification (MIT licensed)
5. Add federation mechanisms
6. Harden system for high-availability deployments

---

## Licensing

This reference implementation is licensed under:

AGPL 3.0 or later

The protocol specification and architecture documentation are licensed under:

MIT License

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## Canonical Repository

Canonical repository:

https://codeberg.org/GrayDurian/ProFed

Please open issues there.

GitHub mirror (automatically synchronized):

https://github.com/cdonat/ProFed

Issues should preferably be raised on Codeberg.

---

## Development Setup

### Requirements

- Python 3.11 or newer
- uv (Python package manager)

Install uv:

    curl -Ls https://astral.sh/uv/install.sh | sh

### Setup Environment

    uv venv
    uv pip install -e .[dev]

Activate environment:

    source .venv/bin/activate

---

## Running Tests

Run tests once:

    ./scripts/test.sh

Run tests continuously with visual feedback:

    ./scripts/watch-tests.sh

---

## Documentation

Additional documentation is located in the docs/ directory:


- [Architecture](docs/architecture.md)
- [Component System](docs/components.md)
- [Runtime](docs/runtime.md)
- [Message Bus](docs/message-bus.md)
- [Deployment](docs/deployment.md)

---

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
