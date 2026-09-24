"""Deterministic calendar and holiday features for Sweden SE3 load forecasting.

Features:
- hour_of_day: int in [0, 23]
- day_of_week: int in [0, 6] (Monday=0, Sunday=6)
- day_of_month: int in [1, 31]
- month: int in [1, 12]
- is_weekend: int in {0, 1}
- is_public_holiday: int in {0, 1}

is_public_holiday represents Swedish public holidays plus explicitly included de facto reduced-activity days.
"""

from __future__ import annotations
import datetime
from typing import Set
import pandas as pd


def get_easter_sunday(year: int) -> datetime.date:
    """Calculate Easter Sunday for a given Gregorian year using Butcher's algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(year, month, day)


def get_swedish_public_and_de_facto_holidays(year: int) -> Set[datetime.date]:
    """Return all statutory Swedish public holidays plus de facto reduced-activity days.
    
    Statutory holidays under Lag (1989:1070) om allmänna helgdagar:
    1. Fixed:
       - Jan 1: Nyårsdagen (New Year's Day)
       - Jan 6: Trettondedag jul (Epiphany)
       - May 1: Första maj (Labour Day)
       - Jun 6: Sveriges nationaldag (National Day)
       - Dec 25: Juldagen (Christmas Day)
       - Dec 26: Annandag jul (Boxing Day)
    2. Easter-based:
       - Good Friday (Långfredagen, Easter - 2 days)
       - Easter Sunday (Påskdagen)
       - Easter Monday (Annandag påsk, Easter + 1 day)
       - Ascension Day (Kristi himmelsfärdsdag, Easter + 39 days)
       - Whit Sunday (Pingstdagen, Easter + 49 days)
    3. Weekday-bound:
       - Midsummer Day (Midsommardagen, Saturday between June 20 and June 26)
       - All Saints' Day (Alla helgons dag, Saturday between October 31 and November 6)
       
    De facto reduced-activity days (treated on par with red days in Swedish labor practice and grid demand):
       - Midsummer Eve (Midsommarafton, Friday preceding Midsummer Day)
       - Christmas Eve (Julafton, Dec 24)
       - New Year's Eve (Nyårsafton, Dec 31)
    """
    easter = get_easter_sunday(year)
    holidays = {
        # Fixed statutory
        datetime.date(year, 1, 1),
        datetime.date(year, 1, 6),
        datetime.date(year, 5, 1),
        datetime.date(year, 6, 6),
        datetime.date(year, 12, 25),
        datetime.date(year, 12, 26),
        # Easter-based statutory
        easter - datetime.timedelta(days=2),
        easter,
        easter + datetime.timedelta(days=1),
        easter + datetime.timedelta(days=39),
        easter + datetime.timedelta(days=49),
        # De facto reduced-activity days
        datetime.date(year, 12, 24),
        datetime.date(year, 12, 31),
    }

    # Midsummer Day: Saturday between June 20 and June 26
    # Midsummer Eve: Friday before Midsummer Day
    for day in range(20, 27):
        d = datetime.date(year, 6, day)
        if d.weekday() == 5:  # Saturday
            holidays.add(d)
            holidays.add(d - datetime.timedelta(days=1))  # Friday
            break

    # All Saints' Day: Saturday between Oct 31 and Nov 6
    found_all_saints = False
    if datetime.date(year, 10, 31).weekday() == 5:
        holidays.add(datetime.date(year, 10, 31))
        found_all_saints = True
    if not found_all_saints:
        for day in range(1, 7):
            d = datetime.date(year, 11, day)
            if d.weekday() == 5:
                holidays.add(d)
                break

    return holidays


def compute_target_calendar_features(target_timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute deterministic calendar features evaluated for the target timestamp T = t + h.
    
    Features computed:
    - hour_of_day: int in [0, 23]
    - day_of_week: int in [0, 6]
    - day_of_month: int in [1, 31]
    - month: int in [1, 12]
    - is_weekend: int in {0, 1}
    - is_public_holiday: int in {0, 1}
    
    Note: is_public_holiday represents Swedish public holidays plus explicitly
    included de facto reduced-activity days.
    """
    years = target_timestamps.year.unique()
    all_holidays: Set[datetime.date] = set()
    for y in years:
        all_holidays.update(get_swedish_public_and_de_facto_holidays(int(y)))

    df = pd.DataFrame(index=target_timestamps)
    df["hour_of_day"] = target_timestamps.hour.astype(int)
    df["day_of_week"] = target_timestamps.dayofweek.astype(int)
    df["day_of_month"] = target_timestamps.day.astype(int)
    df["month"] = target_timestamps.month.astype(int)
    df["is_weekend"] = (target_timestamps.dayofweek >= 5).astype(int)
    df["is_public_holiday"] = [
        1 if ts.date() in all_holidays else 0 for ts in target_timestamps
    ]
    return df
