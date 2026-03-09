#!/bin/bash
# Ralph runner script for Rock RMS MCP Server
# Usage: ./scripts/ralph/ralph.sh [max_iterations]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PRD_FILE="$REPO_ROOT/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"

cd "$REPO_ROOT"

MAX_ITERATIONS="${1:-10}"

echo "Starting Ralph (Claude Code)..."
echo "   Working directory: $REPO_ROOT"
echo "   PRD file: $PRD_FILE"
echo "   Max iterations: $MAX_ITERATIONS"
echo ""

# Check prerequisites
if ! command -v claude &> /dev/null; then
    echo "Error: 'claude' CLI not found. Please install Claude Code."
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo "Error: 'jq' not found. Please install jq."
    exit 1
fi

if [ ! -f "$PRD_FILE" ]; then
    echo "Error: prd.json not found at $PRD_FILE"
    exit 1
fi

# Initialize progress file if not exists
if [ ! -f "$PROGRESS_FILE" ]; then
    echo "# Ralph Progress Log" > "$PROGRESS_FILE"
    echo "" >> "$PROGRESS_FILE"
    echo "Project: $(jq -r '.project' "$PRD_FILE")" >> "$PROGRESS_FILE"
    echo "Branch: $(jq -r '.branchName' "$PRD_FILE")" >> "$PROGRESS_FILE"
    echo "Started: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$PROGRESS_FILE"
    echo "" >> "$PROGRESS_FILE"
fi

# Create/checkout branch
BRANCH_NAME=$(jq -r '.branchName' "$PRD_FILE")
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")

if [ "$CURRENT_BRANCH" != "$BRANCH_NAME" ]; then
    echo "Checking out branch: $BRANCH_NAME"
    if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
        git checkout "$BRANCH_NAME"
    else
        git checkout -b "$BRANCH_NAME"
    fi
fi

# Main iteration loop
for ((i=1; i<=MAX_ITERATIONS; i++)); do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Iteration $i/$MAX_ITERATIONS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Get next incomplete story (lowest priority with passes=false)
    NEXT_STORY=$(jq -r '
        .userStories
        | map(select(.passes == false))
        | sort_by(.priority)
        | .[0]
        // empty
    ' "$PRD_FILE")

    if [ -z "$NEXT_STORY" ] || [ "$NEXT_STORY" == "null" ]; then
        echo ""
        echo "All user stories complete!"
        echo "<promise>COMPLETE</promise>"
        echo "" >> "$PROGRESS_FILE"
        echo "## Completed: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$PROGRESS_FILE"
        echo "All user stories marked as passes: true" >> "$PROGRESS_FILE"
        break
    fi

    STORY_ID=$(echo "$NEXT_STORY" | jq -r '.id')
    STORY_TITLE=$(echo "$NEXT_STORY" | jq -r '.title')
    STORY_DESC=$(echo "$NEXT_STORY" | jq -r '.description')
    STORY_CRITERIA=$(echo "$NEXT_STORY" | jq -r '.acceptanceCriteria | join("\n- ")')

    echo "Working on: $STORY_ID - $STORY_TITLE"
    echo "   $STORY_DESC"
    echo ""

    # Log to progress file
    echo "" >> "$PROGRESS_FILE"
    echo "## Iteration $i - $STORY_ID: $STORY_TITLE" >> "$PROGRESS_FILE"
    echo "Started: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$PROGRESS_FILE"

    # Build the prompt for Claude
    PROMPT=$(cat <<EOF
You are Ralph, an autonomous development agent building a Rock RMS MCP Server.

## Current Task
**Story ID:** $STORY_ID
**Title:** $STORY_TITLE
**Description:** $STORY_DESC

**Acceptance Criteria:**
- $STORY_CRITERIA

## Instructions
1. Read the existing codebase structure to understand the project
2. Implement this single user story following all acceptance criteria
3. Commit your changes with a descriptive message referencing $STORY_ID
4. After successful completion, update prd.json to set passes: true for $STORY_ID
5. Append learnings to scripts/ralph/progress.txt

## Project Context
- This is a Python MCP server for Rock RMS (Grace Church's church management system)
- Rock RMS API base: https://rock.gracechurchsc.org/api
- Auth: POST /api/Auth/Login returns 204 with .ROCK cookie via Set-Cookie header
- OData v3 syntax (not v4, no nested \$expand)
- Use the \`mcp\` Python SDK for MCP server implementation
- Use \`requests\` for HTTP calls to Rock RMS
- The server communicates over stdio with Claude Desktop
- Read-only: NO tools that create, update, or delete Rock RMS records
- All tools filter to Pelham campus children's locations only
- Credentials via env vars: ROCK_USERNAME, ROCK_PASSWORD

## Key Rock RMS Details
- Schedule IDs: Saturday=1711, 9am=1723, 11am=1716
- Pelham children's locations: Play House (13739), Tree House 1F (13749), Tree House 2F (13766), Quest (13776), Camp Grace (13777), Up & Out (13765), Mosaic (13762)
- Saturday only has 3 rooms: Ladybugs (13741)→PH, Hedgehogs (13756)→TH, Squirrels (13759)→CG
- Camp Grace groups split by group name: "1st Grade"/"2nd Grade"→CG 1/2, "3rd/4th Grade Girls"→CG 3/4 Girls, "3rd/4th Grade Boys"→CG 3/4 Boys

## Reference Implementation
Check /Users/jonscott/Desktop/DevProjects/rock-attendance/update_gck_sheet.py for working Rock RMS auth and attendance fetching patterns.

## Quality Gates
Before marking complete:
- [ ] All acceptance criteria verified
- [ ] pip install . works (test with pip install -e .)
- [ ] python -m rock_rms_mcp starts without error (ctrl+c to exit)
- [ ] Changes committed
- [ ] prd.json updated with passes: true for $STORY_ID
- [ ] progress.txt updated with learnings

When the story is fully complete and verified, output:
<promise>STORY_COMPLETE</promise>

If ALL stories are now complete, also output:
<promise>COMPLETE</promise>
EOF
)

    # Run Claude Code with the prompt
    echo "$PROMPT" | claude --dangerously-skip-permissions -p - 2>&1 | tee -a /tmp/ralph_iteration_$i.log

    RESULT=$?

    # Check output for completion signals
    if grep -q "<promise>COMPLETE</promise>" /tmp/ralph_iteration_$i.log; then
        echo ""
        echo "All stories complete!"
        echo "Completed: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$PROGRESS_FILE"
        break
    fi

    if grep -q "<promise>STORY_COMPLETE</promise>" /tmp/ralph_iteration_$i.log; then
        echo ""
        echo "Story $STORY_ID completed"
        echo "Completed: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$PROGRESS_FILE"
    else
        echo ""
        echo "Story $STORY_ID iteration ended without completion signal"
        echo "Status: Incomplete - $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$PROGRESS_FILE"
    fi

    # Brief pause between iterations
    sleep 2
done

echo ""
echo "Ralph finished after $i iterations."
echo "   Check progress.txt for learnings"
echo "   Check prd.json for completion status"
