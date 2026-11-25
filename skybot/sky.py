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

