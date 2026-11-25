from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from skybot.sky import SkySettings, _night_window, moon_info_at
import pytest

def test_full_moon_is_almost_fully_illuminated() -> None:
    when = datetime(2024, 4, 23, 23, 49, tzinfo = timezone.utc)
    result = moon_info_at(when)

    assert result.illumination_percent == pytest.approx(100., abs=1.)
    assert result.phase == 'Luna piena'

def test_moon_calculation_requires_a_timezone() -> None:
    when = datetime(2024, 4, 23, 23, 49)

    with pytest.raises(ValueError, match = 'when must include a timezone'):
        moon_info_at(when)

def test_night_window_after_midnight_starts_the_previous_evening() -> None:
    zone = ZoneInfo("Europe/Rome")
    when = datetime(2026, 11, 25, 1, 0, tzinfo=zone)
    settings = SkySettings(
        bodies=(),
        minimum_altitude_deg=10.0,
        sun_altitude_threshold_deg=-6.0,
        time_window_start_hour=18,
        time_window_end_hour=6,
        time_step_minutes=5,
    )

    start, end = _night_window(when, "Europe/Rome", settings)

    assert start == datetime(2026, 11, 24, 18, 0, tzinfo=zone)
    assert end == datetime(2026, 11, 25, 6, 0, tzinfo=zone)