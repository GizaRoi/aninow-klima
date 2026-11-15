"""Source-preserving timing profiles and conservative rotation scheduling.

No network or inferred crop thresholds. Dates use [start, finish): finishing
on the next rice planting date is allowed; no work may extend beyond it.
"""
import calendar
import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
TIMING_FILE = HERE / 'fast_growing_vegetables_ph_under_90_days.csv'
NUMERIC = ('reported_harvest_min', 'reported_harvest_max', 'nursery_days_min',
           'nursery_days_max', 'start_to_first_harvest_days_min',
           'start_to_first_harvest_days_max', 'reported_harvest_period_days',
           'full_crop_cycle_days')
SINGLE = {'single_head_harvest', 'single_curd_harvest', 'fresh_ear_harvest',
          'single_root_harvest', 'single_whole_plant_harvest', 'single_uprooted_harvest'}


def add_months(day: date, months: int = 3) -> date:
    """Calendar months, clamped to the last day of the destination month."""
    m = day.year * 12 + day.month - 1 + months
    y, m = divmod(m, 12)
    return date(y, m + 1, min(day.day, calendar.monthrange(y, m + 1)[1]))


@dataclass(frozen=True)
class TimingProfile:
    record_id: str
    crop_id: str
    existing_crop_id: str | None
    first_min: int | None
    first_max: int | None
    under_90: bool
    source: dict


def load_profiles(path=TIMING_FILE) -> list[TimingProfile]:
    out, seen = [], set()
    with open(path, encoding='utf-8-sig', newline='') as stream:
        for original in csv.DictReader(stream):
            row = dict(original)
            key = row['record_id'].strip()
            if not key or key in seen:
                raise ValueError(f'Duplicate or blank timing record_id: {key}')
            seen.add(key)
            for name in NUMERIC:
                raw = row[name].strip()
                row[name] = int(raw) if raw else None
                if row[name] is not None and row[name] < 0:
                    raise ValueError(f'{key}: negative {name}')
            flag = row['under_90_days_first_harvest'].strip().lower()
            if flag not in ('true', 'false'):
                raise ValueError(f'{key}: invalid boolean {flag!r}')
            row['under_90_days_first_harvest'] = flag == 'true'
            lo, hi = (row[f'start_to_first_harvest_days_{end}'] for end in ('min', 'max'))
            if lo is not None and hi is not None and lo > hi:
                raise ValueError(f'{key}: reversed first-harvest range')
            if row['reported_harvest_basis'] == 'days_after_transplanting':
                for end in ('min', 'max'):
                    nursery = row[f'nursery_days_{end}']
                    reported = row[f'reported_harvest_{end}']
                    if nursery is None or reported is None:
                        lo = hi = None
                        break
                    if row[f'start_to_first_harvest_days_{end}'] != nursery + reported:
                        raise ValueError(f'{key}: inconsistent nursery conversion')
            # Recompute the strict screen; the source flag remains in provenance.
            out.append(TimingProfile(key, row['crop_id'], row['existing_crop_id'] or None,
                                     lo, hi, hi is not None and hi < 90, row))
    return out


def load_requirements():
    with open(HERE / 'crop_requirements_ph.csv', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    keys = [r['crop_id'] for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate requirement crop_id; refusing a multiplying join')
    return {r['crop_id']: r for r in rows}


def weighted_index(components, weights):
    if any(w < 0 for w in weights.values()):
        raise ValueError('Weights cannot be negative')
    total = sum(weights.values())
    have = {k: w for k, w in weights.items() if w > 0 and components.get(k) is not None}
    evaluated = sum(have.values())
    return {'index': (sum(w * components[k] for k, w in have.items()) / evaluated
                      if evaluated else None),
            'coverage': evaluated / total if total else None,
            'skipped': [k for k in weights if components.get(k) is None]}


def schedule(profile, harvest, next_rice, preparation=None, picking=None, clearance=None):
    """All propagation starts after the fixed fallow; nursery is already counted.

    Missing planning assumptions remain missing. No implicit nursery overlap.
    """
    if next_rice <= harvest:
        raise ValueError('Next rice planting must be after harvest')
    for value in (preparation, picking, clearance):
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ValueError('Planning days must be nonnegative whole numbers')
    start = add_months(harvest)
    row = profile.source
    if picking is None and row['harvest_pattern'] in SINGLE:
        picking = 0
    if picking is None:
        picking = row['reported_harvest_period_days']
    missing = []
    if preparation is None:
        missing.append('preparation_days')
    if clearance is None:
        missing.append('clearing_and_rice_preparation_days')
    if picking is None:
        missing.append('additional_picking_days_or_explicit_termination_plan')
    if profile.first_max is None:
        missing.append('first_harvest_duration')
    first = (start + timedelta(days=preparation + profile.first_max)
             if preparation is not None and profile.first_max is not None else None)
    finish = first + timedelta(days=picking + clearance) if first and not missing else None
    first_fit = ('fits' if first <= next_rice else 'does_not_fit') if first else 'unresolved'
    full = ('fits' if finish <= next_rice else 'does_not_fit') if finish else 'unresolved'
    # A known failure is binding even when another assumption is missing.
    if start >= next_rice or first_fit == 'does_not_fit':
        full = first_fit = 'does_not_fit'
    return dict(fallow_months=3, fallow_start=harvest.isoformat(), fallow_end=start.isoformat(),
                window_days=(next_rice - harvest).days,
                available_after_fallow_days=max(0, (next_rice - start).days),
                cycle_start_event=row['cycle_start_event'], earliest_cycle_start=start.isoformat(),
                preparation_days=preparation, additional_picking_days=picking,
                clearing_and_rice_preparation_days=clearance,
                first_harvest_latest=first.isoformat() if first else None,
                field_clear_date=finish.isoformat() if finish else None,
                first_harvest_fit=first_fit, full_window_fit=full, missing=missing,
                nursery_days=[row['nursery_days_min'], row['nursery_days_max']],
                nursery_overlap=False,
                picking_plan='farmer-selected; may terminate early' if picking is not None else 'unresolved')


def assess(profile, plan, requirement, soil_ph=None, temperature=None, drainage='unknown'):
    """DA preferred ranges are screens, never inferred lethal response curves.

    Named cultivars and distinct production routes retain provisional status.
    Water lacks a profile-specific coefficient, so is deliberately unevaluated.
    """
    components, evidence, gaps, failures = {}, [], [], []
    if plan['full_window_fit'] == 'does_not_fit':
        failures.append('schedule_overrun')
    if not profile.under_90:
        failures.append('not_strictly_under_90_days_to_first_harvest')
    if plan['full_window_fit'] == 'unresolved':
        gaps.extend(plan['missing'])
    gaps.append('plot_soil_test_or_current_sample_verification')
    if requirement is None:
        gaps.append('no_joined_requirement_profile')
    else:
        for key, value, low, high, unit in (
            ('ph', soil_ph, 'soil_ph_min', 'soil_ph_max', 'pH'),
            ('temperature', temperature, 'growth_air_temp_min_c', 'growth_air_temp_max_c', 'deg C')):
            lo, hi = requirement.get(low), requirement.get(high)
            result = float(float(lo) <= value <= float(hi)) if value is not None and lo and hi else None
            components[key] = result
            evidence.append(dict(condition=key, input=value, min=lo or None, max=hi or None,
                                 units=unit, rule='published preferred range screen', result=result,
                                 source=requirement['source_url'],
                                 scope='crop-level context; cultivar compatibility unverified'))
        gaps.append('cultivar_and_production_scope_not_validated')
    if drainage == 'unknown':
        gaps.append('plot_drainage_unknown')
    if drainage == 'poorly_drained' and requirement and 'drain' in requirement['water_and_drainage'].lower():
        failures.append('requires_drained_soil')
    components.update(water=None, texture=None)
    gaps.extend(['profile_specific_water_requirements', 'profile_specific_texture_rule'])
    index = weighted_index(components, dict(ph=1, temperature=1, water=1, texture=1))
    return dict(record_id=profile.record_id, crop_id=profile.crop_id,
                under_90_days_first_harvest=profile.under_90, provenance=profile.source,
                schedule=plan, status='excluded' if failures else 'provisional',
                failures=failures, critical_gaps=gaps, evidence=evidence,
                suitability_context=index,
                note='Context index is not validated suitability or a harvest probability.')


def compare(harvest, next_rice, preparation=None, picking=None, clearance=None,
            soil_ph=None, temperature=None, drainage='unknown'):
    requirements = load_requirements()
    return [assess(p, schedule(p, harvest, next_rice, preparation, picking, clearance),
                   requirements.get(p.existing_crop_id), soil_ph, temperature, drainage)
            for p in load_profiles()]
