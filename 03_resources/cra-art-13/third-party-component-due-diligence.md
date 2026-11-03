---
id: resource/cra-art-13/third-party-component-due-diligence
title: "Due diligence for third-party and open-source components (gebotene Sorgfalt)"
status: active
tags: [cyber-resilience-act, cra-article-13, supply-chain, open-source, vulnerability-handling]
source: https://kunnus.tech/knowledge-base/articles/13
ingested: 2026-11-03
last_reviewed: 2026-11-03
---

# Due diligence for third-party and open-source components (gebotene Sorgfalt)

Art. 13(5): when integrating components sourced from third parties, manufacturers exercise due diligence ("lassen die gebotene Sorgfalt walten") so that those components do not compromise the product's cybersecurity - including free and open-source software ("freie und quelloffene Software") not made available in the course of a commercial activity.

Art. 13(6): when a manufacturer identifies a vulnerability in an integrated component, including an open-source one, it reports the vulnerability to the person or entity manufacturing or maintaining that component and handles and remediates it per Annex I Part II. If the manufacturer develops a software or hardware fix, it shares the code or documentation with the component maintainer, where appropriate in a machine-readable format.

Guidance as summarised on the page (non-binding):
- 3.4-3.5: integrating FOSS does not make the integrator responsible for the component's own CRA conformity; due diligence (Abs. 5) and upstream duties (Abs. 6) apply. A FOSS component's CRA status does not change because it is integrated into monetised products; package repositories have no CRA obligations.
- 7.3: due diligence means defining what the component must provide and verifying it risk-based - evidence such as the component maker's specs and security documentation, conformity/assurance docs, own tests.
- 9.2: report upstream only for the actually integrated version and per the maintainer's CVD process; no duty if already known (check databases/advisories) or if the project is orphaned; report only vulnerabilities of the component itself, not those created by integration; share fixes machine-readably and licence-compatibly; neither side must adopt the other's fix.

## In this resource
[CRA Art. 13 - Obligations of manufacturers (Pflichten der Hersteller)](resource/cra-art-13){"type":"part-of","link-info":"Art. 13 paragraphs 5-6; guidance sections 3.4-3.5, 7.3, 9.2"}

## Mentions
- Annex I Part II
- Recital 34

## Related
- <https://eur-lex.europa.eu/legal-content/DE/TXT/HTML/?uri=CELEX:32024R2847>

## Concept links
- [Voluntary security attestation programmes for FOSS](resource/cra-art-25/foss-security-attestation-programmes){"type":"related","link-info":"component due diligence that FOSS attestation supports"}

