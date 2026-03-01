# Contributing to ProFed

Thank you for your interest in contributing to ProFed!

## Table of Contents

- [Canonical Repository](#canonical-repository)
- [How to Contribute](#how-to-contribute)
- [Licensing](#licensing)
  - [Code](#code)
  - [Protocol Specification and Architecture Documents](#protocol-specification-and-architecture-documents)
- [Code Style](#code-style)
- [Code Review Practices](#code-review-practices)
- [Pull Request Checklist](#pull-request-checklist)

## Canonical Repository

The canonical repository for ProFed is hosted on Codeberg:

https://codeberg.org/GrayDurian/ProFed

Please submit all pull requests to this repository.

There is also a GitHub mirror for convenience:

https://github.com/cdonat/ProFed

Forks from GitHub are fine, but all pull requests must target the canonical
Codeberg repository.

## How to Contribute

1. Fork the repository (either Codeberg or GitHub)
2. Create a feature branch
3. Make your changes
4. Open a pull request against the canonical Codeberg repository with a
   clear description

Keep pull requests focused and reasonably small. Include tests or
documentation updates when appropriate.

Tip: Make commits atomic — each commit should represent a single logical
change.

## Licensing

### Code

All source code in this repository is licensed under:

GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)  
SPDX Identifier: `AGPL-3.0-or-later`

By submitting a contribution, you agree that your code contributions are
licensed under the same license.

### Protocol Specification and Architecture Documents

The protocol specification and architecture documentation are licensed under:

MIT License  
SPDX Identifier: `MIT`

This allows anyone to implement compatible components or use the protocol
without being bound by the AGPL, as long as they do not use the ProFed code
itself.

## Code Style

- Follow existing code style and structure
- Add tests for new features when possible
- Update documentation if needed

## Code Review Practices

- Make sure you understand all changes in your pull request and can explain
  them if needed
- Prefer small, incremental pull requests over large, sweeping changes; they
  are easier to review and merge
- You are responsible for all changes you submit, including any generated or
  suggested by AI tools
- Pull requests that are too large or cannot be explained by the contributor
  may be sent back for revision or closed

## Pull Request Checklist

- [ ] Code builds correctly
- [ ] Tests added or updated
- [ ] Documentation updated
- [ ] License headers included where appropriate

You are responsible for all changes you submit, including any
generated or suggested by AI tools. Ensure you understand every change in
your pull request.

