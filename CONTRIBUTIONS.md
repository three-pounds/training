# Upstream contributions

What this project intends to give back to the open source projects it builds on, and where each
piece stands. Nothing here is published until a person publishes it: an entry reaches
`published` only when its link points at a real issue or pull request.

Status values: `idea`, `draft-ready`, `published`, `answered`, `closed`.

| id | upstream | what | status | link | next action | last change |
|---|---|---|---|---|---|---|
| C1 | wger-project/mcp-server | Document in `log_set` that wger's weight field is non-negative and has no meaning of its own, and what that implies for assisted, bodyweight and added loads | idea | | Draft a `docs` pull request against the `log_set` docstring | 2026-11-04 |
| C2 | wger-project/mcp-server | Optional `load_kind` on `log_set` and a `WGER_ASSISTED_EXERCISE_IDS` setting, so an assisted exercise cannot be logged as added load | idea | | Open a short issue first, with the prototype in a fork as evidence; independent precedent: openGym models assistance per exercise, weight meaning the help | 2026-11-04 |
| C3 | wger catalog | Correct exercise data that contradicts itself: category and muscle of "Side Lateral Raise (Cable)", the equipment field of "Assisted Pull-Up", and the name versus description of "High-Cable Lateral Raise" | idea | | Find out how catalog corrections are submitted and reviewed | 2026-11-04 |
| C4 | wger-project/wger | Review the cardio logging request (#2510) against real swim and cardio logs, without personal data | idea | | Read the thread and write a short comment describing the fields a swim block needs | 2026-11-04 |
| C5 | wger-project/wger | Represent assisted load in the core, once there is use evidence from C2 | idea | | Wait for use evidence; open an issue before any code | 2026-11-04 |

## Rules

- Issue before code in a core project.
- One small branch per topic in a fork.
- No blocking rule is proposed without evidence from real use, false positives included.
- The agent drafts; a person publishes.
