# Architecture decision records

One file per decision: context, decision, alternatives considered, consequences. A decision is
never edited to hide that it changed; it is superseded by a new record.

| # | Decision | Status |
|---|---|---|
| [0001](0001-repository-strategy.md) | Fork-in-tree with an unmodified upstream root commit | Accepted |
| [0002](0002-upstream-base.md) | Base on Zen `stable` 1.23.4b / Firefox 158.0.1, not `dev` | Accepted |
| [0003](0003-theming-mechanism-and-palette.md) | Theme through Zen's variables and the preprocessor; adjust `ash-500` | Accepted |
| [0004](0004-upstream-service-isolation.md) | Detach from Zen-operated services; no update channel yet | Accepted |
| [0005](0005-application-identity.md) | Application identity: `nivora`, vendor, distribution id | Accepted, partly unverified |
