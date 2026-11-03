<!-- WebFetch rendering of https://kunnus.tech/knowledge-base/articles/14 (fetched 2026-11-03). The tool returned a condensed English summary, not verbatim text. Verbatim German text: page.html / page.txt. -->

**Article 14: Manufacturer reporting duties**

- **Actively exploited vulnerabilities (para. 1-2):** Report to the coordinating CSIRT and ENISA via the single reporting platform. Send an early warning within 24 hours of becoming aware, a notification within 72 hours, and a final report within 14 days after a fix or mitigation is available. The early warning must name the Member States where the product was made available.
- **Severe security incidents (para. 3-4):** Same reporting route. The early warning is due within 24 hours and must state whether malicious or unlawful action is suspected. The notification follows within 72 hours, and the final report within one month of that notification.
- **Severity (para. 5):** An incident is severe if it can impair the availability, authenticity, integrity, or confidentiality of sensitive or important data or functions, or if it led or can lead to malicious code running in the product or in a user's systems.
- **Interim reports (para. 6):** The CSIRT can request status updates.
- **Where to report (para. 7):** The CSIRT of the Member State of the manufacturer's main EU establishment. Without an EU establishment, use the fallback order: authorised representative, importer, distributor, then the Member State with the most users.
- **User information (para. 8):** Inform affected users, and where necessary all users, about the risk and available fixes or mitigations, ideally in a machine-readable format. If the manufacturer fails to do so in time, CSIRTs may inform users.
- **Delegated and implementing acts (para. 9-10):** The Commission can specify delay conditions and reporting formats.

**Commission guidance (dated 27 July 2026, non-binding)**

- **Open-source stewards:** Duties depend on the kind of support. Pure non-technical support (governance, branding, events) carries no reporting duty for exploited vulnerabilities. Infrastructure stewards (repositories, signing keys) report severe incidents. Engineering stewards also report exploited vulnerabilities and inform users. Roles are assessed per project.
- **Timing:** Reporting duties apply from 11 September 2026, ahead of full CRA application in December 2027. They cover products already on the market and products past end of support. There is no retroactive reporting for exploitation known before that date.
- **Awareness:** The 24-hour clock starts when the manufacturer has reasonable certainty after a prompt initial assessment, not when a CVE is published.
- **Third-party components:** Only exploitable issues in your own product are reportable. Otherwise, report voluntarily and pass the information upstream to the component maintainer.
- **User notification:** Risk-based. Share details first with affected customers, and publish more broadly after a fix.

**Common manufacturer questions (FAQ summary)**

- The early warning needs at least the affected product, the type of vulnerability if known, and an initial risk assessment. The full analysis follows in the 72-hour notification.
- Importers and distributors must inform the manufacturer and cooperate, but the primary duty lies with the manufacturer.

**Practical preparation**

- Name reporting owners and deputies.
- Prepare templates for the 24-hour and 72-hour reports.
- Set up vulnerability monitoring with alerting.
- Define how quickly suspected cases are assessed.
- Run the process once as an exercise.
