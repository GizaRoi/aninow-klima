# Space Apps Guidance for This Prototype

Checked 2026-11-14. This is a source-based implementation note, not an official rulebook or a claim of submission eligibility.

## Verified current sources

- [2026 official event overview](https://www.spaceappschallenge.org/2026/): register for the hackathon, select a Local or Universal Event, and join/form a team of no more than six. The overview lists project submission via the Team page's Project tab, opening November 14 at 09:00 and closing November 15 at 23:59 local time. Confirm the applicable event/timezone and any local presentation schedule in the participant dashboard or with the Local Lead.
- [Field Shift challenge](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/): develop decision support combining NASA Earth observations, local soil information, crop characteristics and farmer priorities to explore rotations and resilience.
- [2026 NASA announcement](https://science.nasa.gov/universe/nasa-welcomes-all-ages-experience-levels-for-space-apps-challenge/): describes the November 14–15 event and use of NASA's free/open data.

The current event overview/challenge summaries were retrievable through indexed official sources. Direct guide retrieval repeatedly returned errors. No source was substituted from another NASA competition.

## Guides requiring confirmation

Official entry points:

- [Resources](https://www.spaceappschallenge.org/resources/)
- [Project submission guide](https://www.spaceappschallenge.org/resources/project-submission-guide/)
- [Participant FAQ](https://www.spaceappschallenge.org/resources/participant-faq/)

The current guide pages were not reliably accessible during implementation. Confirm exact deliverables, deadlines, source/code accessibility, judging rubric, AI/tool disclosure, rules about prior work and asset/brand use from the current guides or Local Lead before submitting. Older-year FAQs, staging content and Local Lead pages were not treated as the global 2026 rulebook. No exact video duration, slide count, or AI permission is asserted here.

## How the prototype follows the verified direction

| Challenge element | Implemented demonstration | Remaining work |
|---|---|---|
| NASA environmental evidence | Real archived POWER sample, dates/units/source link and reproducible fetch script | Reviewed ingestion/quality policy; IMERG integration; connection to decision features |
| Local soil information | Drainage input with an explicit unknown state | Real soil evidence, reviewed interpretation and local agronomic validation |
| Crop characteristics/rotation | Rice baseline, one example alternative, timeline and explanatory checks | Replace synthetic numbers with published local profiles; add crop history/harvest evidence |
| Farmer priorities | Water, affordability, calendar, soil-care and income choices; constraints remain visible | Reviewed priority ordering over sufficiently supported candidates |
| Explainability | Reasons, assumptions, unknowns, simulated outcomes and data-source page | Farmer/adviser review and validated predictive estimates |

The prototype is an interaction demonstration, not a finished challenge submission. Actual source use is limited to the archived context cards; synthetic fixture calculations are clearly identified. Preserve attribution, third-party permissions, and records of AI assistance as project practices, and verify current formal disclosure/license requirements separately. NASA does not endorse this project.
