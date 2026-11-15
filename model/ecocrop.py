"""FAO EcoCrop sheet snapshots, explicit profile matches, and FAO-56 water data.

Snapshots retrieved 2026-11-15 from the URLs below. Original table order is
optimal min/max, absolute min/max; the scoring model expects absolute/optimal.
No species is inferred from a genus or a similar common name.
"""
from html import unescape
from pathlib import Path
import re

SOURCES = Path(__file__).resolve().parent / 'sources' / 'ecocrop'
URL = 'https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id='
FAO56 = 'https://www.fao.org/4/x0490e/x0490e0b.htm'
# Explicit joins; these never change the supplied CSV's existing_crop_id.
MATCHES = {
    'FGV_MUSTARD_CHINESE': (548, 'Brassica juncea', 'species'),
    'FGV_KANGKONG_ONCE_OVER': (1264, 'Ipomoea aquatica', 'species; aquatic versus upland production is provisional'),
    'FGV_PECHAY_DIRECT': (3878, 'Brassica rapa Pak Choi', 'Pak Choi / chinensis crop group'),
    'FGV_KAILAAN': (3867, 'Brassica oleracea var. acephala', 'EcoCrop cropView 3867 explicitly lists B. alboglabra; broad kale group, provisional'),
    'FGV_CUCUMBER_DEBUT': (817, 'Cucumis sativus', 'species'),
    'FGV_RADISH_SNOW_WHITE_45': (1839, 'Raphanus sativus', 'Chinese/daikon radish sheet; named cultivar not validated'),
    'FGV_BUSH_SITAO_SUMILANG': (2153, 'Vigna unguiculata', 'species; bush profile retained separately'),
    'FGV_SNAPBEAN_MAYABONG': (1668, 'Phaseolus vulgaris', 'species'),
    'FGV_POLE_SITAW_MONTENEGRO': (10834, 'Vigna unguiculata ssp. sesquipedalis', 'subspecies; pole profile retained separately'),
    'FGV_AMPALAYA_GREEN_COMET': (7795, 'Momordica charantia', 'species'),
    'FGV_ALUGBATI_CUTTINGS': (504, 'Basella alba', 'species; cutting timeline retained'),
    'FGV_PATOLA_TAGALOG': (1373, 'Luffa acutangula', 'species'),
    'FGV_UPO_EXCELLENTE': (1315, 'Lagenaria siceraria', 'species'),
    'FGV_CHINESECABBAGE_GREEN_CHALLENGER': (547, 'Brassica chinensis', 'EcoCrop synonyms include B. pekinensis; broad Chinese cabbage group, provisional'),
    'FGV_GARDENPEA_EDIBLE_PODS': (1721, 'Pisum sativum', 'species; edible-pod timing retained'),
    'FGV_OKRA_TARLAC': (289, 'Abelmoschus esculentus', 'species'),
    'FGV_MUNGBEAN_ROTATION': (2150, 'Vigna radiata', 'species; dry pulse profile'),
    'FGV_SWEETCORN_SUGAR_KING': (10981, 'Zea mays ssp. saccharata', 'sweet corn subspecies; not grain maize'),
    'FGV_CAULIFLOWER_WHITE_CORAL': (553, 'Brassica oleracea var. botrytis', 'crop variety'),
    'FGV_CABBAGE_ORIENTAL_BALL': (554, 'Brassica oleracea var. capitata', 'crop variety'),
    'FGV_EGGPLANT_GWAPITO': (1965, 'Solanum melongena', 'species'),
}
UNMATCHED = {
    'FGV_AMARANTH_GREEN': 'Amaranthus spp. does not identify a species; cannot assign the A. tricolor sheet.',
    'FGV_LETTUCE_GREEN_SPAN': 'Available EcoCrop 1313 is head lettuce (var. capitata), not verified leaf lettuce.',
    'FGV_SALUYOT_DIRECT': 'No verified Corchorus olitorius sheet found; C. capsularis is a different species.',
}


def text(html):
    return ' '.join(unescape(re.sub('<[^>]+>', ' ', html)).split())


def read_sheet(sheet_id, expected):
    html = (SOURCES / f'{sheet_id}.html').read_text(encoding='utf-8-sig')
    title = re.search(r'<h2[^>]*>(.*?)</h2>', html, re.S)
    if not title or text(title[1]) != expected:
        raise ValueError(f'EcoCrop {sheet_id}: unexpected taxon or invalid snapshot')
    rows = []
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.S):
        rows.append([text(c) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.S)])
    def values(label, n):
        for row in rows:
            if label in row:
                i = row.index(label)
                cells = row[i + 1:i + 1 + n]
                if len(cells) == n:
                    return cells
        raise ValueError(f'EcoCrop {sheet_id}: missing {label}')
    def limits(label):
        raw = values(label, 4)
        try:
            a, b, c, d = map(float, raw)
        except ValueError:
            return None
        if not c <= a <= b <= d:
            raise ValueError(f'EcoCrop {sheet_id}: unordered {label} limits')
        return c, a, b, d
    tex = values('Soil texture', 2)
    return dict(sheet=sheet_id, temp=limits('Temperat. requir.'),
                ph=limits('Soil PH'), rain=limits('Rainfall (annual)'),
                tex_opt=[v.strip() for v in tex[0].split(',') if v.strip()],
                tex_abs=[v.strip() for v in tex[1].split(',') if v.strip()],
                drainage=values('Soil drainage', 2)[1],
                ecocrop_cycle=values('Crop cycle', 2), source_url=URL + str(sheet_id))


# (ini, mid, end), stage days, named row and region in FAO-56 Tables 12/11.
# Stage proportions are scaled to the explicitly planned crop occupancy by the
# existing model, not substituted for local first-harvest dates.
WATER = {
    'FGV_CUCUMBER_DEBUT': ((.6, 1., .75), (20, 30, 40, 15), 'Cucumber fresh market; June/Aug, Arid Region'),
    'FGV_RADISH_SNOW_WHITE_45': ((.7, .9, .85), (5, 10, 15, 5), 'Radish; Mar/Apr, Mediterranean/Europe; initial Kc from small vegetables group'),
    'FGV_GARDENPEA_EDIBLE_PODS': ((.5, 1.15, 1.1), (15, 25, 35, 15), 'Peas fresh; May, Europe'),
    'FGV_SWEETCORN_SUGAR_KING': ((.3, 1.15, 1.05), (20, 20, 30, 10), 'Maize sweet; March, Philippines; initial Kc from cereals group'),
    'FGV_CAULIFLOWER_WHITE_CORAL': ((.7, 1.05, .95), (35, 50, 40, 15), 'Cauliflower; Sept, California desert; initial Kc from small vegetables group'),
}
INHERIT_WATER = {'FGV_EGGPLANT_GWAPITO': 'eggplant', 'FGV_MUNGBEAN_ROTATION': 'mungbean',
                 'FGV_BUSH_SITAO_SUMILANG': 'sitaw', 'FGV_POLE_SITAW_MONTENEGRO': 'sitaw',
                 'FGV_SNAPBEAN_MAYABONG': 'snapbean', 'FGV_CABBAGE_ORIENTAL_BALL': 'cabbage'}


def build_crops(profiles, legacy):
    """Adapt timing profiles to the existing scorer without overwriting legacy crops."""
    result = {}
    for p in profiles:
        match = MATCHES.get(p['record_id'])
        sheet = read_sheet(*match[:2]) if match else dict(
            sheet=None, temp=None, ph=None, rain=None, tex_opt=[], tex_abs=[], drainage='unknown')
        plan = p['schedule']
        picking = plan['additional_picking_days']
        # With missing picking plans, show first-harvest exposure only, never
        # count it as a complete rotation or a historical suitability pass.
        horizon = p['provenance']['start_to_first_harvest_days_max'] + (picking or 0)
        gaps = list(plan['missing'])
        if not match:
            gaps.append(UNMATCHED[p['record_id']])
        if match and 'provisional' in match[2]:
            gaps.append(match[2])
        kc, kc_source = None, 'No verified FAO-56 coefficient and stage combination for this profile.'
        if p['record_id'] in INHERIT_WATER:
            base = legacy[INHERIT_WATER[p['record_id']]]
            kc, kc_source = base['kc'], base['kc_source']
        if p['record_id'] in WATER:
            coefficients, stages, label = WATER[p['record_id']]
            kc = dict(ini=coefficients[0], mid=coefficients[1], end=coefficients[2],
                      stages=list(stages), percolation=0.)
            kc_source = f'FAO-56 Tables 12 and 11, {label}. {FAO56}'
        if kc is None:
            gaps.append('water_demand_not_evaluated')
        if not sheet['temp'] or not sheet['ph']:
            gaps.append('missing_ecocrop_numeric_limits')
        if not sheet['tex_abs']:
            gaps.append('missing_ecocrop_texture')
        result[p['record_id']] = dict(sheet, local_name=p['provenance']['local_name'],
            scientific_name=p['provenance']['scientific_name'], limits='ecocrop', guide_id=None,
            limits_source=(f"FAO EcoCrop {match[0]}: {match[1]}; {match[2]}. {URL}{match[0]}"
                           if match else UNMATCHED[p['record_id']]),
            cycle_min=horizon, cycle_max=horizon,
            cycle_source='CSV conservative first-harvest upper endpoint + selected/sourced picking days; '
                         'not the general EcoCrop cycle. ' + p['provenance']['timing_source_url'],
            legume=p['record_id'] in {'FGV_BUSH_SITAO_SUMILANG', 'FGV_POLE_SITAW_MONTENEGRO',
                                    'FGV_SNAPBEAN_MAYABONG', 'FGV_GARDENPEA_EDIBLE_PODS', 'FGV_MUNGBEAN_ROTATION'},
            kc=kc, kc_source=kc_source, timing_profile=True, schedule=plan,
            critical_gaps=gaps, full_schedule=not plan['missing'],
            forced_exclusions=p['failures'])
    return result
