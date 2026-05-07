# Complete QSO From Keyboard Design

## Goal

Let an operator complete and log a selected POTA QSO without leaving POTA Spot Hunter. The feature should preserve the fast keyboard workflow: tune with `Space`, complete with `Shift+W`, enter reports, and submit with `Enter`.

## Interaction Model

- `Space` keeps the current behavior: tune the radio and send a WSJT-X-compatible status update to the logger.
- Lowercase `w` keeps the current behavior: mark the highlighted spot worked without logging a QSO.
- `Shift+W` opens a modal QSO completion dialog for the highlighted spot.
- The dialog shows sent and received RST fields.
- Default reports are mode-aware:
  - `599` for `CW`
  - `59` for other modes
- The sent RST field is focused and selected so the operator can type over it immediately.
- Received RST is optional. If left blank, omit `RST_RCVD` from ADIF.
- `Enter` sends a WSJT-X `Logged ADIF` UDP packet, then marks the spot worked.
- `Esc` or cancel closes the dialog without logging or marking worked.

## Logger Data

The logger remains the source of station identity. POTA Spot Hunter should not send `STATION_CALLSIGN`, `OPERATOR`, or other station profile fields.

Send a lean ADIF record containing:

- `CALL`: selected activator callsign
- `QSO_DATE`: UTC date at the time of logging
- `TIME_ON`: UTC time at the time of logging
- `BAND`: selected spot band, uppercase
- `FREQ`: selected spot frequency in MHz
- `MODE`: selected spot mode
- `RST_SENT`: sent report
- Optional `RST_RCVD`: received report when provided
- `SIG`: `POTA`
- `SIG_INFO`: selected spot park reference

Wrap that ADIF record in the WSJT-X `Logged ADIF` UDP message, message type `12`, using the existing WSJT-X-style framing helpers.

## Architecture

Add a small QSO logging layer to `logger_udp.py`:

- Build ADIF fields with correct ADIF length tags.
- Build a `Logged ADIF` packet.
- Add `LoggerClient.log_qso(spot, rst_sent, rst_received=None)`.

Add GUI support to `gui.py`:

- Extend the `Logger` protocol with `log_qso`.
- Add `CompleteQsoDialog`.
- Add `complete_selected_qso`.
- Update the table event filter so `Shift+W` completes QSO while plain `w` still marks worked.

The GUI should only mark a spot worked after `logger.log_qso` succeeds. If logging raises an exception, keep the row visible and show the error in the status label.

## Testing

Add tests for:

- ADIF field formatting with lengths.
- Logged ADIF packet framing and message type `12`.
- `LoggerClient.log_qso` sending heartbeat plus logged ADIF.
- Default report selection for CW and non-CW spots.
- `Shift+W` opening completion flow without triggering lowercase worked behavior.
- Successful completion logs the QSO and then hides the row as worked.
- Canceling completion does not log or mark worked.
- Logger failure leaves the row visible and reports an error.
