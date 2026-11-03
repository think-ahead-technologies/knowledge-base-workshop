---
id: resource/cra-art-03/remote-data-processing
title: "CRA remote data processing (Datenfernverarbeitung, RDPS)"
status: active
tags: [cyber-resilience-act, cra-article-03, remote-data-processing, cloud]
source: https://kunnus.tech/knowledge-base/articles/3
ingested: 2026-11-03
last_reviewed: 2026-11-03
---

# CRA remote data processing (Datenfernverarbeitung, RDPS)

"Datenfernverarbeitung" (point 2) is data processing at a distance for which software is designed and developed by the manufacturer or under its responsibility, and without which the product with digital elements could not perform one of its functions. Such solutions are part of the product (point 1).

Commission guidance (non-binding) section 8.1 reads this as three cumulative criteria: processing at a distance, functional necessity, and development by or under responsibility of the manufacturer. Key points: who operates it is irrelevant (on-prem or private cloud can be RDPS); "functions" includes onboarding, file sync, configuration, automatic update delivery and identity/access management; telemetry purely for statistics or product development is not RDPS (but its risks still belong in the risk assessment); own software on third-party IaaS/PaaS can be RDPS, while standard third-party SaaS is not RDPS but is treated like a third-party component (mitigate risks + due diligence); "under the manufacturer's responsibility" means built to the manufacturer's designs/specifications, not merely licensing an existing service; internal systems (HR, CRM, CI/CD, pentest infrastructure) are not RDPS; a website counts only if it contributes a function (e.g. an auth portal issuing tokens).

Section 8.3 walks five use cases: mobile banking app (own banking interface is RDPS, ledger systems behind it are not, third-party support chat is a component), smart thermostat and industrial robot (own cloud software on third-party IaaS is RDPS), e-reader (third-party SaaS storage is not RDPS but a component), mobile network (pure communication channel, neither).

## Mentions
- No other CRA article referenced in the definition itself.
- Guidance mentions NIS-2 evidence from IaaS providers.

## In this resource
[CRA Art. 3 - Definitions (Begriffsbestimmungen)](resource/cra-art-03){"type":"part-of","link-info":"Art. 3 point 2, plus guidance sections 8.1 and 8.3"}

## Concept links
- [CRA scope - products with digital elements and a data connection](resource/cra-art-02/cra-scope-data-connection){"type":"related","link-info":"scope vs remote data processing definition"}

