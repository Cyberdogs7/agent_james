import pytest
from datetime import datetime
from backend.time_utils import format_datetime

def test_format_datetime_12h_am():
    dt = datetime(2023, 10, 27, 8, 30)
    result = format_datetime(dt, time_format="12h")
    assert result == "Friday, October 27, 2023 at 08:30 AM"

def test_format_datetime_12h_pm():
    dt = datetime(2023, 10, 27, 20, 45)
    result = format_datetime(dt, time_format="12h")
    assert result == "Friday, October 27, 2023 at 08:45 PM"

def test_format_datetime_12h_noon():
    dt = datetime(2023, 10, 27, 12, 0)
    result = format_datetime(dt, time_format="12h")
    assert result == "Friday, October 27, 2023 at 12:00 PM"

def test_format_datetime_12h_midnight():
    dt = datetime(2023, 10, 27, 0, 0)
    result = format_datetime(dt, time_format="12h")
    assert result == "Friday, October 27, 2023 at 12:00 AM"

def test_format_datetime_24h():
    dt = datetime(2023, 10, 27, 20, 45)
    result = format_datetime(dt, time_format="24h")
    assert result == "Friday, October 27, 2023 at 20:45"

def test_format_datetime_default_format():
    dt = datetime(2023, 10, 27, 8, 30)
    result = format_datetime(dt)
    assert result == "Friday, October 27, 2023 at 08:30 AM"

def test_format_datetime_leap_year():
    dt = datetime(2024, 2, 29, 15, 0)
    result = format_datetime(dt, time_format="24h")
    assert result == "Thursday, February 29, 2024 at 15:00"

def test_format_datetime_edge_of_year():
    dt = datetime(2023, 12, 31, 23, 59)
    result = format_datetime(dt, time_format="12h")
    assert result == "Sunday, December 31, 2023 at 11:59 PM"
