from datetime import datetime, timedelta

from mcp.server.fastmcp import FastMCP

from rock_rms_mcp.client import RockClient

mcp = FastMCP("rock-rms")
rock = RockClient()

# ── Children's group type keywords for filtering ────────────────────
CHILDREN_GROUP_KEYWORDS = {
    "camp grace", "tree house", "play house", "mosaic",
    "quest", "up & out", "up and out", "ladybugs", "hedgehogs", "squirrels",
}

# ── Schedule IDs ─────────────────────────────────────────────────────
SCHEDULES = {"saturday": 1711, "9am": 1723, "11am": 1716}
SCHEDULE_NAMES = {1711: "Saturday", 1723: "9am", 1716: "11am"}

# ── Pelham children's location sets ──────────────────────────────────
PLAY_HOUSE = {13740, 13741, 13742, 13743, 13744, 13745, 13746, 13748}
TREE_HOUSE_1F = {13751, 13755, 13756, 13757, 13758, 13759}
TREE_HOUSE_2F = {13767, 13768, 13769, 13770, 13771, 13772, 13773}
QUEST = {13776}
CAMP_GRACE = {
    13778, 13779, 13780, 13781, 13782, 13783, 13784, 13785, 13786,
    13787, 13788, 13789, 13790, 13791, 13792, 13793,
}
UP_AND_OUT = {13765}
MOSAIC = {13762, 13763, 16232, 16233, 13774}

ALL_PELHAM_KIDS = (
    PLAY_HOUSE | TREE_HOUSE_1F | TREE_HOUSE_2F | QUEST |
    CAMP_GRACE | UP_AND_OUT | MOSAIC |
    {13735, 13736, 13737, 13738, 13739, 13749, 13761, 13762, 13764, 13766, 13777}
)

SATURDAY_OVERRIDES = {
    13741: "Play House",
    13756: "Tree House 1F",
    13759: "CG 1/2",
}

CATEGORY_ORDER = [
    "Play House", "Tree House 1F", "Tree House 2F", "Quest",
    "CG 1/2", "CG 3/4 Girls", "CG 3/4 Boys", "Up & Out", "Mosaic",
]

SATURDAY_CATEGORIES = {"Play House", "Tree House 1F", "Tree House 2F", "CG 1/2", "CG 3/4 Girls", "CG 3/4 Boys"}
SUNDAY_CATEGORIES = set(CATEGORY_ORDER)


def _categorize(location_id: int, group_name: str, service_key: str) -> str | None:
    g = (group_name or "").lower()

    if service_key == "saturday" and location_id in SATURDAY_OVERRIDES:
        return SATURDAY_OVERRIDES[location_id]

    if location_id in PLAY_HOUSE:
        return "Play House"
    if location_id in TREE_HOUSE_1F:
        return "Tree House 1F"
    if location_id in TREE_HOUSE_2F:
        return "Tree House 2F"
    if location_id in QUEST:
        return "Quest" if service_key in ("9am", "11am") else None
    if location_id in UP_AND_OUT:
        return "Up & Out" if service_key in ("9am", "11am") else None
    if location_id in MOSAIC:
        return "Mosaic" if service_key in ("9am", "11am") else None
    if location_id in CAMP_GRACE:
        if "1st grade" in g or "2nd grade" in g:
            return "CG 1/2"
        if "girl" in g and ("3rd" in g or "4th" in g):
            return "CG 3/4 Girls"
        if "boy" in g and ("3rd" in g or "4th" in g):
            return "CG 3/4 Boys"
        if "up and out" in g:
            return "Up & Out" if service_key in ("9am", "11am") else None
        return "CG 1/2"
    return None


def _fetch_occurrences(date_str: str, schedule_id: int) -> list[dict]:
    path = (
        f"AttendanceOccurrences"
        f"?$filter=OccurrenceDate eq datetime'{date_str}' and ScheduleId eq {schedule_id}"
        f"&$select=Id,GroupId,LocationId,ScheduleId"
        f"&$top=500"
    )
    return rock.get(path).json()


def _fetch_attendances(date_str: str) -> list[dict]:
    path = (
        f"Attendances"
        f"?$filter=StartDateTime ge datetime'{date_str}'"
        f" and StartDateTime lt datetime'{date_str}T23:59:59'"
        f" and DidAttend eq true"
        f"&$select=Id,OccurrenceId,PersonAliasId"
        f"&$top=5000"
    )
    return rock.get(path).json()


def _fetch_group(group_id: int) -> dict | None:
    try:
        return rock.get(f"Groups/{group_id}?$select=Id,Name,GroupTypeId").json()
    except Exception:
        return None


def _most_recent_sunday() -> str:
    today = datetime.now()
    days_since_sunday = (today.weekday() + 1) % 7
    if days_since_sunday == 0:
        days_since_sunday = 7
    sunday = today - timedelta(days=days_since_sunday)
    return sunday.strftime("%Y-%m-%d")


def _process_service(date_str: str, service_key: str, schedule_id: int) -> dict[str, int]:
    occurrences = _fetch_occurrences(date_str, schedule_id)
    pelham_occs = {
        o["Id"]: o for o in occurrences
        if o.get("LocationId") and o["LocationId"] in ALL_PELHAM_KIDS
    }

    if not pelham_occs:
        return {}

    attendances = _fetch_attendances(date_str)
    group_cache: dict[int, dict | None] = {}
    counts: dict[str, int] = {}

    for att in attendances:
        occ_id = att.get("OccurrenceId")
        if occ_id not in pelham_occs:
            continue

        occ = pelham_occs[occ_id]
        loc_id = occ["LocationId"]
        group_id = occ.get("GroupId")

        if group_id and group_id not in group_cache:
            group_cache[group_id] = _fetch_group(group_id)

        group_name = ""
        if group_id and group_cache.get(group_id):
            group_name = group_cache[group_id].get("Name", "")

        cat = _categorize(loc_id, group_name, service_key)
        if cat:
            valid = SATURDAY_CATEGORIES if service_key == "saturday" else SUNDAY_CATEGORIES
            if cat in valid:
                counts[cat] = counts.get(cat, 0) + 1

    return counts


@mcp.tool()
def ping() -> str:
    """Check connectivity to Rock RMS. Returns OK if authenticated."""
    rock.get("People?$top=1&$select=Id")
    return "OK — connected to Rock RMS"


@mcp.tool()
def get_attendance(
    date: str | None = None,
    schedule: str | None = None,
    location_group: str | None = None,
) -> dict:
    """Get children's check-in attendance counts from Rock RMS.

    Args:
        date: Date in YYYY-MM-DD format. Defaults to most recent Sunday.
        schedule: Filter to a specific service: "saturday", "9am", or "11am". Returns all services if omitted.
        location_group: Filter to a specific category like "Play House", "CG 1/2", etc. Returns all if omitted.

    Returns counts bucketed by category (Play House, Tree House 1F, Tree House 2F, Quest,
    CG 1/2, CG 3/4 Girls, CG 3/4 Boys, Up & Out, Mosaic) for each service, plus totals.
    """
    if date is None:
        date = _most_recent_sunday()

    dt = datetime.strptime(date, "%Y-%m-%d")
    day_of_week = dt.weekday()  # 5=Sat, 6=Sun

    if schedule:
        key = schedule.lower().strip()
        if key not in SCHEDULES:
            return {"error": f"Unknown schedule '{schedule}'. Valid: saturday, 9am, 11am"}
        services = [(key, SCHEDULES[key])]
    else:
        if day_of_week == 5:
            services = [("saturday", SCHEDULES["saturday"])]
        elif day_of_week == 6:
            services = [("9am", SCHEDULES["9am"]), ("11am", SCHEDULES["11am"])]
        else:
            all_keys = ["saturday", "9am", "11am"]
            services = [(k, SCHEDULES[k]) for k in all_keys]

    result: dict = {"date": date, "services": {}, "grand_total": 0}

    for service_key, schedule_id in services:
        counts = _process_service(date, service_key, schedule_id)

        if location_group:
            counts = {k: v for k, v in counts.items() if k == location_group}

        ordered = {cat: counts.get(cat, 0) for cat in CATEGORY_ORDER if cat in counts}
        service_total = sum(ordered.values())

        result["services"][service_key] = {
            "schedule_id": schedule_id,
            "categories": ordered,
            "total": service_total,
        }
        result["grand_total"] += service_total

    return result


@mcp.tool()
def search_people(
    name: str,
    group_type: str | None = None,
) -> dict:
    """Search for children, families, or volunteers by name in Rock RMS.

    Args:
        name: Name to search for (first, last, or full name).
        group_type: Optional filter to children's group types. Use one of:
            "Camp Grace", "Tree House", "Play House", "Mosaic" to filter
            to people in those children's ministry groups.

    Returns a list of up to 10 matching people with name, age, birthdate,
    email, phone, and family members.
    """
    if not name or not name.strip():
        return {"error": "name parameter is required"}

    resp = rock.get(f"People/Search?name={name}&includeDetails=true&top=10")
    people = resp.json()

    if not isinstance(people, list):
        return {"results": [], "count": 0}

    results = []
    for person in people[:10]:
        person_id = person.get("Id")

        phones = []
        for phone in (person.get("PhoneNumbers") or []):
            number = phone.get("NumberFormatted") or phone.get("Number", "")
            if number:
                phones.append({
                    "type": phone.get("NumberTypeValue", {}).get("Value", "Unknown"),
                    "number": number,
                })

        family_members = []
        try:
            families = rock.get(f"Groups/GetFamilies/{person_id}").json()
            for fam in (families if isinstance(families, list) else []):
                for member in (fam.get("Members") or []):
                    mp = member.get("Person") or {}
                    mid = mp.get("Id")
                    if mid and mid != person_id:
                        family_members.append({
                            "name": f"{mp.get('NickName', '')} {mp.get('LastName', '')}".strip(),
                            "role": (member.get("GroupRole") or {}).get("Name", ""),
                            "age": mp.get("Age"),
                        })
        except Exception:
            pass

        entry = {
            "id": person_id,
            "name": f"{person.get('NickName', '')} {person.get('LastName', '')}".strip(),
            "full_name": f"{person.get('FirstName', '')} {person.get('NickName', '') if person.get('NickName') != person.get('FirstName') else ''} {person.get('LastName', '')}".strip().replace("  ", " "),
            "age": person.get("Age"),
            "birthdate": person.get("BirthDate", "")[:10] if person.get("BirthDate") else None,
            "email": person.get("Email"),
            "phones": phones,
            "family_members": family_members,
        }
        results.append(entry)

    if group_type:
        gt_lower = group_type.lower().strip()
        filtered = []
        for entry in results:
            try:
                memberships = rock.get(
                    f"GroupMembers?$filter=PersonId eq {entry['id']} and GroupMemberStatus eq 'Active'"
                    f"&$select=GroupId"
                    f"&$expand=Group"
                    f"&$top=50"
                ).json()
                for gm in (memberships if isinstance(memberships, list) else []):
                    gname = ((gm.get("Group") or {}).get("Name") or "").lower()
                    if gt_lower in gname:
                        filtered.append(entry)
                        break
            except Exception:
                pass
        results = filtered

    return {"results": results, "count": len(results)}


def main():
    mcp.run(transport="stdio")
