#!/usr/bin/env python3
"""
seed_persona_calendar.py — seed the simulator calendar with a REALISTIC persona:
a Royal Enfield product-head VP's week (VJ 2026-08-25, replaces "Test Meeting NN"
for the ep1 app showcase). Reuses the app repo's proven seeder internals.

Usage: shutdown sim first, then:  python3 seed_persona_calendar.py <udid>
"""
import importlib.util, os, sqlite3, sys, time, uuid, datetime as dt
from zoneinfo import ZoneInfo

SEEDER = "/Users/vijenderpanda/missnomeetings/Tools/seed-simulator-calendar.py"
spec = importlib.util.spec_from_file_location("seeder", SEEDER)
sd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sd)

MEETINGS = [
    "Hunter 350 refresh — design review",
    "VP sync: Q3 dealer expansion",
    "Supplier QBR — braking systems",
    "Himalayan launch film — final cut",
    "1:1 with CEO — product roadmap",
    "Chennai plant visit prep — Line 2",
    "Accessories range — pricing call",
    "Media fleet — test ride feedback",
    "Warranty data deep-dive",
    "Design studio — 2027 concepts",
]


def seed_persona(cur, tzname):
    tz = ZoneInfo(tzname)
    now = time.time()
    days = {}
    for i, title in enumerate(MEETINGS):
        start = now + 40 * 60 + i * 105 * 60
        end = start + 30 * 60
        cur.execute("""insert into CalendarItem
            (summary,start_date,start_tz,end_date,end_tz,all_day,calendar_id,entity_type,
             status,availability,privacy_level,UUID,unique_identifier,hidden,creation_date,flags)
            values (?,?,?,?,?,0,?,2,0,0,0,?,?,0,?,0)""",
            (title, start - sd.REF, tzname, end - sd.REF, tzname, sd.CAL_ID,
             str(uuid.uuid4()).upper(), "gregorian/" + str(uuid.uuid4()).upper(), now - sd.REF))
        rowid = cur.lastrowid
        midnight = dt.datetime.fromtimestamp(start, tz).replace(hour=0, minute=0,
                                                                second=0, microsecond=0)
        day = midnight.timestamp() - sd.REF
        cur.execute("""insert into OccurrenceCache
            (day,event_id,calendar_id,store_id,occurrence_date,occurrence_start_date,
             occurrence_end_date,latest_possible_alarm,earliest_possible_alarm)
            values (?,?,?,?,?,?,?,?,?)""",
            (day, rowid, sd.CAL_ID, sd.STORE_ID, start - sd.REF, start - sd.REF,
             end - sd.REF, start - sd.REF, start - sd.REF - 7 * 86400))
        days[day] = days.get(day, 0) + 1
    for day, n in days.items():
        cur.execute("""insert into OccurrenceCacheDays (calendar_id,store_id,day,count)
                       values (?,?,?,?)
                       on conflict(calendar_id,day) do update set count = count + excluded.count""",
                    (sd.CAL_ID, sd.STORE_ID, day, n))
    print(f"seeded {len(MEETINGS)} persona meetings across {len(days)} days")


def clean_all(cur):
    sd.clean(cur)  # removes Test Meeting rows
    titles = tuple(MEETINGS)
    q = ",".join("?" * len(titles))
    cur.execute(f"""delete from OccurrenceCache where event_id in
                   (select ROWID from CalendarItem where summary in ({q}))""", titles)
    cur.execute(f"delete from CalendarItem where summary in ({q})", titles)


if __name__ == "__main__":
    udid = sys.argv[1]
    con = sqlite3.connect(sd.db_path(udid))
    sd.register_stubs(con)
    cur = con.cursor()
    clean_all(cur)
    if "--clean" not in sys.argv:
        tzname = os.readlink("/etc/localtime").split("zoneinfo/")[-1]
        seed_persona(cur, tzname)
    con.commit(); con.close()
