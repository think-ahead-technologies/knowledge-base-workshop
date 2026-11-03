---
id: resource/cra-art-13/cybersecurity-risk-assessment
title: "Cybersecurity risk assessment (Bewertung der Cybersicherheitsrisiken)"
status: active
tags: [cyber-resilience-act, cra-article-13, risk-assessment]
source: https://kunnus.tech/knowledge-base/articles/13
ingested: 2026-11-03
last_reviewed: 2026-11-03
---

# Cybersecurity risk assessment (Bewertung der Cybersicherheitsrisiken)

Art. 13(2) requires manufacturers to carry out an assessment of the cybersecurity risks ("Bewertung der Cybersicherheitsrisiken") of a product with digital elements and to take its outcome into account in the planning, design, development, production, delivery and maintenance phases, to minimise risks, prevent incidents and limit their impact, including on user health and safety.

Per Art. 13(3) the assessment is documented and, where relevant, updated during the support period. At minimum it analyses risks based on the intended purpose ("Zweckbestimmung") and reasonably foreseeable use (operating environment, assets to protect), considering the expected product lifetime. It must state whether and how the security requirements of Annex I Part I point 2 apply and are implemented, how Annex I Part I point 1 is applied, and how the vulnerability-handling requirements of Annex I Part II are met.

Art. 13(4): the assessment goes into the technical documentation (Art. 31, Annex VII). For products under Art. 12 that are also subject to other Union law, it may be part of the risk assessment required there. Where an essential requirement does not apply, the documentation must contain a clear justification. Art. 13(7) requires systematic documentation of all relevant cybersecurity aspects, including known vulnerabilities and relevant third-party information, and updating the assessment where needed.

Commission guidance as summarised on the page (non-binding, C(2026) 5252 final):
- 2.6: legacy/interoperability constraints are not exempt; document the constraint, assess the risk, apply compensating measures, re-assess periodically. If both a legacy and a secure protocol are supported, the secure one must be the default.
- 2.7: products designed before 11 December 2027 need no redesign if a current risk assessment shows existing measures cover the risks; historical design/test docs need not be reconstructed.
- 4.3: an update is a substantial modification ("wesentliche Änderung") only if it changes the assessed intended purpose or creates risks not covered by the assessment; security updates are normally not. Four criteria: new threat vectors, new attack scenarios, changed likelihood, changed impact of known scenarios.
- 7.1-7.2: no own "risk appetite"; residual risks are measured against the "angemessenes Cybersicherheitsniveau"; cost or commercial reasons do not justify untreated risks; transferring risk to users or third parties is not a compliance strategy.
- 7.3: external dependencies (backends, infrastructure) are assessed and mitigated on the product side.
- 7.4: variants with the same architecture, security-relevant design, purpose and risk profile may share one assessment, technical documentation and declaration of conformity.
- 8.2-8.3: remote data processing solutions (RDPS) belong in the risk assessment and technical documentation.

## In this resource
[CRA Art. 13 - Obligations of manufacturers (Pflichten der Hersteller)](resource/cra-art-13){"type":"part-of","link-info":"Art. 13 paragraphs 2-4 and 7; guidance sections 2.6, 2.7, 4.3, 7.1-7.4"}

## Mentions
- Art. 12
- Art. 31
- Art. 31(2)
- Annex I Part I (points 1 and 2)
- Annex I Part II
- Annex II
- Annex VII
- Recital 34
- Recital 55

## Related
- <https://eur-lex.europa.eu/legal-content/DE/TXT/HTML/?uri=CELEX:32024R2847>

## Cross-references
- [CRA Art. 12 - High-risk AI systems](resource/cra-art-12){"type":"related","link-info":"cited in the legal text of Art. 13"}
- [CRA Art. 31 - Technical documentation](resource/cra-art-31){"type":"related","link-info":"cited in the legal text of Art. 13"}

## Concept links
- [CRA market-availability conditions - Annex I Part I and Part II](resource/cra-art-06/cra-market-availability-conditions){"type":"related","link-info":"Annex I conditions vs the risk assessment that applies them"}

