# Keyboard Spot Controls Design

## Goal

Let an operator work the spot table without reaching for the mouse, while keeping radio tuning as an explicit action. The keyboard flow should make browsing cheap, make activation deliberate, and keep the existing mouse controls intact.

## Interaction Model

- `j` and `Down Arrow` move the highlighted spot down one visible row.
- `k` and `Up Arrow` move the highlighted spot up one visible row.
- `Space` activates the highlighted spot by using the same tune-and-logger path as a row click.
- `w` marks the highlighted spot worked by using the existing worked action.
- `n` marks the highlighted spot nil copy by using the existing can't-hear temporary ignore action.
- Navigation alone never tunes the radio or sends a logger update.
- If no spot is highlighted and visible spots exist, the first keyboard command selects the first visible row. For `Space`, `w`, and `n`, the command then acts on that selected row.
- If no spots are visible, keyboard commands are harmless no-ops.

## Architecture

The feature belongs in `MainWindow`, near the existing table selection and row activation behavior. `MainWindow` should install keyboard shortcuts or override key handling for the table-focused workflow, then route each command through small helper methods:

- current-row lookup that handles no-selection and empty-table states.
- relative selection movement with row bounds.
- current spot activation via `handle_row_activated(row)`.
- current spot worked/nil-copy actions via `mark_worked(spot)` and `mark_cant_hear(spot)`.

This keeps the new shortcuts as a thin command layer over existing behavior instead of duplicating tune, logger, worked, or ignore logic.

## Focus Behavior

The table should have focus after rendering and after row-changing commands, so repeated shortcuts work naturally. Existing buttons, checkboxes, and settings dialog behavior should continue to receive normal keyboard input when they are focused. Letter shortcuts should be scoped to the spot table/main window workflow, not to text fields inside settings.

## Error Handling

The feature should reuse existing error handling. If `Space` activates a spot and rig or logger work fails, `handle_row_activated` already reports the error in the status label. Worked and nil-copy commands should follow the existing status messages and re-render behavior.

## Testing

Add GUI tests for:

- `j` and `Down Arrow` move selection down without tuning or sending logger updates.
- `k` and `Up Arrow` move selection up without tuning or sending logger updates.
- `Space` activates the highlighted row and sends the same rig/logger commands as a click.
- `w` marks the highlighted spot worked without tuning.
- `n` marks the highlighted spot can't-hear/nil-copy without tuning.
- Shortcut commands on an empty table do not crash.
