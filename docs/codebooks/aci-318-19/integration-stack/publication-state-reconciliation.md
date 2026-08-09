# ACI 318-19 publication-state reconciliation

Base: `feature/aci-318-19-structural-measurement`.

Owns:
- printing, correction, errata, and other publication-state evidence for the exact retained ACI artifact;
- explicit comparison between retained bytes and authoritative correction evidence where legally and operationally available;
- source-safe recording of what is known, unknown, or conflicting about correction incorporation;
- preserving the retained artifact as the base source rather than silently rewriting it.

Does not own:
- parser or semantic implementation;
- replacing retained bytes with a newer copy;
- silently applying current web errata to the base artifact.

Completion:
- final integration can distinguish exact-retained-artifact claims from broader ACI 318-19 publication-state claims;
- correction evidence is explicit and provenance-backed;
- unresolved correction state remains visible.

Evidence join: final `feature/aci-318-19-integration-closeout` must consider this branch before broader publication-state claims.
