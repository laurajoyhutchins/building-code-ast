# NDS 2018 publication-state reconciliation

Predecessor: `feature/nds-2018-structural-measurement`.

This is a parallel evidence sidecar, not part of the semantic trunk.

Owns:
- investigating printing, correction, addenda, and errata state for the retained NDS 2018 artifact;
- comparing exact artifact identity and compact publication-state facts against independently obtained authoritative evidence where lawfully accessible;
- recording discrepancies without silently replacing the retained source bytes;
- defining what stronger publication-state claims are and are not justified at integration closeout.

Does not own:
- parser behavior or AST repair;
- substituting another PDF as the source artifact;
- copying errata, source prose, tables, figures, or page images into public Git;
- blocking ordinary compiler work that depends only on the exact retained artifact.

Completion:
- printing/correction/errata questions are either evidence-backed or explicitly unresolved;
- any material discrepancy is documented with exact artifact identities and downstream implications;
- no source substitution occurs implicitly;
- final integration closeout can calibrate publication-state claims against this evidence.

Join point: `feature/nds-2018-integration-closeout` must consider this sidecar before making claims broader than the exact retained artifact.