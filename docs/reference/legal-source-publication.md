# Legal Reference: Copyright and Publication of Building-Code Sources

> **Status:** Project reference, reviewed July 23, 2026. This document records the repository's operating interpretation and source-publication policy. It is not legal advice and should be revisited before materially expanding the public corpus.

## Question addressed

When may Building Code AST store or publish exact regulatory language, and which parts of a codebook or incorporated standard should remain outside the public repository?

The central distinction is between:

1. law and official government-authored legal materials;
2. privately authored model codes and standards;
3. publisher-created expression such as layout, tables, figures, commentary, annotations, examples, and supplemental material; and
4. project-authored structures and transformations produced from lawfully handled sources.

These categories can coexist in one publication. Adoption of some text as law does not automatically make the publisher's entire codebook product freely redistributable.

## Controlling Supreme Court line

### *Wheaton v. Peters*, 33 U.S. (8 Pet.) 591 (1834)

The Court rejected a reporter's claim to exclusive rights in the Court's opinions. A reporter may claim copyright in independently authored material, but not in the judicial opinions themselves.

Official source: [U.S. Government Publishing Office](https://www.govinfo.gov/app/details/USREPORTS-33/USREPORTS-33-591)

### *Banks v. Manchester*, 128 U.S. 244 (1888)

The Court held that judicial opinions and official work prepared by judges as part of their public duties cannot be privately owned through copyright. The public must be free to reproduce the authoritative law.

Official source: [U.S. Government Publishing Office](https://www.govinfo.gov/app/details/USREPORTS-128/USREPORTS-128-244)

### *Callaghan v. Myers*, 128 U.S. 617 (1888)

The Court preserved the distinction between uncopyrightable judicial opinions and copyrightable editorial contributions created by a private reporter. Headnotes, arguments, indexes, arrangements, and other independently authored matter may remain protected even when published beside public legal text.

Official source: [U.S. Government Publishing Office](https://www.govinfo.gov/app/details/USREPORTS-128/USREPORTS-128-617)

### *Georgia v. Public.Resource.Org, Inc.*, 590 U.S. 255 (2020)

The Court described the animating principle of the government-edicts doctrine as "no one can own the law." The doctrine turns primarily on authorship: judges and legislators cannot be authors for copyright purposes when producing works in the course of their official duties. The Court therefore held that Georgia's official statutory annotations were ineligible for copyright even though the annotations did not themselves carry the force of law.

This decision does **not** establish that every privately authored standard becomes public domain whenever a government mentions or incorporates it.

Official source: [Supreme Court, U.S. Reports volume 590, part 1](https://www.supremecourt.gov/opinions/preliminaryprint/590US1PP_web.pdf) at 255.

## Model building codes adopted as law

### *Veeck v. Southern Building Code Congress International, Inc.*, 293 F.3d 791 (5th Cir. 2002) (en banc)

The Fifth Circuit held that privately authored model building codes entered the public domain **as the law of the municipalities that enacted them**. The same works retained copyright when distributed as model codes rather than as enacted municipal law.

This is the closest authority to Building Code AST's expected source material, but it is a Fifth Circuit decision rather than a nationwide Supreme Court holding. The repository should therefore avoid treating it as a blanket nationwide license to republish model-code books.

Sources:

- [Full opinion](https://law.justia.com/cases/federal/appellate-courts/F3/293/791/521953/)
- [U.S. Solicitor General's amicus brief at the certiorari stage](https://www.justice.gov/osg/brief/southern-building-code-v-veeck-amicus-petition)

## Standards incorporated by reference

### *American Society for Testing & Materials v. Public.Resource.Org, Inc.*, 82 F.4th 1262 (D.C. Cir. 2023)

The D.C. Circuit concluded that Public.Resource.Org's noncommercial publication of standards incorporated into law was fair use. The decision relied on the purpose of informing the public what the law requires and on publishing only versions given legal effect.

The decision is a fair-use holding, not a declaration that every incorporated standard is categorically in the public domain. Fair use remains fact-specific.

Reference: [U.S. Copyright Office case summary](https://www.copyright.gov/fair-use/summaries/amsoc-publicresourceorg-dccirc2023.pdf)

### *American Society for Testing & Materials v. UpCodes, Inc.*, No. 24-2965 (3d Cir. Apr. 7, 2026)

The Third Circuit affirmed denial of a preliminary injunction because UpCodes was likely to succeed on fair use. The court treated publication of incorporated standards as jurisdiction-specific law as a purpose distinct from publishing current industry standards, even though UpCodes operates a commercial platform.

The procedural posture matters: the ruling concerns likelihood of success at the preliminary-injunction stage, not a final judgment after a complete merits record.

Reference: [Third Circuit opinion text](https://law.justia.com/cases/federal/appellate-courts/ca3/24-2965/24-2965-2026-04-07.html)

## Repository publication rules

The public repository may contain:

- project-authored software, schemas, documentation, tests, and synthetic fixtures;
- official enactments or other public-domain legal text when the source and legal basis are documented;
- jurisdiction-specific adopted text obtained from a legally suitable official source;
- source metadata, locators, checksums, and local-ingestion instructions;
- project-authored ASTs, graphs, normalized facts, annotations, and analyses that do not unnecessarily reproduce protected expression; and
- short quotations where a reviewed lawful basis supports their use.

The public repository should not contain without separate clearance:

- a privately published model code merely because it is available online;
- a complete publisher-formatted codebook;
- typography, pagination, page images, illustrations, diagrams, ornamental arrangement, or other book design;
- publisher commentary, examples, annotations, explanatory notes, or supplemental matter not established to be part of the law or otherwise lawfully publishable;
- unincorporated standards or current best-practice editions when only an older edition has legal effect; or
- generated outputs that reproduce protected passages at substantial length merely because the output has been transformed into JSON, Markdown, an AST, or another format.

A transformation can contain new project-authored expression without extinguishing rights in copied source expression. The project should claim and license only what it has a sound basis to claim and license.

## Preferred source hierarchy

For exact text intended for public Git storage, prefer sources in this order:

1. an official legislature, agency, municipal, judicial, or government publishing source that expressly supplies the enacted text;
2. an official government repository or authenticated public record;
3. a source carrying express permission or a compatible license;
4. a reviewed source supported by a jurisdiction-specific public-domain or fair-use analysis; and
5. local-only ingestion when the publication basis remains uncertain.

A publisher's commercial PDF or web viewer should not become the default corpus source merely because it is convenient or visually complete.

## Required source decision record

Before adding non-synthetic source text or derived public artifacts, record:

- source title, edition, and date;
- issuing organization and adopting authority;
- jurisdiction and effective dates;
- exact provision or incorporated-material locator;
- official source URL or acquisition record;
- whether the source is enacted directly, adopted by reference, or indirectly incorporated;
- publication basis: government edict, public domain, permission, license, fair use, or another reviewed basis;
- included and excluded portions;
- transformation and quotation notes;
- checksum of the locally used source artifact;
- reviewer and review date; and
- any jurisdictional limitation or unresolved legal risk.

## Operational conclusion

Building Code AST can preserve exact source text as an ingestion and provenance invariant without placing every source artifact in public Git. Restricted or uncertain source material may remain local-only while the repository publishes project-authored code, source identities, spans, schemas, and cleared derived artifacts.

The legally safest public corpus is not a mirror of commercial codebooks. It is a provenance-rich collection of text with a documented publication basis, plus project-authored semantic structures that preserve the distinction between law, source expression, interpretation, and transformation.
