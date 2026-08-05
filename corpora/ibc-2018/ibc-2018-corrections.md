# IBC 2018 verification corrections

## Caption occurrence consolidation

An early caption-occurrence total of 266 was not a logical table count. Continuation and repeat captions were consolidated into 215 logical table records. The 266 occurrences remain source anchors.

## Embedded labels inside Figure 2308.6.7.2

Four labels reading `TABLE 2304.10.1` on PDF page 556 were initially eligible caption candidates. Their geometry and surrounding figure evidence show that they are labels embedded in a figure. The candidates are retained with `rejected_embedded_in_figure` disposition and do not increase the formal-table count.

## Exception child inflation

An early 1,294-line exception result counted numbered child items as independent exceptions. The corrected policy counts 769 explicit marker blocks and attaches 881 numbered children to those blocks.

## Equation false positives

A broad 762-line formula-like scan admitted prose measurements, unit fragments, external-standard designations, variable definitions, figure labels, and continuations. The displayed-block policy was tightened and the superseded candidates were not promoted. The current baseline contains 90 primary displayed equation or formula blocks with attachments.
