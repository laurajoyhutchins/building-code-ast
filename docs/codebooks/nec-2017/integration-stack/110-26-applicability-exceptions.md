# NEC 110.26 applicability and exceptions

Predecessor: `feature/nec-110-26-table-lookup`.

Owns:
- the structural ownership and reviewed semantic representation of applicability conditions and exceptions required by the complete 110.26 rule family;
- multiple, nested, and scoped exception attachment with exact source evidence;
- explicit unresolved attachment or logical-grouping states rather than proximity-based guesses;
- publication-neutral semantic vocabulary additions only when the reviewed rule family proves a genuine gap.

Does not own:
- project-specific applicability decisions;
- definition/reference graph construction;
- broad NEC exception automation;
- compliance evaluation.

Completion:
- supported 110.26 applicability and exception relationships preserve exact structural ownership and reviewed meaning;
- ambiguous ownership or logical grouping blocks accepted semantic promotion;
- parser candidates remain distinct from approved interpretation;
- synthetic tests cover nested/multiple/ambiguous exception cases without NEC source text.

Successor: `feature/nec-110-26-definition-reference-edges`.
