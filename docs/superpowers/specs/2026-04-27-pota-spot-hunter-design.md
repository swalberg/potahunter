# POTA Spot Hunter Design

## Goal

Build a simple Windows-focused Python desktop app for hunting Parks on the Air spots. The app shows current POTA spots, lets the user click a row to tune the radio, sends a WSJT-X-compatible UDP update to the logging ecosystem, and lets the user remove spots from view after trying them.

The first real station target is Windows with OmniRig and Log4OM. Development can proceed on macOS by using fake rig and logger implementations.

## Scope

In scope for the first version:

- Show all current POTA spots in a table.
- Refresh spots periodically.
- Click a spot row to tune the radio and send logger UDP details.
- Mark a spot as `Worked`.
- Mark a spot as `Can't Hear`.
- Hide worked spots until the activator changes band or mode.
- Hide can't-hear spots for a configurable time, defaulting to 15 minutes.
- Keep suppression state only in memory.
- Provide settings for refresh interval, ignore duration, logger UDP host and port, and OmniRig radio selection.

Out of scope for the first version:

- Cross-platform rig control.
- Persistent worked or ignored history.
- Automatic QSO detection from Log4OM.
- POTA account login, spotting, or re-spotting.
- Advanced filters beyond showing all current spots.

## User Interface

The main window is a table-first interface optimized for quick hunting. Each row represents one current POTA spot and includes activator call, frequency, mode, park reference, and comments or spotter details.

Clicking a row is the primary action. A row click tunes the radio through OmniRig and sends the logger update. The row becomes highlighted and the status line reports what happened.

Each row has two explicit disposition buttons:

- `Worked`: hide this activator/park/band/mode until the activator changes band or mode.
- `Can't Hear`: hide this activator/park/band/mode until the ignore timer expires.

The table header, selected row, and hover states must maintain readable foreground/background contrast. A selected row should remain visually obvious without making text hard to read.

## Spot Identity and Suppression Rules

The app normalizes each spot into a stable key:

- Activator callsign.
- Park reference.
- Derived amateur band.
- Mode.

The visible list is rebuilt from the latest fetched spots minus in-memory suppressions.

`Worked` suppression hides the current activator/park/band/mode key until the same activator and park appears on a different band or mode. A small frequency change within the same band does not make the worked spot reappear.

`Can't Hear` suppression hides the current activator/park/band/mode key until its expiry time. The default is 15 minutes and is configurable.

No suppression state is written to disk. Restarting the app starts fresh.

## Architecture

The app is split into small components:

- `SpotSource`: fetches current POTA spots and returns normalized spot objects.
- `SpotState`: applies worked and can't-hear suppression rules.
- `RigController`: defines the tuning interface.
- `FakeRigController`: development implementation used on macOS and in tests.
- `OmniRigController`: Windows COM implementation for OmniRig.
- `LoggerClient`: builds and sends WSJT-X-compatible UDP messages.
- `Settings`: loads, validates, and saves app configuration.
- `GUI`: PySide6/Qt table, status line, settings dialog, and event wiring.

The app should not bake Log4OM-specific behavior into the component name. The first validation target is Log4OM, but the UDP layer should be described and tested as WSJT-X-compatible logger messaging so it can also work with tools that follow that convention.

## Data Flow

1. A timer asks `SpotSource` for current POTA spots.
2. Spots are normalized and passed through `SpotState`.
3. The GUI renders the visible list.
4. The user clicks a row.
5. The GUI asks `RigController` to tune frequency and mode.
6. The GUI asks `LoggerClient` to send a WSJT-X-compatible UDP update.
7. The status line reports success or any partial failure.
8. If the user clicks `Worked` or `Can't Hear`, `SpotState` records an in-memory suppression and the table refreshes.

## Error Handling

The app should fail visibly but keep running.

- If POTA fetching fails, keep the last displayed spots and show a status message.
- If OmniRig is unavailable or rejects a command, report the error in the status line.
- If logger UDP sending fails locally, report the error in the status line.
- A row is not automatically marked worked or ignored after tuning or logger updates.
- Settings validation rejects invalid ports, empty logger hosts, non-positive refresh intervals, and negative ignore durations.

## Testing

Automated tests should cover:

- Spot normalization.
- Worked suppression.
- Can't-hear suppression and expiry.
- Settings validation.
- Logger UDP packet construction.
- GUI action wiring using fake rig and logger clients.

Manual Windows validation should cover:

- OmniRig connection and tuning.
- Log4OM receiving the WSJT-X-compatible UDP update.
- Packaging and launching the app on Windows.

## Integration Notes

The POTA public API documentation is sparse, so `SpotSource` should be isolated behind an interface and verified during implementation against the current POTA spot endpoint behavior.

The exact UDP message shape should be verified against Log4OM during implementation. Start from standard WSJT-X network message framing and keep the logger module generic enough for other WSJT-X-compatible consumers.
