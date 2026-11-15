# Planting planner frontend

The Next.js application lives in `apps/web` on `feat/planting-planner`. It follows the existing visual prototype's forest green palette, farm artwork, glass panels, and lime accents. The model remains separate in `model/`.

The header and footer use the supplied `Version 2.png`, copied unchanged to `public/images/aninow-logo.png`. A shared SVG viewport excludes empty transparent margins when displaying it, preserving the complete leaf and wordmark. A light background gives the original dark green lettering contrast on the app's forest green shell. Logo dimensions adapt to desktop and phone widths without stretching the artwork.

## Run and verify

From the checkout root, run `npm install`, then `npm run dev`. On Windows PowerShell use `npm.cmd`. The dev server runs at `http://127.0.0.1:3000`.

- `npm run typecheck` checks TypeScript.
- `npm test` checks fixture behavior, input validation, and language catalog parity.
- `npm run build` exports the app to `dist/`.
- With the app serving at port 4173, `npx playwright test` checks the desktop and phone flows in installed Chrome.

## Content and preview boundary

The form, English/Tagalog copy, four crop fixtures, and priority weights were imported from the user-supplied `orca_share_media1794688206295_7527467922416547931.html` in the workspace root. The frontend deliberately preserves that reference's sample figures, including its 115-day rice fixture and 44-season example history. These differ from the current Python model; they must not be presented as model output. Results and downloads explicitly identify their sample status.

The inputs are pilot location (Muñoz, fixed), soil type (including unknown), standing water (no/yes/unsure), water source, rice harvest, next rice planting, and optional soil pH. Output controls cover normal, dry, and El Niño seasons and four priorities. Each crop shows fit, sample history, days needed, calendar use, condition ratings, soil benefits, missing checks, and questions for an agriculturist. Hard calendar and drainage exclusions stay visible alongside the rice baseline.

`lib/preview.ts` provides a typed `getPreviewComparison` adapter that returns the full display contract. It ports only the reference's illustrative client logic. It makes no network calls and does not invoke or modify the Python model. A future model adapter can replace this function and map model fields into the display contract. The current `soil` selection uses the HTML's series labels, while the model takes different field inputs; that mapping needs evidence and explicit agreement before integration. Do not treat the sample weighted average as the model's geometric mean or the sample history counts as actual observations.

The farm illustration was reused from `feat/visual-prototype`; it depicts no measured field. The browser stores only language preference. Field values and comparisons stay in memory until reload. Downloads contain a JSON comparison labeled `mode: sample`. Nothing is submitted to a server. Both languages preserve machine identifiers and input values; additional interface translations are AI-authored drafts awaiting farmer/agriculturist review.

The app supports phone and desktop layouts, keyboard navigation, input validation, document language, optional browser storage, expanded explanations, and reduced motion. The preview is a separate private Site, declared in `.openai/hosting.json`.

## Team and detailed results

`/team/` displays the four existing team portraits from the visual prototype at their original proportions. Names and roles are already part of the image artwork, so there are no duplicate visible captions. Each image retains the member's name as alternative text. Shared navigation and English/Tagalog controls are available on both pages.

The results screen has **Simple / More detailed** controls. More detailed opens every eligible crop's original HTML explanation: condition ratings, soil benefits, missing checks, and questions for an agriculturist. Simple collapses them again. Individual **Show why** controls still work, and changing language, season, or priority preserves the detail mode. Excluded crops retain their exclusion reason without receiving scores. This feature uses the existing sample adapter and does not connect to the Python model.
