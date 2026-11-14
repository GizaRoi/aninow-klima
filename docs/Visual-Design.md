# Visual direction

The November 2026 visual refresh follows the user's [Eloqwnt agriculture reference on Dribbble](https://dribbble.com/shots/27615353-AI-Powered-Low-Pesticide-Agriculture-Website): a misty floating farm, sage/olive surroundings, white sans-serif typography, translucent panels with corner accents, and restrained lime highlights. AniNow retains its branding, field inputs, comparison semantics, source labels and session saves. No reference screenshot is included in the website.

The desktop navigation is horizontal. On mobile, the panels stack below the farm and navigation opens in a drawer. Hero copy and panels use CSS Grid with explicit gaps, so wrapped headings and browser zoom cannot move the field panel over the planting button. The page, hero overlay and glass panels use deeper forest-green tones. The climate sparkline plots all 30 archived daily maximum values in `power-sample.json`; its range and date are available to screen readers. The crop engine and fixtures are unchanged.

Supporting typography uses 16px descriptions, 14–15px navigation/form labels, and 12–13px captions and source notes across viewport sizes. Cards, forms and comparison layouts wrap or stack as needed to accommodate readable text; responsive styles no longer reduce helper copy to 6–10px.

## Hero artwork

- Saved asset: `apps/web/public/images/farm-diorama.png`.
- Created using the built-in imagegen tool. The artwork is illustrative and does not depict a measured farm or a validated pilot.
- Theme styles: `apps/web/app/reference-theme.css`.

Final generation prompt:

> Use case: stylized-concept. Asset type: wide website hero background, 1536x1024 landscape. Create a premium photorealistic 3D isometric miniature Philippine rice farm diorama floating in soft atmospheric mist. A square deep earth slab with visible dark soil cross-section, geometric patchwork plots of lush rice green, muted gold harvested rice, terracotta brown soil and small green rotation crops, narrow dividing paths, a few small trees at the rear edge. View from above at a 35 degree angle, diamond orientation. Main farm centered slightly right in the frame, occupies central 60% of image width and lower 70% of height, clear open misty space at the top and upper left for web typography. Background is a seamless muted sage gray olive atmospheric studio backdrop, pale soft mist around the slab, soft directional sunlight, delicate realistic plant texture, calm cinematic agricultural technology art direction. Sophisticated restrained natural colors: forest green #223024, olive #626659, mist #acaea1, gold #948e70, soil #4d321f. This is background artwork only. No text, no typography, no logos, no UI, no charts, no framing border, no watermarks. Detailed architectural miniature realism, not cartoon.
