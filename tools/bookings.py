"""The demo practice's appointment book: three weeks of bookings from a given day.

A weekday has 20 bookings: 12 with Dr Thistlewood (USERID 1) and 8 with Dr Ravensworth (USERID 3), in 15-minute
slots 08:30-12:30 and 13:30-17:00. A Saturday has 4 or 5, 08:30-12:00, with one doctor, turn about. Sundays have none.

The patients are the practice's current ones. With 40 of them, half are booked each weekday and the other half the
next, so nobody is booked two weekdays running or twice in a day.

Everything is worked out from the calendar date alone, so a given day has the same bookings whenever the book is
made, and making it again changes nothing. Used by gen_base.py (the snapshot) and refresh_dates.py (every refresh).
"""
import datetime as dt
import random

DAYS = 21                               # today and the 20 days after it
SYN_APPT_LT = 2001                      # these bookings have APPOINTMENTS RECORDID below this
SLOT = 900                              # 15 minutes
WEEKDAY_SLOTS = [8 * 3600 + 1800 + i * SLOT for i in range(16)] + [13 * 3600 + 1800 + i * SLOT for i in range(14)]
SATURDAY_SLOTS = [8 * 3600 + 1800 + i * SLOT for i in range(14)]
DOCTORS = ((1, 12), (3, 8))             # (USERID, bookings each weekday)
RECEPTION = 6                           # booked by (Tessa Wyndham-Lowe)
REASONS = ['Review', 'Repeat prescription', 'Results', 'Blood pressure check', 'Skin check', 'Referral',
           'Care plan review', 'Immunisation', 'Follow-up', 'Medication review', 'Check-up']
CHILD_REASONS = ['Immunisation', 'Check-up', 'Follow-up', 'Review']
OLDER_REASONS = REASONS + ['Health assessment', 'Medication review']


def _weekday_number(d):
    """Weekdays since a fixed Monday, so the two halves of the patients alternate across weekends."""
    days = (d - dt.date(2001, 1, 1)).days
    return days // 7 * 5 + min(days % 7, 4)


def _reason(rng, age):
    return rng.choice(CHILD_REASONS if age < 16 else OLDER_REASONS if age >= 75 else REASONS)


def make_bookings(patients, start, days=DAYS):
    """Rows for dbo.APPOINTMENTS, RECORDID from 1. patients: [(INTERNALID, date of birth)], current patients only."""
    order = sorted(patients)
    random.Random('medui-demo-bookings').shuffle(order)
    rows = []
    for n in range(days):
        d = start + dt.timedelta(days=n)
        rng = random.Random(f'medui-demo-bookings {d.isoformat()}')
        if d.weekday() == 6:                                    # Sunday
            continue
        if d.weekday() == 5:                                    # Saturday morning, one doctor
            doctor = DOCTORS[d.isocalendar()[1] % 2][0]
            chosen = rng.sample(order, min(rng.choice((4, 5)), len(order)))
            plan = [(doctor, p, t) for p, t in zip(chosen, sorted(rng.sample(SATURDAY_SLOTS, len(chosen))))]
        else:
            pool = order[_weekday_number(d) % 2::2]
            rng.shuffle(pool)
            plan = []
            for doctor, count in DOCTORS:
                mine, pool = pool[:count], pool[count:]
                plan += [(doctor, p, t) for p, t in zip(mine, sorted(rng.sample(WEEKDAY_SLOTS, len(mine))))]
        for doctor, (pid, dob), t in plan:
            age = (d - dob).days / 365.25
            made = min(d - dt.timedelta(days=rng.randint(2, 21)), start)
            rows.append(dict(RECORDID=len(rows) + 1, INTERNALID=pid, RECORDSTATUS=1, USERID=doctor,
                             APPOINTMENTDATE=dt.datetime.combine(d, dt.time(0)), APPOINTMENTTIME=t, APPOINTMENTLENGTH=SLOT,
                             APPOINTMENTCODE=1, APPOINTMENTTYPE=1, REASON=_reason(rng, age),
                             CREATED=dt.datetime.combine(made, dt.time(9 + rng.randrange(8), rng.choice((0, 10, 20, 30, 40, 50)))),
                             CREATEDBY=RECEPTION, BOOKEDBY=RECEPTION, PATIENTS=1, LOCATIONID=1))
    assert len(rows) < SYN_APPT_LT
    return rows


if __name__ == '__main__':                                      # a look at the book, no database
    from collections import Counter
    pts = [(i, dt.date(1950 + i, 3, 14)) for i in range(1, 41)]
    book = make_bookings(pts, dt.date(2026, 11, 17))
    assert book == make_bookings(pts, dt.date(2026, 11, 17))
    per_day = Counter(r['APPOINTMENTDATE'].date() for r in book)
    for d in sorted(per_day):
        print(d, d.strftime('%a'), per_day[d], dict(Counter(r['USERID'] for r in book if r['APPOINTMENTDATE'].date() == d)))
    per_pt = Counter(r['INTERNALID'] for r in book)
    print(len(book), 'bookings;', 'per patient', min(per_pt.values()), 'to', max(per_pt.values()))
    for r in book:                                              # no clash: one patient a day, one booking a slot
        same = [x for x in book if x['APPOINTMENTDATE'] == r['APPOINTMENTDATE']]
        assert sum(x['INTERNALID'] == r['INTERNALID'] for x in same) == 1
        assert sum(x['USERID'] == r['USERID'] and x['APPOINTMENTTIME'] == r['APPOINTMENTTIME'] for x in same) == 1
    later = make_bookings(pts, dt.date(2026, 11, 19))           # the same day's bookings two days on
    key = lambda r: (r['APPOINTMENTDATE'], r['USERID'], r['APPOINTMENTTIME'], r['INTERNALID'], r['REASON'])
    assert {key(r) for r in later if r['APPOINTMENTDATE'].date() <= dt.date(2026, 12, 7)} == \
           {key(r) for r in book if r['APPOINTMENTDATE'].date() >= dt.date(2026, 11, 19)}
    print('checks passed')
