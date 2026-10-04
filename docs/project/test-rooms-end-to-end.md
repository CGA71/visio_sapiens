# Test end to end — declaring a house, and taking it back

What this proves: that the navigation rail tells the truth from every screen,
after rooms are added and after they are removed. That is the one thing that
kept breaking, because the rail is rendered INTO each dashboard file and
`home.yaml` is the file the routine generator never rewrites.

Run against the staging appliance, `http://192.168.1.200:8123`, in English.

## Before

The instance must have no rooms and no floors. The rail should read HOME,
ADMIN and nothing else. If it does not, run part 4 first.

Entities the scenario needs, by friendly name:

| Needed | On this appliance |
|---|---|
| `switch` named *Cave à vin* | `switch.shellyplugmg3_70af09e57f84` |
| `switch` named *Jessica Outlet* | `switch.shellyplugmg3_08927259dfd8` |
| cameras named `DS-CAM-*` | **none — see the note at the end** |

## 1. Declare the house

1. Open `/visio-sapiens-admin/menu`.
2. **ROOMS & FLOORS**.
3. Add a floor: **Ground Floor**.
4. Add three rooms on it: **Entrance Hall**, **Kitchen**, **Living Room**.
5. Entrance Hall → template **entrance**, priority slot **security**.
6. Kitchen and Living Room → template left at its default, priority slot
   **appliances**.
7. Apply.

## 2. Assign the devices

8. **DETECTED DEVICES → DEVICE ASSIGNMENT** (or the console menu).
9. Every `DS-CAM-*` camera → **Entrance Hall**, slot **security**.
10. *Cave à vin* → **Kitchen**, slot **switches**.
11. *Jessica Outlet* → **Entrance Hall**, slot **switches**.
12. **Save and generate**.

## 3. What has to be true

- The left rail lists **Entrance Hall, Kitchen, Living Room**.
- It lists them **from every screen**: HOME, the ADMIN menu, and a room page.
  This is the check that matters - the rail is baked into each file, so one
  screen can be right while another is a week behind.
- The whole flow ran **in English**: the form's own labels, and the template
  and slot pickers of each room.

## 4. Take it back

13. Return to **ROOMS & FLOORS**, delete the three rooms and the floor, apply.
14. The rail must read **HOME and ADMIN**, and nothing else, from every screen.

## Run of 5 October 2026 — passed

Driven with Playwright against the appliance, version `dev-485f131b`.

| Step | Result |
|---|---|
| Floor + 3 rooms, templates and slots | written as asked |
| Apply | `house.yaml` 0 -> 3 rooms, **home.yaml rebuilt in the same pass** |
| The 3 `DS-CAM-*` and the 2 switches assigned | saved to the right slots |
| Save and regenerate | every view rebuilt, `home.yaml` included |
| Rail on HOME, on a room page, in ADMIN | the three rooms, everywhere |
| Entrance Hall | Jessica Outlet under Switches, the three cameras live in the Security mosaic |
| Delete everything, Apply | `house.yaml` back to 0, rail back to HOME + ADMIN |

The cameras proved the point they were there to prove. Their entity ids carry
nothing - `camera.nvr_expanse_canal_1`, `_2`, `_3` - and only their friendly
names follow the nomenclature. They appear named **Garage**, **Garden** and
**Outside**, which is the friendly-name branch of the match doing the work
through the discovery report. Matching on the id alone would have found none
of them.

The rail still carries CORE and ENERGY after the deletion. That is correct:
those two dashboards exist on this box. Only rooms go away with the rooms.

### Two defects found by this run, both fixed

**The floor was named in French on an English console.** `+ Floor` pushed
`Rez-de-chaussée` whatever the interface language, so an English house had to
rename its first floor by hand. It now follows the language.

**The wizard's first screen was French whatever the console said.** The page
reads the language from `input_select.vssp_language` over the websocket, and
the websocket needs a token - so the screen that ASKS for the token could
never know the language. The console now passes `?lang=` on the iframe url,
as it already did for the Google and AI wizards, and both wizards read it at
load. The websocket still wins the moment it answers.

### What this run could not prove

`Delete all` clears the draft; the deletion reaches Home Assistant on the
following **Apply**, like every other change in this form. The wording of its
prompt says "will be deleted from Home Assistant", which reads as immediate.
Not changed here - it is the form's own convention, stated at the top of
HOUSE STRUCTURE - but worth knowing when reading the test.

No restart was needed at any point: the room dashboards were already declared
in `configuration.yaml` from an earlier run, and the patcher never deletes, so
the merge had nothing to change. A first-ever room on a clean instance does
restart.
