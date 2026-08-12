# NDS 2018 whole-document replay measurement

Canonical roadmap: issue #219.

## Exact source boundary

Measurement uses the retained `nds-2018.pdf` artifact registered as SHA-256 `581353dab836de933546bc93b8265674dabb08d1073da04d660cf894250b48b4` (6,791,825 bytes, 206 PDF pages). The digest was recomputed from the retained bytes before measurement. Protected source prose, page images, reconstructive tables, figures, and generated source-reconstructive AST output remain outside Git.

The retained PDF has extractable text on all 206 pages. Applying the landed NDS layout evidence boundary leaves 4,510 text blocks after recurring artifact/page-furniture removal, with 11 recurring furniture keys. The source-safe core measurement digest is `7dc08b76fe40a3653ea3bfd60d7654f7a894fce375ec747191d60747d7507e11` after correcting the appendix-equation denominator described below.

## Structural measurement

The current NDS recognition boundary is collision-free for the measured chapter, section, appendix, equation, and figure locator families:

- 16 chapter observations / 16 unique chapter locators;
- 704 section observations / 704 unique section locators;
- 13 explicitly lettered appendix observations / 13 unique appendix locators;
- 79 currently recognized equation observations / 79 unique equation locators;
- 39 currently recognized figure observations / 39 unique figure locators.

The current table overlay observes 24 caption occurrences across 20 native identifiers. Four identifiers repeat once, producing eight caption observations. These are caption observations, not a claim that the source contains only 20 tables or that repeated captions are automatically continuation relationships.

## Measured unsupported or ambiguous families

Whole-document measurement exposes concrete source families outside the current non-prose recognition grammar:

- 18 appendix equation-label observations use letter-qualified appendix identifiers that are outside the current numeric equation grammar;
- 85 content table-caption observations use native locator shapes outside the current numeric-plus-letter table grammar;
- 11 content figure-caption observations use native locator shapes outside the current numeric-plus-letter figure grammar;
- one appendix heading exposes source role while its publication-native appendix locator is absent from extracted text, so it remains unresolved rather than being invented;
- 542 retained text blocks contain private-use glyph evidence and therefore require non-semantic preservation rather than flattened mathematical interpretation.

The appendix-equation count was originally recorded as 13. Exact-source replay during the bounded appendix-equation remediation re-enumerated every trailing parenthesized locator accepted by the publication-specific appendix equation grammar and found 18 source observations. All 18 belong to the same letter-qualified appendix equation family; the earlier value had inadvertently mirrored the 13-appendix count. The corrected denominator changes no previously recognized numeric equation count and does not broaden the selected locator family beyond appendix letters A through N with optional dotted subsection qualification.

These measurements establish real parser-remediation candidates. They do not by themselves choose a representation, infer table continuation, recover equation mathematics, interpret figures, or authorize semantic promotion. Any descendant correction should begin from representative source evidence for one coherent locator/structure family rather than expanding all non-prose grammar at once.

## Claim boundary

This gate measures structural recognition only. It does not claim generated semantic coverage, parsed semantic coverage, reviewed semantic coverage, or executable engineering/project-evaluation capability. Unsupported and ambiguous regions remain evidence states rather than being normalized away.

The machine-readable source-safe measurement is retained at `corpora/nds-2018/nds-2018-whole-document-replay-measurement.json`.
