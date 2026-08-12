# Engineering Visual Memory v0.4 Evaluation Receipt

This receipt is source-safe. It contains no source text, figures, page renders, or private Drive identifiers.

- Release archive SHA-256: `4e4ed0ca37524c653768df81d5677f6115b2894934f02566dd0281ca068b5c76`
- CLIP checkpoint SHA-256: `40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af`
- Combined figure space: 796 objects, 7,686 views, 8 corpora.
- Page namespaces: 430 TMS 402/602 scan pages; 113 image-only AISC 360-16 pages.

## Figure-fragment recovery

| Corpus | Query | Retrieval result |
|---|---:|---:|
| NEC 2017 | 55% fragment | R@1 84.3%; R@5 98.6%; R@10 100% |
| NDS 2018 | 55% fragment | R@1 84.0%; R@5 96.0%; R@10 100% |
| ASHRAE 90.1-2016 | 40% fragment | R@3 100%; R@5 100% |
| ASHRAE 62.1-2016 | 40% fragment | R@3 100%; R@5 100% |
| Electrical Estimating Methods | 55% fragment | R@3 100%; R@5 100% |
| IBC 2018 private occurrences | 55% fragment | R@3 91.4%; R@5 100% |
| ACI 318-19, adaptive multiscale | 55% fragment | R@5 97.4% |
| NFPA 13-2019, adaptive multiscale | 55% fragment | exact R@5 90.0%; same-title-family R@5 95.3% |

## Page source re-identification

| Namespace | CLIP only | CLIP shortlist + ORB |
|---|---:|---:|
| TMS 402/602-2016, 55% fragment | R@1 39.3%; R@5 68.8% | R@1 74.9%; R@5 82.8%; source in CLIP top-50 95.1% |
| AISC 360-16 image-only pages, 55% fragment | R@1 29.2%; R@5 56.6% | R@1 80.5%; R@5 88.5%; source in CLIP top-50 95.6% |

## Architecture decisions supported by the measurements

1. Visual-object granularity dominates retrieval quality. Figure-level indexing materially outperforms full-page CLIP for technical documents.
2. Multiscale local views are adaptive. Add 50%-scale views when hard-fragment recovery demonstrates a scale mismatch.
3. Page-level exact source re-identification is a separate capability from semantic similarity and uses CLIP candidate generation plus local ORB verification.
4. Text context is channelized. Structural context survives when caption extraction is degraded; missing text remains explicit.
5. Logical visual identity is distinct from source occurrence identity for continuation or multipart figures.
6. Large indexes must be resumable and content-addressed at projection and embedding slices.
7. Cross-corpus cosine similarity is candidate generation only. Semantic or engineering analogy requires source-context and native-vision review.

## Claim boundaries

The figure-fragment metrics measure recovery of a known source occurrence, or a known repeated family where explicitly stated, under deterministic crop tests. They do not measure semantic engineering correctness. No cross-corpus similarity threshold is asserted to establish engineering equivalence.
