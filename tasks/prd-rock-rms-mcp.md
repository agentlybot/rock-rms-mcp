# PRD: Rock RMS MCP Server

## Overview
Grace Church Pelham staff (starting with Allison Scott) currently query Rock RMS through its web UI, which requires navigating multiple screens to answer simple questions like "How many kids checked in Sunday?" or "Who was in the 9am Hedgehogs class?" An MCP server wrapping Rock's REST API would let staff ask these questions in natural language through Claude Desktop, with each user authenticating via their own Rock RMS credentials.

## Goals
- [ ] Goal 1: Staff can query children's attendance by date, service, and location in under 10 seconds
- [ ] Goal 2: Staff can search for people (kids, families, volunteers) by name
- [ ] Goal 3: Staff can view group rosters and check-in lists for any service
- [ ] Goal 4: Staff can ask for attendance trends and comparisons across weeks
- [ ] Goal 5: Zero-maintenance deployment — runs locally on the user's machine via Claude Desktop

## User Stories

### US-001: Project scaffold and Rock RMS authentication
**As a** developer
**I want** a Python MCP server scaffold with Rock RMS cookie-based auth
**So that** all subsequent tools can make authenticated API calls

**Acceptance Criteria:**
- [ ] Python project with `pyproject.toml`, using `mcp` SDK and `requests`
- [ ] `RockClient` class that authenticates via `POST /api/Auth/Login`
- [ ] Handles 204 response with `.ROCK` cookie from `Set-Cookie` header
- [ ] Re-authenticates automatically if session expires (403 response)
- [ ] Credentials read from environment variables `ROCK_USERNAME` and `ROCK_PASSWORD`
- [ ] MCP server starts and registers with Claude Desktop
- [ ] `pip install .` works

### US-002: Get attendance counts tool
**As a** Grace Church staff member
**I want** to ask "How many kids checked in last Sunday at 9am?"
**So that** I can quickly get attendance numbers without navigating Rock's UI

**Acceptance Criteria:**
- [ ] Tool `get_attendance` accepts `date` (YYYY-MM-DD), optional `schedule` (saturday/9am/11am), optional `location_group` (play_house/tree_house/camp_grace/quest/mosaic/up_and_out)
- [ ] Queries `AttendanceOccurrences` filtered by date + schedule ID + Pelham kids locations
- [ ] Queries `Attendances` where `DidAttend eq true`, joins to occurrences
- [ ] Returns counts bucketed by location category (Play House, Tree House 1F, Tree House 2F, Quest, Camp Grace 1/2, CG 3/4 Girls, CG 3/4 Boys, Up & Out, Mosaic)
- [ ] Saturday applies room overrides (Ladybugs→PH, Hedgehogs→TH, Squirrels→CG)
- [ ] If no schedule specified, returns all services for that date
- [ ] If no date specified, defaults to most recent Sunday
- [ ] Returns totals per service and grand total

### US-003: Search people tool
**As a** Grace Church staff member
**I want** to search for a child or family member by name
**So that** I can look up their info without navigating Rock's People screens

**Acceptance Criteria:**
- [ ] Tool `search_people` accepts `name` (string), optional `group_type` filter
- [ ] Queries `GET /api/People/Search?name={name}&includeDetails=true`
- [ ] Returns: full name, age/birthdate, email, phone, family members
- [ ] Limits results to top 10 matches
- [ ] Can filter to children's group types (Camp Grace, Tree House, Play House, Mosaic)

### US-004: Get check-in roster tool
**As a** Grace Church staff member
**I want** to see exactly who checked in for a specific service and room
**So that** I can verify attendance or follow up with families

**Acceptance Criteria:**
- [ ] Tool `get_checkin_roster` accepts `date`, `schedule`, optional `location` or `group`
- [ ] Returns list of checked-in individuals with: name, group name, location/room name, check-in time
- [ ] Resolves PersonAliasId → Person name via `/api/PersonAlias/{id}` and `/api/People/{id}`
- [ ] Caches person lookups within a single request to minimize API calls
- [ ] Results sorted by location, then by name

### US-005: Get group roster tool
**As a** Grace Church staff member
**I want** to see who is in a specific group (e.g., "Kerplunk" or "3rd Grade Boys")
**So that** I can see the full roster independent of check-in

**Acceptance Criteria:**
- [ ] Tool `get_group_roster` accepts `group_name` (string) or `group_id` (int)
- [ ] Searches groups via `GET /api/Groups?$filter=Name eq '{name}'` or by ID
- [ ] Fetches group members via `GET /api/Groups/{id}/Members`
- [ ] Returns: member name, role (Leader/Member), status (Active/Inactive)
- [ ] Includes group metadata: name, description, group type, schedule, location

### US-006: Attendance trends tool
**As a** Grace Church staff member
**I want** to compare attendance across multiple weeks
**So that** I can spot trends, plan staffing, and identify growth/decline

**Acceptance Criteria:**
- [ ] Tool `get_attendance_trends` accepts `start_date`, `end_date`, optional `schedule`, optional `location_group`
- [ ] Fetches attendance for each Sunday (and preceding Saturday) in the range
- [ ] Returns per-week breakdown by service and category
- [ ] Includes summary stats: average, min, max, trend direction (up/down/flat)
- [ ] Handles missing weeks (holidays, weather cancellations) gracefully — shows 0 or "no service"

### US-007: List schedules and locations tool
**As a** Grace Church staff member
**I want** to see available schedules and location names
**So that** I know valid options when querying attendance

**Acceptance Criteria:**
- [ ] Tool `list_schedules` returns all Pelham children's schedule IDs with names and times
- [ ] Tool `list_locations` returns the Pelham children's building location hierarchy with IDs and names
- [ ] Both tools return static data (hardcoded Pelham config) — no API call needed
- [ ] Serves as reference data for the LLM to construct valid queries

## Functional Requirements
1. FR-001: All API calls must use the authenticated user's `.ROCK` session cookie
2. FR-002: The server must re-authenticate if a 403 is received and retry the request once
3. FR-003: All tools must filter to Pelham campus children's locations only
4. FR-004: OData queries must use Rock's v3 syntax (not v4)
5. FR-005: The server must handle Rock's pagination (`$top`, `$skip`) for large result sets
6. FR-006: All dates must be accepted in both YYYY-MM-DD and natural language (the LLM handles NL→date conversion)

## Non-Functional Requirements
1. NFR-001: Read-only — no tools that create, update, or delete Rock RMS records
2. NFR-002: Each user must authenticate with their own Rock RMS credentials
3. NFR-003: Credentials stored as environment variables, never logged or exposed in tool output
4. NFR-004: API calls should include reasonable `$top` limits (500 for occurrences, 5000 for attendances) to prevent overloading Rock
5. NFR-005: Person lookups cached per-request to minimize redundant API calls

## Non-Goals
- Writing data to Rock RMS (check-ins, person updates, group changes)
- Supporting campuses other than Pelham (can be added later)
- Adult/student ministry attendance (children's only for now)
- Real-time check-in monitoring or webhooks
- Hosting as a shared service — this runs locally per user

## Technical Considerations

### Architecture
```
Claude Desktop → stdio → rock-rms-mcp (Python process) → HTTPS → Rock RMS API
```

### Rock RMS API Details
- Base URL: `https://rock.gracechurchsc.org/api`
- Auth: `POST /api/Auth/Login` → 204 + `.ROCK` cookie via `Set-Cookie`
- OData v3 (no nested `$expand`)
- Key endpoints: `AttendanceOccurrences`, `Attendances`, `People`, `Groups`, `PersonAlias`

### Schedule IDs (Pelham)
| Schedule | ID |
|----------|-----|
| Saturday 5:00pm | 1711 |
| Sunday 9:00am | 1723 |
| Sunday 11:00am | 1716 |

### Pelham Children's Location Hierarchy
- Play House (13739): Snails, Ladybugs, Dragonflies, Roly Polies, Caterpillars, Butterflies, Bumblebees, Grasshoppers
- Tree House 1F (13749): Raccoons, Chipmunks, Hedgehogs, Beavers, Otters, Squirrels
- Tree House 2F (13766): Owls, Turtle Doves, Woodpeckers, Hummingbirds, Chickadees, Blue Jays, Sparrows
- Quest (13776)
- Camp Grace (13777): Lodge, Animal House, Bear Den, Watering Hole, Lightning Bugs, Mini Marshmallows, Skeeters, Mud Hole, Skippin' Stones, Briar Patch, Kerplunk, Lakeside, Fox Hole, Spittin' Distance, Fireside, Fishing Hole
- Up & Out (13765)
- Mosaic (13762): Basecamp, Pavillion, Monkey Bars

### Installation (end user)
```bash
pip install rock-rms-mcp
```

Claude Desktop `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "rock-rms": {
      "command": "python",
      "args": ["-m", "rock_rms_mcp"],
      "env": {
        "ROCK_USERNAME": "allison.scott",
        "ROCK_PASSWORD": "her-password"
      }
    }
  }
}
```

## Open Questions
- What Rock RMS permission level do staff accounts need for API access? (Need to verify Allison's account has API read permissions)
- Should we include volunteer schedule lookups (who's serving this week)?
- Are there other campuses that would want this later?
