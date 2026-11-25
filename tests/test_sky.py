from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from skybot.sky import (SkySettings, _night_window, moon_info_at, _visibility_windows)
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


def test_visibility_windows_group_samples_and_find_peaks() -> None:
    sample_times = (
        datetime(2026, 11, 25, 18, 0, tzinfo=timezone.utc),
        datetime(2026, 11, 25, 18, 5, tzinfo=timezone.utc),
        datetime(2026, 11, 25, 18, 10, tzinfo=timezone.utc),
        datetime(2026, 11, 25, 18, 15, tzinfo=timezone.utc),
        datetime(2026, 11, 25, 18, 20, tzinfo=timezone.utc),
        datetime(2026, 11, 25, 18, 25, tzinfo=timezone.utc),
    )
    settings = SkySettings(
        bodies=(),
        minimum_altitude_deg=10.0,
        sun_altitude_threshold_deg=-6.0,
        time_window_start_hour=18,
        time_window_end_hour=6,
        time_step_minutes=5,
    )

    windows = _visibility_windows(
        sample_times=sample_times,
        body_altitudes_deg=[5.0, 12.0, 25.0, 11.0, 30.0, 4.0],
        body_azimuths_deg=[0.0, 45.0, 90.0, 135.0, 180.0, 270.0],
        sun_altitudes_deg=[-4.0, -7.0, -7.0, -4.0, -7.0, -7.0],
        settings=settings,
    )

    assert len(windows) == 2
    assert windows[0].start == sample_times[1]
    assert windows[0].end == sample_times[3]
    assert windows[0].peak_altitude_deg == 25.0
    assert windows[0].peak_direction == "Est"
    assert windows[1].start == sample_times[4]
    assert windows[1].end == sample_times[5]
    assert windows[1].peak_altitude_deg == 30.0
    assert windows[1].peak_direction == "Sud"