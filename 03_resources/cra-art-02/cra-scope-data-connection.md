---
id: resource/cra-art-02/cra-scope-data-connection
title: CRA scope - products with digital elements and a data connection
status: active
tags: [cyber-resilience-act, cra-article-02, cra-scope, data-connection, product-cybersecurity]
source: https://kunnus.tech/knowledge-base/articles/2
ingested: 2026-11-03
last_reviewed: 2026-11-03
---

# CRA scope - products with digital elements and a data connection

Art. 2(1) CRA sets the positive scope: the regulation applies to "auf dem Markt
bereitgestellte Produkte mit digitalen Elementen, deren bestimmungsgemäßer Zweck
oder vernünftigerweise vorhersehbare Verwendung eine direkte oder indirekte
logische oder physische Datenverbindung mit einem Gerät oder Netz einschließt".
Two conditions follow: the product is made available on the EU market, and its
intended purpose or reasonably foreseeable use includes a direct or indirect,
logical or physical data connection to a device or network.

The page adds the (non-binding) EU Commission guidance of 27 July 2026
(C(2026) 5252 final) on how to read this:

- **Data connection vs. mere electronics (guidance 2.5)** - scope hinges on a
  data connection, not on electronics being present. A sender must deliberately
  encode binary states as information that a receiver can decode as data.
  Merely switching an output (0/1) or supplying power is not a data connection.
- **Software as a product (guidance 2.2)** - software is a product only if it is
  provided to the user and runs on the user's system: locally installed apps,
  browser extensions, desktop apps built with web technology. Browser-only web
  apps / PWAs and pure information websites are not products themselves; they
  count only as remote data processing ("Datenfernverarbeitung", RDPS) when they
  support a product function (recitals 11, 12).
- **Placing standalone software on the market (guidance 2.1)** - all copies of a
  version count as placed on the market at the moment of first offer; later
  downloads are only "Bereitstellen auf dem Markt". Iterations without a
  substantial modification keep the date; variants (per-OS builds, feature
  bundles) are separate products.
- **Open source (guidance 3.1-3.2)** - FOSS is placed on the market only when the
  party controlling releases and distribution monetises that version (price,
  monetisation via the software, mandatory data processing, paid version with
  support). Donations, optional consulting and third-party funding alone do not
  trigger scope; FOSS definition per Art. 3 Nr. 48.
- **RDPS (guidance 8.1)** - remote processing is part of the product if it is
  (cumulatively) done at a distance, needed for a product function (incl.
  onboarding, sync, configuration, updates, IAM) and developed by or under the
  responsibility of the manufacturer. Pure telemetry, standard third-party SaaS
  and internal systems (HR, CRM, CI/CD) are not RDPS.

## In this resource
[CRA Art. 2 - Scope (Anwendungsbereich)](resource/cra-art-02){"type":"part-of","link-info":"paragraph (1) and guidance sections 2.1, 2.2, 2.5, 3.1-3.2, 8.1"}

## Mentions
- Art. 3 Nr. 48 (FOSS definition, cited in guidance 3.1-3.2)
- Recitals 11, 12, 18 (cited in the guidance)

## Related
- <https://eur-lex.europa.eu/legal-content/DE/TXT/HTML/?uri=CELEX:32024R2847>

## Cross-references
- [CRA Art. 3 - Definitions](resource/cra-art-03){"type":"related","link-info":"cited only in the non-binding guidance/vendor commentary on Art. 2"}

## Concept links
- [CRA product with digital elements](resource/cra-art-03/product-with-digital-elements){"type":"related","link-info":"scope criterion vs product definition"}
- [CRA remote data processing (Datenfernverarbeitung, RDPS)](resource/cra-art-03/remote-data-processing){"type":"related","link-info":"scope vs remote data processing definition"}

