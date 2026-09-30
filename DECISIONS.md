# Health Project Decisions

This file records durable project decisions for the Health project. Entries remain authoritative unless explicitly superseded by a later decision.

## 2026-09-30 — Precert is not managed in Linear

**Status:** Active

**Decision:** Precert is not a Linear-managed workstream.

All precert planning, task state, decisions, coordination, and project administration must remain within the Health project's private ChatGPT-administered project system and its authoritative project artifacts.

Precert work must not be:

- created in Linear;
- tracked in Linear;
- mirrored or synchronized to Linear;
- migrated to Linear;
- administered through Linear; or
- represented in Linear as a project, issue, sub-issue, workstream, or equivalent tracking object.

The existence of other Health-related work in Linear does not alter this rule.

If any precert work is discovered in Linear, treat that as a governance conflict requiring correction rather than evidence that Linear is an authorized precert system.

This decision remains authoritative unless the user explicitly changes it.

## 2026-09-30 — Private health information must never be published to public Git

**Status:** Active

**Decision:** Private health information and other sensitive personal health data must never be committed, pushed, uploaded, copied, or otherwise published to any public Git repository or public Git-hosted artifact.

This prohibition includes, but is not limited to:

- medical records, clinical notes, test results, imaging, and reports;
- names, dates of birth, addresses, account or record identifiers, and other identifying information when associated with health information;
- private health data contained in source files, datasets, exports, attachments, screenshots, logs, fixtures, examples, prompts, issue bodies, pull requests, comments, build artifacts, or repository history; and
- derived or summarized material that could disclose private health information or identify the person to whom it relates.

**Private by default:** If there is uncertainty about whether material contains private health information or could expose sensitive personal health data, treat the material as private and do not place it in public Git unless it has been verified safe for public disclosure.

Public repositories may contain only material that has been deliberately reviewed and determined not to expose private health information.

If private health information is discovered in a public Git location, treat it as a security incident requiring immediate containment and remediation. Do not treat its prior presence as authorization for continued publication.

This decision remains authoritative unless the user explicitly changes it.

