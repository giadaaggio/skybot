from dataclasses import dataclass
from datetime import datetime
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

