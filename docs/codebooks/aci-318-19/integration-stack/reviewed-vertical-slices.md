# ACI 318-19 reviewed vertical slices

Predecessor: `feature/aci-318-19-semantic-review`.

Owns:
- end-to-end reviewed rule families chosen from measured exact-source evidence;
- at least one equation-backed normative rule, one table/lookup-backed rule, and one prose/definition/reference-heavy rule;
- exact traceability from source geometry through Document AST, relationships, Provision AST, and review evidence;
- commentary evidence where useful without changing normative authority.

Does not own:
- broad semantic coverage claims from a small reviewed sample;
- project calculations, design, or compliance decisions;
- source reconstruction in public fixtures.

Completion:
- contrasting reviewed slices traverse the complete compiler path deterministically;
- every semantic claim points to exact normative evidence;
- commentary evidence remains separately typed;
- unsupported transitions are explicit rather than manually patched around.

Successor: `feature/aci-318-19-semantic-measurement`.
