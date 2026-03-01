# Components

This document describes the component system used by ProFed.

Components are the fundamental building blocks of a ProFed instance. Each
component runs independently and performs a specific function, such as
providing an API, scraping jobs, or managing storage.

The framework is responsible for:

- loading component configuration
- validating configuration
- starting configured components
- managing component processes

Components themselves focus only on their domain logic.

---

# Overview

A component is a Python package located under:

```
src/profed/adapters/
```

Each component package must follow a defined structure and naming
conventions so that the framework can discover and start it.

Example:

```
src/profed/adapters/example_component/
├── __init__.py
└── config/
    └── __init__.py
```

---

# Component Entry Function

Each component must expose a single entry function.

The function name must be the PascalCase version of the package name.

Example:

Package name:

```
example_component
```

Entry function:

```python
def ExampleComponent(cfg):
    ...
```

Fully qualified name:

```
profed.adapters.example_component.ExampleComponent()
```

The `cfg` parameter contains the parsed configuration object for this
component.

The function is called by the framework when the component starts.

The function may:

- run forever (API server, message processor, etc.)
- run once and exit (batch job, scraper, migration tool, etc.)

The framework does not impose any lifecycle restrictions.

---

# Component Configuration

Each component may optionally provide a configuration parser.

Location:

```
profed.adapters.<component>.config.parse
```

Signature:

```python
def parse(cfg: dict, ...) -> Any:
    ...
```

- The first argument always contains the raw configuration section for
  this component.
- Additional arguments may contain parsed configuration objects from
  other components. These are injected automatically by the framework
  based on parameter names.

Example:

```python
def parse(cfg: dict, network):
    timeout = network.timeout
    url = cfg["url"]
    return MyComponentConfig(url, timeout)
```

The return value may be any object. This object will be passed to the
component entry function as `cfg`.

If no `config.parse` function exists, the raw configuration dictionary
is passed instead.

---

# Configuration Section Naming

Each component corresponds to exactly one configuration section.

Example configuration file:

```
[example_component]
url = https://example.org
```

This section maps to:

```
profed.adapters.example_component
```

---

# Component Discovery

The framework discovers components dynamically based on configuration
section names.

For each configuration section:

1. The framework searches for a matching package in:

```
profed.adapters.<section_name>
```

2. The framework tries to call (optional):

```
profed.adapters.<section_name>.config.parse()
```

3. The framework calls the component entry function:

```
profed.adapters.<section_name>.<PascalCaseName>()
```

If any of these steps fail, startup aborts with an error.

---

# Component Isolation

Components must not rely on global mutable state.

All required configuration is provided via the `cfg` parameter.

Components may:

- open database connections
- start network servers
- subscribe to message queues
- spawn worker threads or processes

Depending on the configuration Components will run in separate processes or
containers.

---

# Component Design Guidelines

Components should:

- be deterministic
- validate their own configuration
- fail fast on startup errors
- not block framework initialization unnecessarily
- communicate only asynchronously via the message bus

Components should not:

- access unrelated component configuration directly
- rely on execution order
- modify framework internals
- expect any kind of request/response communication

---

# Minimal Example

```python
# example_component/config/__init__.py
def parse(cfg: dict):
    return {
        "message": cfg.get("message", "Hello World")
    }
```

```python
# example_component/__init__.py
def ExampleComponent(cfg):
    print(cfg["message"])
```

Configuration:

```
[example_component]
message = Hello ProFed
```

---

# Summary

A valid component consists of:

Required:

- package under `profed.adapters`
- PascalCase entry function

Optional:

- `config.parse` function

The framework handles:

- discovery
- configuration injection
- startup

