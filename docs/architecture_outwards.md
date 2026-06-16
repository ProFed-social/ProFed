# ProFed: Federated Professional Networking — Architecture Overview

**Version:** 0.1 (Draft for Discussion)
**Status:** Early design stage — the intent of this document is to share concepts and invite feedback, not to prescribe an implementation.

---

## Table of Contents

1. [Introduction & Goals](#1-introduction--goals)
2. [Core Concepts](#2-core-concepts)
   - 2.1 [Professional Profiles](#21-professional-profiles)
   - 2.2 [Job Postings](#22-job-postings)
   - 2.3 [Federated Search](#23-federated-search)
   - 2.4 [Trust Scores and Handling of Malicious Nodes](#24-trust-scores-and-handling-of-malicious-nodes)
   - 2.5 [Reference Verification](#25-reference-verification)
3. [ActivityPub Integration](#3-activitypub-integration)
   - 3.1 [Vocabulary Approach](#31-vocabulary-approach)
   - 3.2 [Actor Types](#32-actor-types)
   - 3.3 [Object Types](#33-object-types)
   - 3.4 [Relation to Mastodon and Friendica](#34-relation-to-mastodon-and-friendica)
4. [Discussion](#4-discussion)
- [Appendix A: JSON-LD Examples](#appendix-a-json-ld-examples)
- [Appendix B: Microformats2 Field Mapping](#appendix-b-microformats2-field-mapping)

---

## 1. Introduction & Goals

ProFed is an open-source federated professional network built on ActivityPub. Its goal is to bring the features of a professional network — structured CVs, job postings, and meaningful search — to the open, decentralised social web, without requiring a central platform.

ProFed instances are designed to run at any scale, from a single-user personal server to a large multi-tenant deployment. Instances federate with each other and with other ActivityPub-compatible systems.

This document describes the architecture and the concepts behind ProFed's extensions to ActivityPub. It is addressed to developers of compatible or neighbouring systems. The intent is to share ideas early, invite alternative approaches, and identify where interoperability agreements are needed before designs become rigid.

**Design principles:**

- Reuse established standards wherever possible. ProFed is first a Mastodon-compatible ActivityPub server, and only adds new vocabulary where no existing vocabulary covers the use case.
- Keep the added vocabulary as close to existing, well-understood standards as possible. ProFed borrows from Microformats2 rather than inventing a new domain model for professional data.
- Federated search must not create uncontrolled load. ProFed's search architecture is designed with explicit bounds on propagation.
- Systems that do not understand ProFed's extensions should still interoperate with ProFed as a standard ActivityPub server.

---

## 2. Core Concepts

### 2.1 Professional Profiles

Every ProFed user is represented by a standard ActivityPub `Person` actor. ProFed extends this actor with a structured professional profile — a CV — attached directly to the actor object.

The CV contains the sections one would expect: work experience, education, skills, and project descriptions. This data travels with the actor through normal ActivityPub federation. A server that does not understand the ProFed CV extension simply ignores it and treats the actor as a standard `Person`.

The CV data is sourced in two ways: users can enter it directly in ProFed, or ProFed can import it from a personal website that publishes the profile using Microformats2 markup (see section 3.1 and Appendix B). The same field vocabulary is used for both the AP representation and the mf2 website representation, making the import mapping straightforward.

### 2.2 Job Postings

A job posting is a new ActivityPub object type defined by ProFed. Like any other AP object, it is created by an actor, lives in their outbox, and propagates to followers via standard `Create` and `Announce` activities.

Job postings can be created by individual users (a recruiter or hiring manager on their personal actor) or by a `Group` actor representing a job board or a company page. Followers of either receive new postings through the normal ActivityPub delivery mechanism.

Beyond the job title and description, a posting carries structured attributes: the hiring organisation, location, employment type, remote work option, and required skills. These structured attributes are what enables meaningful search and matching, as described in the next section.

ProFed also supports ingesting job postings from external sources via web scrapers. This is primarily a bootstrap strategy to address the initial chicken-and-egg problem: no platform attracts job seekers without job postings, and no employers post there without job seekers. By scraping postings from existing job boards and company career pages into the local index, an instance can offer useful search results from the outset. As candidates begin using ProFed to find those positions, employers and recruiters gain an incentive to publish directly — at which point the scraped copies are superseded by the authoritative ActivityPub objects. The scraper path is an on-ramp, not a permanent dependency.

### 2.3 Federated Search

Federated search is the part of ProFed's architecture that most significantly goes beyond what existing ActivityPub servers provide. It has two modes — interactive search and saved search — which share a common infrastructure: the local index.

#### The Local Index

Each ProFed instance maintains a local full-text and structured index of all objects it has encountered: local profiles, local job postings, objects arriving in the instance's inboxes through normal ActivityPub federation, and objects received from remote instances through either search mode. The index is not limited to objects from directly followed actors. Both search modes below are designed to populate this index continuously, so that over time each instance builds up a broader view of the professional landscape across the network.

#### Interactive Search

When a user issues a search query, the instance first searches its own local index. In addition, it performs a flood search: the query is forwarded in parallel to a set of known, trusted remote instances, which in turn forward it to their peers. The flood is recursive.

The flood search is designed with explicit mechanisms to bound load and prevent redundant work:

**Query normalisation.** Before a query is executed or forwarded, it is normalised into a canonical form. This ensures that semantically equivalent queries from different users or from different remote instances are recognised as identical and handled together rather than triggering separate floods. Query normalisation is not limited to interactive search — it is a general mechanism, and applies equally to saved searches (see below).

**Caching and request coalescing.** The result of an interactive search — including results that arrive late from slow remote instances — is cached for a period (currently envisioned as approximately one hour). If an equivalent normalised query arrives while a flood is already in progress, the new request waits for the existing flood to complete and receives its cached result. If the result is already in the cache, the request is answered immediately. In neither case is a new flood initiated. This means the worst-case load on the network for any given query is one flood per cache window, regardless of how many users across the network issue the same query.

This caching behaviour is also what makes the recursive flood self-terminating without requiring explicit loop detection. In a recursive flood, a query will eventually arrive back at a server that has already seen it — either because it originated there, or because an earlier branch of the flood already reached it. When that happens, the server recognises the normalised query, returns the cached or in-progress result, and does not start a new flood. The query stops there.

The cache lifetime is measured in minutes to hours, while timeouts are measured in seconds. A returning cycle will therefore almost always hit a live cache entry, long before the timeout could even be a factor. The decreasing timeout matters in a different scenario: a server that is badly configured — with an unusually short cache lifetime and an unusually large timeout — could in principle generate fresh floods for queries that should already be cached. Its peers, however, will answer those requests from their own caches, which are still live. The badly configured server gets back cached results and generates no new network load beyond its own outbound requests. This also neutralises the deliberate version of the same misconfiguration, where a server intentionally sets a minimal cache lifetime in order to repeatedly re-flood the network: the flood terminates at the first hop, because every peer it reaches is still holding a cached response.

**Decreasing timeout.** Each flood request carries a timeout indicating how long the receiving instance has to respond. When an instance forwards the query to its own peers, it passes a reduced timeout — for example, if the originating instance allows five seconds, it forwards with four seconds, its peers forward with three, and so on. When the remaining timeout reaches zero, instances stop contributing to the immediate search result but continue forwarding the query. This tail of the flood serves only to propagate matching objects into remote indices; it does not delay the user who initiated the search.

**Index feedback.** Results from the flood search are added to the local index as they arrive. Future equivalent queries will therefore find more results locally, and the deduplication filter will discard a larger proportion of the flood's returns. The flood itself still runs — an instance cannot know in advance what it does not know — but its net contribution shrinks as the index grows.

#### Saved Search

A saved search is represented as a `Service` actor — a Search Actor. Users subscribe to a Search Actor by following it; new matches are delivered to their inbox as `Announce` activities, integrating naturally into any ActivityPub-compatible client.

The Search Actor is not just a passive filter. It actively participates in federation: when a Search Actor is created, it automatically follows Search Actors at known remote instances that represent the same query. Query normalisation ensures that two instances independently create Search Actors for equivalent queries, those actors recognise each other and subscribe to each other once — regardless of how many local users have created that saved search. This prevents redundant subscriptions and duplicate flood propagation.

When a new object arrives — whether as an `Announce` from a remote Search Actor or through any other path — the local instance checks it against all of its saved searches, not only the one whose subscription triggered the delivery. Any saved search whose query matches the object is a candidate for forwarding.

For each matching saved search, deduplication is checked against that Search Actor's outbox: if the object has already been forwarded through this Search Actor, it is skipped. The outbox, rather than the local index, is the correct deduplication boundary here, because the index may contain the object from other sources — inbox delivery, interactive search, direct local creation — and subscribers of a saved search should receive the object regardless of how it entered the index. Conversely, checking the outbox rather than the index ensures that two subscribers of different saved searches that both match the same object each receive it through their respective subscription, without needing to wait for a second Announce to arrive.

For each matching saved search where the object has not yet been forwarded, the Search Actor adds the object to its outbox and delivers an `Announce` to all of its subscribers — local users and remote Search Actors alike. The object is also added to the local index.

Filtering and deduplication happen at every hop. No server forwards a result it has already seen through a given Search Actor. This deduplication, combined with the subscription model, forms the circuit breaker for the saved search network: in one direction, a Search Actor subscribes to any given remote Search Actor at most once, regardless of how many local users have the same saved query; in the other direction, the per-outbox duplicate filter ensures that an object already forwarded through a Search Actor is never forwarded again through that same actor, regardless of how many paths it arrives by. Cycles in the subscription graph are therefore harmless.

---

## 2.4 Trust Scores and Handling of Malicious Nodes

Both search modes interact with remote instances whose behaviour cannot be assumed to be cooperative. ProFed's design includes a trust model that bounds the damage a malicious or malfunctioning node can do, and that causes such nodes to be naturally isolated across the network without requiring central coordination.

#### Trust Score

Every instance maintains a trust score for each peer it interacts with. New peers start with a middle score — neither privileged nor penalised. The score is adjusted continuously based on observed behaviour:

Signals that lower the score include: sending results at a volume that exceeds agreed rate limits; delivering results that do not match the query; delivering objects that fail spot-check verification (see below); and consistently slow response times that erode the usefulness of the node in time-sensitive interactive search.

Signals that raise the score include: consistently relevant results; respecting rate limits; fast response times; and objects that pass spot-check verification.

A low trust score has two direct effects: the rate limit applied to that node is reduced further, and the probability that its delivered objects are subjected to a spot check is increased. These two effects compound: a badly behaving node sends less, and what it does send is scrutinised more.

#### Spot-Check Verification

Job postings and professional profiles carry a canonical source address — the `id` or `url` field of the ActivityPub object, which points back to the originating instance. When a spot check is triggered, the verifying instance fetches the object directly from this source and compares it against what the peer delivered.

Some deviation is expected and acceptable: a job posting may have been updated since it was forwarded. When there is a discrepancy, the verifying instance uses the fetched original — which is, by definition, the most current authoritative version of the object — and discards the peer's version. The original is then what gets indexed and forwarded.

#### Emergent Network Isolation

The combination of trust scores, rate limits, spot checks, and the deduplication already described in the search sections produces an emergent isolation effect for malicious nodes, without requiring any central blocklist or manual intervention.

A node that injects garbage into the search network quickly accumulates low trust scores across all its peers. It is rate-limited everywhere simultaneously, so it can inject only a small volume of bad results. The elevated spot-check probability means those results are disproportionately likely to be caught and discarded before they propagate further. When a node's trust score falls low enough that all its results are spot-checked, its garbage travels at most one hop: the first instance that verifies a bad result against the source discards it there, and the result never reaches anyone else's index or interactive results.

There is also a timing dimension. Interactive search operates under short timeouts. Spot-check verification takes time. In practice, objects from a heavily distrusted node — where every result triggers a synchronous fetch from the source — will rarely arrive within the timeout window of an interactive search. They may still appear in the saved-search flow, where latency is less critical, but there they are still caught by deduplication before reaching users who have already seen the legitimate version of the same object.

---

## 2.5 Reference Verification

Professional profiles commonly include references — short statements from colleagues, managers, or clients attesting to the profile holder's work. On centralised platforms, the platform itself vouches for the authenticity of a reference by controlling the accounts of both parties. In a federated system with no central authority, a different mechanism is needed.

ProFed's approach is inspired by the `rel="me"` link verification used across the web to establish that two URLs belong to the same person. It requires only HTML and the ability of each party to publish content on a URL they control — no ActivityPub, no shared infrastructure.

#### The Mechanism

When someone writes a reference for a ProFed user, the following occurs on the referrer's side: the referrer publishes a hash of the reference text together with the recipient's identity at a stable URL on a website they control. Binding the recipient into the hash prevents a reference written for one person from being re-used by someone else. This URL is the verification anchor.

On the recipient's side: the reference entry in their profile stores both the reference text and a link to that hash URL.

Any client rendering the profile can then verify the reference independently: it computes the hash of the displayed reference text and the recipient's identity using the agreed algorithm, fetches the hash from the referrer's URL, and compares the two. If they match, the reference is marked as verified. If they do not match — or if the URL is unreachable — the reference is marked as unverified. The verification result is a local conclusion drawn by the client; no server needs to pre-compute or cache it.


#### Properties

This mechanism provides meaningful guarantees without a central authority. A reference cannot be fabricated by the recipient, because they cannot publish content on the referrer's domain. A reference cannot be re-attributed to a different person, because the recipient's identity is part of the hashed input — a statement written for one person does not verify for another. A reference cannot be silently altered after the fact, because the hash would no longer match. A referrer can revoke a reference by removing or changing the hash at their URL, at which point clients will display it as unverified.

The mechanism is also lightweight by design. It does not require ActivityPub support, a shared PKI, or any coordination between instances. It works across systems as long as both parties have a URL they control — a personal website, a company page, or any other web presence.

#### ProFed's Role

ProFed stores the reference text and the hash URL on the recipient's side, and the hash value on the referrer's side, as part of the user's profile data. The ProFed web client performs the verification check when rendering a profile and presents the result to the viewer. The underlying data is exposed through the actor's CV extension so that other clients and instances can perform the same check independently.

---

## 3. ActivityPub Integration

### 3.1 Vocabulary Approach

ProFed extends ActivityPub with a `profed:` namespace (`https://profed.social/ns#`). New types and properties are defined within this namespace.

For the domain of professional data (CV fields, job posting fields), ProFed does not invent a new vocabulary from scratch. Instead, it borrows the vocabulary of [Microformats2](https://microformats.org/wiki/microformats2). mf2 already defines property names for exactly this kind of personal and professional data — `p-name`, `p-org`, `dt-start`, `dt-end`, `p-skill`, and so on. ProFed derives JSON field names from these by stripping the type prefix: `p-org` becomes `org`, `dt-start` becomes `start`, and so on.

The practical benefit is consistency between representations. A personal website publishing its owner's CV using mf2 markup and a ProFed actor representing the same CV use identical field names. The profile importer does not need a translation table — it is a direct mapping.

### 3.2 Actor Types

ProFed uses three actor types from ActivityStreams 2.0:

**`Person`** — the primary user actor. Extended with a `resume` property (type `profed:resume`) carrying the structured CV. Systems that do not understand this property treat the actor as a standard Mastodon-compatible person.

**`Group`** — used for job boards and company pages. ProFed follows Friendica's established forum semantics: posts sent to a `Group` actor are re-announced to all followers. This allows job postings to propagate to anyone following the group without requiring them to follow individual recruiters.

**`Service`** — used for Search Actors. A `Service` actor representing a saved search carries the query parameters as properties of the actor object (`profed:queryString`, `profed:queryFilters`). Any ActivityPub client or server can follow it to subscribe to results.

### 3.3 Object Types

**`Note`** — used for standard posts, as in any Mastodon-compatible server. Job postings can be announced in `Note` form for consumption by clients that do not understand `profed:JobPosting`.

**`profed:JobPosting`** — a new object type for structured job postings. Carries the fields described in section 2.2. Propagates via standard `Create` and `Announce` activities.

Standard ActivityPub activities apply without modification: `Create`, `Update`, `Delete`, `Announce`, `Follow`, `Accept`, `Reject`, `Undo`.

### 3.4 Relation to Mastodon and Friendica

ProFed aims to be a drop-in peer for Mastodon and Friendica instances. Concretely:

- A Mastodon user can follow a ProFed user and receive their posts. The CV data is invisible to Mastodon but does not interfere with it.
- A Mastodon user can follow a ProFed job board (`Group`) and receive job postings as boosted notes in their timeline.
- A Friendica user benefits from the `Group`/forum semantics which Friendica already implements and understands.
- A Mastodon or Friendica user cannot follow a Search Actor in a meaningful way from their client — the client does not know how to display search results — but the ActivityPub protocol mechanics work correctly regardless.

ProFed clients (and ProFed-aware clients) can use the Mastodon client API to interact with ProFed. Professional-specific features (CV editing, job posting creation, saved search management) require ProFed-specific API endpoints, which are outside the scope of this document.

---

## 4. Discussion

This document is an invitation to discuss. All aspects of the design are open for comment — including the foundational decisions that may appear settled. We are at the stage where a different perspective on any part of the architecture is more valuable than a polished specification.

---

## Appendix A: JSON-LD Examples

These examples illustrate the data structures described in the main text. They represent the current design and are subject to change, particularly where noted.

### A.1 Person Actor with Resume (abbreviated)

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    "https://w3id.org/security/v1",
    {
      "profed": "https://profed.social/ns#",
      "resume": "profed:resume"
    }
  ],
  "type": "Person",
  "id": "https://profedtest.okunah.de/actors/christof",
  "preferredUsername": "christof",
  "name": "Christof Josef Donat",
  "summary": "\"Fearless when facing complex challenges\" (Roland Bock, PPRO)",
  "inbox":   "https://profedtest.okunah.de/actors/christof/inbox",
  "outbox":  "https://profedtest.okunah.de/actors/christof/outbox",
  "icon":  { "type": "Image", "url": "https://profedtest.okunah.de/media/..." },
  "image": { "type": "Image", "url": "https://profedtest.okunah.de/media/..." },
  "publicKey": { "...": "..." },
  "resume": {
    "experience": [
      { "name": "Main Developer and Architect",         "org": "ProFed Project", "start": "2025-10", "end": "now"     },
      { "name": "Senior Python Software Engineer",      "org": "Swiss Re",       "start": "2025-07", "end": "2025-09" },
      { "name": "Senior Quantitative Python Developer", "org": "Credit Suisse",  "start": "2019-05", "end": "2024-01" }
    ],
    "education": [
      { "name": "Mathematics and Computer Science", "org": "University Ulm",                     "start": "1997-10", "end": "1999-12" },
      { "name": "University Entrance Diploma",      "org": "Rudolf-Diesel-Gymnasium Augsburg",   "start": "1994-07"                   }
    ],
    "skills": [
      { "name": "Python"      },
      { "name": "FastAPI"     },
      { "name": "PostgreSQL"  },
      { "name": "C++"         },
      { "name": "ActivityPub" }
    ],
    "projects": [
      {
        "name": "ProFed",
        "url":  "https://codeberg.org/ProFed/ProFed",
        "summary": "Federated professional social network.",
        "skills": [
          { "name": "Python"      },
          { "name": "FastAPI"     },
          { "name": "ActivityPub" }
        ]
      }
    ]
  }
}
```

### A.2 Job Posting Object

The field `salary` is not yet part of the design — its format remains an open question.

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    {
      "profed":      "https://profed.social/ns#",
      "JobPosting":  "profed:JobPosting"
    }
  ],
  "type":         "JobPosting",
  "id":           "https://example.profed.social/jobs/42",
  "attributedTo": "https://example.profed.social/actors/alice",
  "published":    "2025-06-01T10:00:00Z",
  "to": ["https://www.w3.org/ns/activitystreams#Public"],

  "name":             "Senior Rust Developer",
  "summary":          "We are building a distributed data processing platform.",
  "content":          "<p>Full job description...</p>",
  "org":              "ACME GmbH",
  "adr":              "Berlin, Germany",
  "employment-type":  "full-time",
  "remote":           "hybrid",
  "end":              "2025-08-31",
  "skills": [
    { "name": "Rust"                 },
    { "name": "Distributed Systems" },
    { "name": "PostgreSQL"          }
  ]
}
```

### A.3 Search Actor

```json
{
  "@context": [
    "https://www.w3.org/ns/activitystreams",
    {
      "profed":       "https://profed.social/ns#",
      "queryString":  "profed:queryString",
      "queryFilters": "profed:queryFilters"
    }
  ],
  "type":              "Service",
  "id":                "https://example.profed.social/searches/abc123",
  "preferredUsername": "search-rust-dev-remote",
  "name":              "Jobs: Rust Developer (Remote)",
  "inbox":     "https://example.profed.social/searches/abc123/inbox",
  "outbox":    "https://example.profed.social/searches/abc123/outbox",
  "followers": "https://example.profed.social/searches/abc123/followers",
  "following": "https://example.profed.social/searches/abc123/following",
  "publicKey": { "...": "..." },

  "queryString": "Rust developer",
  "queryFilters": {
    "type":   "JobPosting",
    "remote": "yes"
  }
}
```

---

## Appendix B: Microformats2 Field Mapping

This table documents the correspondence between mf2 property names (as used on personal websites) and the JSON field names used in ProFed's AP objects. The mf2 type prefix (`p-`, `dt-`, `u-`, `e-`) is stripped to produce the JSON key.

### h-card → Person actor

| mf2 property  | AP field     | Notes                                                                          |
|:--------------|:-------------|:----------------------------------————————————————————————————————————————————-|
| `p-name`      | `name`       |                                                                                |
| `p-note`      | `summary`    |                                                                                |
| `p-job-title` | —            | Display field; not in AP actor                                                 |
| `p-location`  | `org`        | Current profile organisation; importer reads `location`, falls back to `p-org` |
| `u-photo`     | `icon.url`   |                                                                                |
| `u-url`       | `url`        |                                                                                |

### h-resume → resume object

**Experience and Education entries** (each is an `h-event` within `p-experience` / `p-education`):

| mf2 property | JSON field | Notes                                 |
|:-------------|:-----------|:--------------------------------------|
| `p-name`     | `name`     | Job title or degree name              |
| `p-org`      | `org`      | Employer or institution               |
| `dt-start`   | `start`    | `YYYY-MM` or `YYYY`                   |
| `dt-end`     | `end`      | `YYYY-MM`, `YYYY`, or `"now"`         |

**Skills** — each `p-skill` value maps to `{ "name": "<value>" }`.

**Projects** — each project entry uses `p-name`, `u-url`, `p-summary`, `e-content`, and nested `p-skill` entries.

---

*This document is maintained at [https://codeberg.org/ProFed/ProFed](https://codeberg.org/ProFed/ProFed). Feedback via issues or pull requests is welcome.*
