# NFPA 13 (2019) exception semantics

Predecessor: `feature/nfpa13-applicability-semantics` (PR #77)

Owns:
- the issue #3 exception vocabulary required by reviewed NFPA 13 provisions;
- structural attachment of exceptions to their actual owning requirement or scope;
- multiple and nested exception relationships;
- exact source spans plus explicit unresolved ownership;
- parser inference and review-state separation for exception candidates.

Does not own:
- applicability semantics already established by the predecessor;
- table, calculation, or figure meaning;
- definition/reference resolution beyond predecessor graph contracts;
- compliance or design conclusions.

Completion:
- synthetic fixtures cover multiple, nested, referenced, and ambiguously owned exceptions;
- nearest-sentence attachment is rejected where structural ownership disagrees;
- unsupported exception shapes preserve evidence and diagnostics;
- reviewed NFPA cases demonstrate faithful ownership without flattening nested requirements.

Successor: `feature/nfpa13-table-semantics-contract`.
