<!-- WebFetch condensed rendering of https://kunnus.tech/knowledge-base/articles/13 (fetched 2026-11-03). The tool declined a verbatim reproduction; the full German legal text is in page.txt / page.html. -->

**Article 13 (CRA, Regulation (EU) 2024/2847): manufacturer duties, in 25 paragraphs**

- **Paras 1-3:** Products must meet Annex I Part I requirements. Manufacturers must run and document a cybersecurity risk assessment, which covers intended and foreseeable use and is updated over the support period. For example, para 1 says manufacturers "gewährleisten, dass dieses Produkt" meets the basic cybersecurity requirements.
- **Paras 4-7:** The risk assessment goes into the technical documentation. Third-party and open-source components require due diligence, and vulnerabilities in components must be reported upstream and fixed.
- **Paras 8-11:** Vulnerabilities must be handled throughout the product lifetime and support period. The support period is at least five years, or the expected use period if shorter. Security updates stay available for at least ten years. Older versions may be handled under certain conditions.
- **Paras 12-16:** Conformity assessment, EU declaration of conformity, CE marking, record retention (at least ten years or the support period), serial-production conformity, product identification, and manufacturer contact details.
- **Paras 17-20:** A single point of contact for users, information and instructions for users, and a copy or simplified version of the declaration of conformity.
- **Paras 21-25:** Corrective action when a product is non-compliant, cooperation with market surveillance authorities, notice before ceasing business, and implementing acts on the SBOM format. The ADCO may also assess dependencies on software components.

**Commission guidance (as described on the page)**

The page summarizes guidance sections 2.6, 2.7, 3.4-3.5, 4.3, 5, 7.1-7.4, 8.2-8.3, and 9.2. The main points are:
- **2.6:** Interoperability constraints must be documented, risk-assessed, and mitigated, and reviewed during the support period.
- **2.7:** Products designed before CRA applies need a current risk assessment, but not a redesign.
- **3.4-3.5:** Integrating open-source components does not make the integrator responsible for those components' own compliance, but due diligence is required.
- **4.3:** A software update is a substantial modification only if it changes the risk profile, not because of its size.
- **5:** The support period is based on expected use. Five years is a minimum, not a default.
- **7.1-7.4:** Residual risk is judged against the product's appropriate cybersecurity level, not the manufacturer's risk appetite. Product variants with the same security-relevant design can share one assessment.
- **8.2-8.3:** Remote data processing services (RDPS) must be documented in the product's technical documentation, and third-party services are treated as external dependencies.
- **9.2:** Vulnerability handling covers upstream reporting, checking known vulnerabilities, and documented release decisions.

**FAQ (summary)**

The FAQ covers the main duties, the minimum support period, whether the SBOM must be published (it is not required publicly), penalties (up to EUR 15M or 2.5% of global turnover), application to products developed before December 2027, and operational steps for implementation.

**Related recitals**

The page lists recitals 50 to 64.

**Caveats**

- The page itself states that only the official EUR-Lex text is legally binding, and that the Commission guidance is not binding.
- Guidance document C(2026) 5252 final is cited by the page; not verified against the primary source.
