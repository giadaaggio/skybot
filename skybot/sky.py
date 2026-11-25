from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import math

import astropy.units as u
from astropy.coordinates import GeocentricTrueEcliptic, get_body, get_sun
from astropy.time import Time
from astropy.utils import iers
from astropy.coordinates import solar_system_ephemeris

iers.conf.auto_download = False

# constants
MOON_PHASES = (
    'Luna nuova', 
    'Falce crescente',
    'Primo quarto',
    'Gibbosa crescente',
    'Luna piena',
    'Gibbosa calante',
    'Ultimo quarto',
    'Falce calante',
)

COMPASS_DIRECTIONS = (
    'Nord',
    'Nord-est',
    'Est',
    'Sud-est',
    'Sud',
    'Sud-ovest',
    'Ovest',
    'Nord-ovest',
)
COMPASS_SECTOR_WIDTH_DEG = 360. / len(COMPASS_DIRECTIONS)

@dataclass(frozen=True)
class MoonInfo:
    phase: str
    illumination_percent: float

@dataclass(frozen=True)
class BodySpec:
    name: str
    display_name: str

@dataclass(frozen=True)
class SkySettings:
    bodies: tuple[BodySpec, ...]
    minimum_altitude_deg: float
    sun_altitude_threshold_deg: float
    time_window_start_hour: int
    time_window_end_hour: int
    time_step_minutes: int

@dataclass(frozen=True)
class VisibilityWindow:
    start: datetime
    end: datetime
    peak_altitude_deg: float
    peak_direction: str

@dataclass(frozen=True)
class VisibleBody:
    name: str
    display_name: str
    windows: tuple[VisibilityWindow, ...]

@dataclass(frozen=True)
class SkyReport:
    moon: MoonInfo
    bodies: tuple[VisibleBody, ...]


# what does 'tonight' means?
def _night_window(
        when: datetime,
        timezone_name: str,
        settings: SkySettings,
) -> tuple[datetime, datetime]:
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError('when must include a timezone')

    zone = ZoneInfo(timezone_name)
    local_when = when.astimezone(zone)
    wraps_midnight = (
        settings.time_window_end_hour <= settings.time_window_start_hour
    )
    start_date = local_when.date()

    if wraps_midnight and local_when.hour < settings.time_window_end_hour:
        start_date -= timedelta(days=1)
    elif not wraps_midnight and local_when.hour >= settings.time_window_end_hour:
        start_date += timedelta(days=1)

    end_date = start_date + timedelta(days=1 if wraps_midnight else 0)
    start = datetime.combine(
        start_date,
        time(hour=settings.time_window_start_hour),
        tzinfo = zone,
    )
    end = datetime.combine(
        end_date,
        time(hour=settings.time_window_end_hour),
        tzinfo=zone,
    )

    return start, end


# map an azimuth to an Italian compass direction
def _compass_direction(azimuth_deg: float) -> str:
    half_sector = COMPASS_SECTOR_WIDTH_DEG / 2.
    normalized_azimuth = azimuth_deg % 360.
    index = int((normalized_azimuth + half_sector) // COMPASS_SECTOR_WIDTH_DEG)
    return COMPASS_DIRECTIONS[index % len(COMPASS_DIRECTIONS)]


# group consecutive vibile samples into visibilty windows
def _visibility_windows(
        sample_times: tuple[datetime, ...],
        body_altitudes_deg: list[float],
        body_azimuths_deg: list[float],
        sun_altitudes_deg: list[float],
        settings: SkySettings,
) -> tuple[VisibilityWindow, ...]: 
    sample_count = len(sample_times)
    if not sample_times or any(
        len(values) != sample_count 
        for values in (body_altitudes_deg, body_azimuths_deg, sun_altitudes_deg)
    ): 
        raise ValueError('sample times and altitude arrays must have matching lengths')

    visible = [
        body_altitude > settings.minimum_altitude_deg
        and sun_altitude < settings.sun_altitude_threshold_deg
        for body_altitude, sun_altitude in zip(
            body_altitudes_deg, sun_altitudes_deg, strict = True
        )
    ]

    windows: list[VisibilityWindow] = []
    index = 0 
    while index < sample_count:
        if not visible[index]: 
            index += 1
            continue

        first_visible = index
        while index + 1 < sample_count and visible[index + 1]:
            index += 1
        last_visible = index

        peak_index = max(
            range(first_visible, last_visible + 1), 
            key = lambda sample_index: body_altitudes_deg[sample_index]
        )
        end_index = min(last_visible + 1, sample_count - 1)
        windows.append(
            VisibilityWindow(
                start = sample_times[first_visible],
                end = sample_times[end_index],
                peak_altitude_deg = body_altitudes_deg[peak_index],
                peak_direction = _compass_direction(body_azimuths_deg[peak_index]),
            )
        )
        index += 1

    return tuple(windows)


# calculate Moon's phase and illuminated percentage
def moon_info_at(when: datetime) -> MoonInfo:
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError('when must include a timezone')

    observation_time = Time(when)

    with solar_system_ephemeris.set('builtin'):
        moon = get_body('moon', observation_time)
        sun = get_sun(observation_time)

    separation_rad = sun.separation(moon).to_value(u.rad)
    illumination = (1. - math.cos(separation_rad)) / 2.

    ecliptic_frame = GeocentricTrueEcliptic(equinox = observation_time)
    moon_longitude = moon.transform_to(ecliptic_frame).lon.to_value(u.deg)
    sun_longitude = sun.transform_to(ecliptic_frame).lon.to_value(u.deg)
    phase_position = (moon_longitude - sun_longitude) % 360.
    phase_index = int((phase_position + 22.5) // 45.) % len(MOON_PHASES)

    return MoonInfo(
        phase = MOON_PHASES[phase_index],
        illumination_percent = illumination * 100.
    )

