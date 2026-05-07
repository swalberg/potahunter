# Spot Age Column Design

## Goal

Show how recently each POTA spot was last heard so an operator can prioritize fresh spots without inspecting raw timestamps.

## Interaction Model

Add an `Age` column to the spot table. The column displays compact relative age text based on the POTA API `spotTime` value:

- Less than 1 minute: `0m`
- 1 to 59 minutes: `Xm`
- 1 hour or more: `Xh Ym`

Examples: `2m`, `18m`, `1h 12m`.

If a spot has no usable timestamp, show an empty age cell rather than failing to render the row.

## Data Model

Store the parsed `spotTime` on `Spot` as an optional timezone-aware `datetime`. The parser should treat POTA timestamps without an explicit timezone as UTC, matching the API's current shape. Invalid or missing `spotTime` should not make an otherwise usable spot disappear.

Existing spot identity stays unchanged: worked and can't-hear suppression should still key on activator, park, band, and mode only.

## GUI Rendering

Place `Age` as the leftmost table column, followed by `Call`, so operators see freshness before anything else. Sort the displayed spot list by age with the newest spots first and spots without usable timestamps at the bottom. Existing row activation, keyboard shortcuts, filtering, and action buttons should continue to use the same visible row indexes and spot objects.

The age display can be calculated when the table renders. The app already refreshes the table when fresh API data arrives, so a separate once-per-minute UI timer is out of scope for this first version.

## Error Handling

Parsing bad `spotTime` values should fall back to `None` for that field. The row should still render with a blank age cell. If the local clock is behind the spot timestamp, clamp the age to `0m`.

## Testing

Add tests for:

- parsing `spotTime` into a timezone-aware UTC `datetime`.
- preserving otherwise valid spots when `spotTime` is missing or invalid.
- formatting compact age values for minute and hour ranges.
- rendering the new `Age` column as the leftmost table column.
- sorting visible rows with the freshest spots first.
- keeping keyboard/action column behavior intact after the column insertion.
