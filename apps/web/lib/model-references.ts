import type { ModelCrop } from './model';

/** Bibliographic metadata verified against the publications, not CSV upload dates. */
export type ModelReference = {
  id: string;
  authors: string;
  date: string;
  title: string;
  italicTitle: boolean;
  description?: string;
  series?: string;
  publisher?: string;
  website?: string;
  journal?: { title: string; volume: string; article: string };
  retrieved?: string;
  url: string;
};

const fao = 'Food and Agriculture Organization of the United Nations';
const da = 'Department of Agriculture, Regional Field Office No. 02';
const daBase = 'https://cagayanvalley.da.gov.ph/wp-content/uploads/2018/02/';

export const modelReferences: Record<string, ModelReference> = {
  fao56: {
    id: 'fao56', authors: 'Allen, R. G., Pereira, L. S., Raes, D., & Smith, M.', date: '1998',
    title: 'Crop evapotranspiration: Guidelines for computing crop water requirements', italicTitle: true,
    series: 'FAO Irrigation and Drainage Paper No. 56', publisher: fao,
    url: 'https://www.fao.org/4/x0490e/x0490e00.htm',
  },
  irrigationManual3: {
    id: 'irrigationManual3', authors: 'Brouwer, C., & Heibloem, M.', date: '1986',
    title: 'Irrigation water management: Irrigation water needs', italicTitle: true,
    series: 'Training Manual No. 3', publisher: fao,
    url: 'https://www.fao.org/4/s2022e/s2022e00.htm',
  },
  riceVarieties: {
    id: 'riceVarieties', authors: 'Philippine Rice Research Institute', date: 'n.d.',
    title: 'Rice varieties', italicTitle: true, website: 'Pinoy Rice Knowledge Bank',
    url: 'https://www.pinoyrice.com/rice-varieties/',
  },
  riceSeedChoice: {
    id: 'riceSeedChoice', authors: 'Glover, D., Kim, S. K., & Stone, G. D.', date: '2020',
    title: 'Golden Rice and technology adoption theory: A study of seed choice dynamics among rice growers in the Philippines',
    italicTitle: false, journal: { title: 'Technology in Society', volume: '60', article: '101227' },
    url: 'https://doi.org/10.1016/j.techsoc.2019.101227',
  },
  lettuceBicol: {
    id: 'lettuceBicol', authors: 'Department of Agriculture, Regional Field Office No. 5', date: '2021',
    title: 'Guiya sa gulay', italicTitle: true,
    url: 'https://bicol.da.gov.ph/wp-content/uploads/2023/04/Guiya-sa-Gulay-2021.pdf',
  },
  urbanGardening: {
    id: 'urbanGardening', authors: 'Agricultural Training Institute, Cordillera Administrative Region', date: 'n.d.',
    title: 'A guide to urban/home gardening', italicTitle: true,
    url: 'https://ati2.da.gov.ph/ati-car/content/sites/default/files/2022-12/urban_agriculture_for_upland.pdf',
  },
};

// A card is a separate reference list. Its DA author/year identifies one guide,
// so no same-author/same-year letter disambiguation is needed within a card.
const guides: Record<string, { title: string; file: string; date: string }> = {
  PHV_EGGPLANT: { title: 'Eggplant production guide', file: 'Eggplant.pdf', date: '2017' },
  PHV_TOMATO: { title: 'Tomato production guide', file: 'Tomato.pdf', date: '2017' },
  PHV_SQUASH: { title: 'Squash production guide', file: 'Squash.pdf', date: '2017' },
  PHV_SITAW: { title: 'Sitao production guide', file: 'Sitao.pdf', date: '2017' },
  PHV_SNAPBEAN: { title: 'Snap beans production guide', file: 'Snap-Beans-Production-Guide.pdf', date: '2017' },
  PHV_CABBAGE: { title: 'Cabbage production guide', file: 'Cabbage.pdf', date: '2017' },
  PHV_POTATO: { title: 'White potato production guide', file: 'White-Potato-Production-Guide.pdf', date: '2017' },
  PHV_CARROT: { title: 'Carrot production guide', file: 'Carrot-Prod-Guide.pdf', date: '2017' },
  PHV_GARDENPEA: { title: 'Sweet pea production guide', file: 'Sweet-Pea-Production-Guide.pdf', date: '2017' },
};

// Scientific names and sheet identifiers are pinned to the model's actual sources.
// This includes the six DA-screened crops' EcoCrop soil-texture sheets.
const ecoCropNames: Record<string, string> = {
  '1574': 'Oryza sativa', '2150': 'Vigna radiata', '1965': 'Solanum melongena',
  '1379': 'Lycopersicon esculentum', '819': 'Cucurbita maxima',
  '10834': 'Vigna unguiculata ssp. sesquipedalis', '1668': 'Phaseolus vulgaris',
  '554': 'Brassica oleracea var. capitata', '1313': 'Lactuca sativa var. capitata',
  '1971': 'Solanum tuberosum', '2175': 'Zea mays', '10981': 'Zea mays ssp. saccharata',
  '2199': 'Arachis hypogaea', '1150': 'Glycine max', '1265': 'Ipomoea batatas',
  '1420': 'Manihot esculenta', '364': 'Allium cepa', '618': 'Capsicum annuum',
  '708': 'Citrullus lanatus', '815': 'Cucumis melo', '871': 'Daucus carota',
  '1937': 'Sesamum indicum', '1982': 'Sorghum bicolor var. sweet',
  '556': 'Brassica oleracea var. italica', '817': 'Cucumis sativus',
  '1839': 'Raphanus sativus', '1721': 'Pisum sativum',
  '553': 'Brassica oleracea var. botrytis', '2153': 'Vigna unguiculata',
};

for (const [id, name] of Object.entries(ecoCropNames)) {
  modelReferences[`ecocrop:${id}`] = {
    id: `ecocrop:${id}`, authors: fao, date: 'n.d.', title: name,
    italicTitle: true, description: `Data sheet ${id}`, website: 'EcoCrop',
    retrieved: 'November 15, 2026',
    url: `https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=${id}`,
  };
}
for (const [id, guide] of Object.entries(guides)) {
  modelReferences[id] = {
    id, authors: da, date: guide.date, title: guide.title, italicTitle: true,
    url: `${daBase}${guide.file}`,
  };
}

const guideBySheet: Record<string, string> = {
  '1965': 'PHV_EGGPLANT', '1379': 'PHV_TOMATO', '871': 'PHV_CARROT', '1721': 'PHV_GARDENPEA',
};

/** Identify only sources named by the response; keep unfamiliar metadata visible. */
export function referencesForCrop(
  result: Pick<ModelCrop, 'limits_source' | 'cycle_source'> & Partial<Pick<ModelCrop, 'guide_check'>>,
  waterSource: string,
): { references: ModelReference[]; unmatched: string[] } {
  const ids = new Set<string>();
  const unmatched = new Set<string>();
  const sheetIds = new Set<string>();
  function addGuide(id: string) {
    // These are the two specific providers of lettuce's scored pH and temperature.
    // The RFO02 lettuce leaflet is not substituted for either publication.
    if (id === 'PHV_LETTUCE') {
      ids.add('lettuceBicol'); ids.add('urbanGardening'); return true;
    }
    if (modelReferences[id]) { ids.add(id); return true; }
    return false;
  }

  for (const raw of [result.limits_source, result.cycle_source, waterSource]) {
    if (!raw.trim()) continue;
    let recognized = false;
    let unknownIdentifier = false;
    for (const match of raw.matchAll(/EcoCrop\s+sheet\s+(\d+)/gi)) {
      const id = match[1];
      sheetIds.add(id);
      if (modelReferences[`ecocrop:${id}`]) { ids.add(`ecocrop:${id}`); recognized = true; }
      else unknownIdentifier = true;
    }
    for (const match of raw.matchAll(/\bPHV_[A-Z]+\b/g)) {
      if (addGuide(match[0])) recognized = true;
      else unknownIdentifier = true;
    }
    if (/FAO[\s-]*56/i.test(raw)) { ids.add('fao56'); recognized = true; }
    if (/Training Manual (?:no\.?\s*)?3/i.test(raw)) { ids.add('irrigationManual3'); recognized = true; }
    if (/Pinoy Rice Knowledge Bank|PhilRice/i.test(raw)) { ids.add('riceVarieties'); recognized = true; }
    if (/Glover et al\.?\s*2020/i.test(raw)) { ids.add('riceSeedChoice'); recognized = true; }
    if (!recognized || unknownIdentifier) unmatched.add(raw);
  }

  // Global-limit crops can also return a Philippine temperature caution. Carrot
  // and garden pea explicitly identify that additional screen in limits_source.
  for (const sheet of sheetIds) {
    const guide = guideBySheet[sheet];
    if (guide && (result.guide_check || /DA crop guide/i.test(result.limits_source))) addGuide(guide);
  }

  return {
    references: [...ids].map(id => modelReferences[id]).sort((a, b) =>
      a.authors.localeCompare(b.authors, 'en') || a.date.localeCompare(b.date, 'en') || a.title.localeCompare(b.title, 'en')),
    unmatched: [...unmatched],
  };
}
