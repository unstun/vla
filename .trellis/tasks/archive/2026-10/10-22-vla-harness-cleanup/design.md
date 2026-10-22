# Design

Use .agents/skills as the canonical project-skill source. Keep all installed
trellis-* directories and nine project skills. Claude and Cursor retain their
Trellis-managed real directories; mirror remaining project skills with links.

The synchronization script becomes offline and project-only. It removes only
recognizable generated vendor links and dangling generated project links,
preserves unrelated links and real directories, and does not fetch or check out
vendor source. Keep vendor-skills.lock and the existing ignored checkout as
provenance; they no longer select active skills.

Disable routine prompt/session injection and review-flag mutation. Retain
agent-context hooks for explicitly requested delegation and Cursor's shell
session bridge. Read specs via Trellis skills; reset reviewed flags manually
when editing research documents. Main-session execution remains the default.

Retired tracked skill files are recoverable from the recorded starting commit.
Do not modify pre-existing dirty Trellis templates or any research evidence.
