# Event Manager

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Home Assistant integration that creates sensors for upcoming events – birthdays, anniversaries, and one-time events.

![Example dashboard with upcoming events](images/dashboard-example.png)


## Maintainer and credits

- Maintainer / app developer: [@allanpersson](https://github.com/allanpersson)
- Original developer: [@CagosDk](https://github.com/CagosDk), credited for the original Event Countdown integration this project is based on.

## Versioning and build numbers

This project uses Semantic Versioning plus a monotonically increasing build number: `MAJOR.MINOR.PATCH+build.N`. The current build metadata is stored in `build.json`, and every future code, documentation, or packaging change must increment the build number.

## Installation via HACS

1. Add this repository as a **Custom Repository** in HACS (category: Integration)
2. Find "Event Manager" in HACS and install
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration** and search for "Event Manager"

## Configuration

The integration is configured entirely through the UI, with two kinds of entries:

### Global Configuration

Created automatically the first time the integration is added. Use its **Configure** button to set:

- **Language** – language used for each sensor's `full_name` text:
  - **Automatic** (default) – follows the language configured in Home Assistant (Settings → System → General)
  - **English**
  - **Dansk**

### Events

Add one entry per event via **Add Integration → Event Manager**. Each event has its own **Configure** / **Delete** actions and the following fields:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Name of the event |
| `day` | Yes | Day (1-31) |
| `month` | Yes | Month (1-12) |
| `year` | No | Birth year / wedding year — used to calculate age |
| `type` | Yes | `birthday` (default), `anniversary`, or `event` |
| `soon` | Yes | Days before the event is marked as "soon" (default: 30) |
| `picture` | No | Path to image, e.g. `/local/pic/name.jpg` |
| `recurring` | Yes | On = repeats every year. Off = skipped once the date has passed (default depends on `type`) |
| `disabled` | Yes | On = the event is ignored until re-enabled |
| `delete_after_occurrence` | Yes | On = the event (and its configuration entry) is removed automatically the day after it occurs |

### Event types and how they're displayed

The `full_name` attribute is built differently depending on the event `type`. With **English** as the language:

| Type | Example `name` | Example `full_name` |
|------|-----------------|----------------------|
| `birthday` | `Mom's birthday` | *"Mom's birthday in 14 days"* (no `year` set) |
| `birthday` (with `year`) | `Mom's birthday` | *"Mom turns 46 in 14 days"* |
| `anniversary` | `Wedding anniversary` | *"Wedding anniversary in 5 days"* (no `year` set) |
| `anniversary` (with `year`) | `Wedding anniversary` | *"10 year wedding anniversary in 5 days"* |
| `event` | `Summer holiday` | *"Summer holiday in 60 days"* |

With **Dansk** as the language, the same events would show:

| Type | Eksempel `name` | Eksempel `full_name` |
|------|------------------|------------------------|
| `birthday` | `Mors fødselsdag` | *"Mors fødselsdag om 14 dage"* (uden `year`) |
| `birthday` (med `year`) | `Mors fødselsdag` | *"Mors 46 års fødselsdag om 14 dage"* |
| `anniversary` | `bryllupsdag` | *"bryllupsdag om 5 dage"* (uden `year`) |
| `anniversary` (med `year`) | `bryllupsdag` | *"10 års bryllupsdag om 5 dage"* |
| `event` | `Sommerferie` | *"Sommerferie om 60 dage"* |

For `birthday`, the word "birthday" / "fødselsdag" is stripped from `name` before building `full_name`, so it doesn't appear twice.

- **`birthday`** – repeats every year by default, calculates age automatically
- **`anniversary`** – repeats every year by default, calculates the number of years automatically
- **`event`** – one-time by default, skipped once the date has passed (unless `recurring` is enabled)

The integration recomputes the upcoming events every hour, and whenever an event is added, edited, or removed.

## Sensors

The Global Configuration entry creates one stable sensor for each event entry you add. Sensors are no longer limited by a fixed slot count, and each sensor stays bound to its own event so attributes and friendly names cannot be mixed with data from another event.

- **State** – `true` if this event is within its `soon` threshold (i.e. it should be displayed), otherwise `false`. Use this to control card visibility (see below).
- **Attributes:**
  - `full_name` – human-readable text, e.g. *"Mors 46 års fødselsdag om 14 dage"*
  - `name` – event name
  - `type` – event type
  - `age` – calculated age / anniversary number
  - `days_remaining` – days remaining
  - `soon` – `true` if within the threshold (same value as the state)
  - `soon_threshold` – threshold in days
  - `event_date` – original event date (YYYY-MM-DD)
  - `entity_picture` – path to image, only set if a `picture` was configured for the event

If an event is disabled or a non-recurring event has passed, its sensor shows state `false` and `full_name: "No event"` (or `"Ingen begivenhed"` in Danish).

If no `picture` is configured for an event, `entity_picture` is left empty and the entity's icon is set to `mdi:calendar-clock`.

## Showing `full_name` on a dashboard

By default, a sensor card shows the entity's *state* (`true`/`false`) and its picture/icon. To show the human-readable `full_name` text instead:

1. Add the sensor to a dashboard (e.g. a **Tile** card or **Entities** card) and open its settings (pencil icon → **Edit** or the entity's "Visual settings" / *"Mærkatindstillinger"*).
2. Under **Content**, enable **Show entity picture** if you want the event's image displayed.
3. Under **State**, choose which attribute to display:
   - For the **Tile** card: set *"Show information for"* / *"Tilstandsoplysninger"* to **Full name** instead of the default state.
4. Repeat for `Tilstand` (state) / `Ikon` (icon) as desired — these can be toggled independently.

This way the card displays text like *"Mors 46 års fødselsdag om 14 dage"* together with the event's picture, instead of the raw `true`/`false` state.

## Hiding cards for events that aren't "soon"

Because the sensor's state is `true`/`false`, you can add a **visibility condition** to a card so it's only shown when the event is within its `soon` threshold:

1. Edit the card → **Visibility** (*"Synlighed"*) → **Add condition** (*"Tilføj betingelse"*).
2. Choose **Entity state** (*"Entitetstilstand"*), select the event's sensor entity, leave **Attribute** empty, and set **State equals** (*"Tilstand er lig med"*) to `true`.

The card is then hidden automatically whenever that event is not within its "soon" threshold.

