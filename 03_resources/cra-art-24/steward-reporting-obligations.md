---
id: resource/cra-art-24/steward-reporting-obligations
title: Open-source software steward reporting obligations
status: active
tags: [cyber-resilience-act, cra-article-24, open-source-software-steward, vulnerability-reporting, incident-reporting]
source: https://kunnus.tech/knowledge-base/articles/24
ingested: 2026-11-03
last_reviewed: 2026-11-03
---

# Open-source software steward reporting obligations

Art. 24(3) CRA extends parts of the Art. 14 reporting regime to stewards:

- **Art. 14(1)** applies "soweit sie an der Entwicklung der Produkte mit
  digitalen Elementen beteiligt sind" - i.e. only to the extent the steward is
  involved in developing the product.
- **Art. 14(3) and (8)** apply to the extent that severe incidents
  ("schwerwiegende Sicherheitsvorfälle") affecting the security of products with
  digital elements affect network and information systems the steward provides
  for developing such products.

(The article numbers come from the legal text; what Art. 14(1), (3), (8) contain
is described here only as the page's guidance summary states it: 14(1) reporting
actively exploited vulnerabilities, 14(3) reporting severe incidents to
ENISA/CSIRT, 14(8) informing users.)

## Commission guidance tiering (non-binding, as summarised on the page)
Commission guidance C(2026) 5252 final of 27 July 2026, section 3.3, tiers the
duties by the kind of support given, per FOSS project:

- **Non-technical support only** (branding, governance, events, donations): no
  duty to report actively exploited vulnerabilities; pass information to the
  maintainers and consider voluntary reporting under Art. 15.
- **Infrastructure steward** (repositories, version control, signing keys):
  report severe incidents affecting product security to ENISA/CSIRT
  (Art. 14(3)), inform users where relevant.
- **Engineering steward** (developers, releases, vulnerability handling): report
  actively exploited vulnerabilities (Art. 14(1)) and inform users (Art. 14(8)).
- The same organisation can be steward for project A and manufacturer for
  project B (e.g. community vs. paid edition).
- Not-for-profit entities whose revenues serve statutory non-profit purposes do
  not place their FOSS on the market even when monetising it; steward duties
  apply.

## In this resource
[CRA Art. 24 - Obligations of open-source software stewards (Pflichten der Verwalter quelloffener Software)](resource/cra-art-24){"type":"part-of","link-info":"legal text paragraph 3 of Art. 24 and the guidance section 3.3 summary"}

## Mentions
- Art. 14(1), Art. 14(3), Art. 14(8)
- Art. 15 (guidance summary only)
- Art. 3 Nr. 14 (guidance summary only)

## Related
- <https://eur-lex.europa.eu/legal-content/DE/TXT/HTML/?uri=CELEX:32024R2847>

## Cross-references
- [CRA Art. 3 - Definitions](resource/cra-art-03){"type":"related","link-info":"cited only in the non-binding guidance/vendor commentary on Art. 24"}
- [CRA Art. 14 - Reporting obligations of manufacturers](resource/cra-art-14){"type":"related","link-info":"cited in the legal text of Art. 24"}
- [CRA Art. 15 - Voluntary reporting](resource/cra-art-15){"type":"related","link-info":"cited only in the non-binding guidance/vendor commentary on Art. 24"}

## Concept links
- [CRA free and open-source software and its steward](resource/cra-art-03/open-source-software-steward){"type":"related","link-info":"steward definition vs steward reporting duties"}
- [CRA actively exploited vulnerability reporting (24h / 72h / 14 days)](resource/cra-art-14/actively-exploited-vulnerability-reporting){"type":"related","link-info":"steward reporting applies the Art. 14 reporting duties"}
- [CRA fine-setting criteria, enforcement and exemptions](resource/cra-art-64/cra-fine-setting-and-exemptions){"type":"related","link-info":"steward duties vs the steward exemption from fines"}

