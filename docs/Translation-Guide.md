# English and Tagalog

The prominent **English / Tagalog** control stays at the top of every view. It uses language names, selected-state semantics and keyboard-accessible buttons. Selection is remembered in local storage when available; language switching continues to work if storage is unavailable. The document language and title update with the selection.

The UI uses a bundled, AI-authored Tagalog catalog at `apps/web/lib/messages.tl.json`. No Google service, API key or network translation request is used. The copy has not received native-speaker or agricultural-expert review and should be reviewed with the intended users before a production farmer-advisory release.

`apps/web/lib/language.tsx` provides shared language state. `translations.ts` translates catalog messages and formats result explanations for display. Crop IDs, inputs, checks, dates, currency values, comparison arithmetic and session saves keep their original semantics. Dates display using `fil-PH` in Tagalog while date inputs retain their ISO values. Brand names, official challenge titles, source URLs, measurements and unit symbols are retained.

The reusable [Tagalog localization skill](../.agents/skills/tagalog-localization/SKILL.md) is included in the repository and installed in the user's Codex skills folder. It guides direct translation and review, with familiar agricultural vocabulary and explicit preservation of uncertainty and demo labels. It is project-created, not a third-party translation product, and is available for future turns.

When adding copy, add both its English message and Tagalog counterpart, preserving interpolation tokens. Include accessible labels, validation, dynamic results, dialogs and source descriptions. Run the translation invariants and browser language-switching checks alongside the existing prototype tests.
