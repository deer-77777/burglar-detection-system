# Operator Guide

A page-by-page reference for staff using the Burglar Detection dashboard. If
you're looking for how to deploy the system instead, see the top-level
[README.md](../README.md).

---

## Contents

1. [First login](#1-first-login)
2. [Top navigation](#2-top-navigation)
3. [Dashboard](#3-dashboard)
4. [Cameras](#4-cameras)
5. [Groups](#5-groups)
6. [History](#6-history)
7. [Users](#7-users)
8. [Glossary](#8-glossary)

---

## 1. First login

The first time anyone signs in to a freshly deployed system, the credentials
are:

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin` |

You will be **forced to change the password immediately** — the default
credentials cannot be restored once changed. Pick a strong password (at least
8 characters; the form blocks shorter ones).

If you mistype your password 5 times within 5 minutes the account is locked
for 15 minutes. Wait it out or ask another administrator to reset it.

---

## 2. Top navigation

The bar across the top of every page contains:

| Item | Visible when | Purpose |
|---|---|---|
| Dashboard | Always | Live grid of camera feeds and active alerts. |
| Cameras | Has **Manage cameras** permission | Add, edit, delete cameras. |
| Groups | Has **Manage groups** permission | Edit the Store/Floor/Section tree and attach cameras. |
| History | Always | Browse past Dwell and Revisit events. |
| Users | Has **Manage users** permission | Create accounts and grant permissions. |
| EN / JA | Always | Switch UI language between English and Japanese. |
| Log out | Always | End your session. |

Items are hidden — not just disabled — for users without the matching
permission, so the workspace stays focused.

---

## 3. Dashboard

A grid of live camera cards. Each card shows the camera name, its group path
(e.g. *Store A / Floor 1 / Cosmetics*), a coloured status dot, and a status
chip on the right.

### Status colours

| Colour | State | Meaning |
|---|---|---|
| 🟢 Green | **Live** | Stream is open, detection is running. |
| 🟡 Yellow | **Reconnecting** / **Pending** | Worker has lost the stream and is retrying with backoff, or just started up. |
| 🔴 Red border | **Alert** | An event was raised on this camera in the last few seconds. |
| 🔴 Solid red dot | **Error** | Stream could not be opened — bad URL, auth failure, or network problem. Check the camera's connection log. |
| ⚫ Grey | **Disabled** | "Display on dashboard" is turned off for this camera. The worker has stopped decoding to save resources. |

### Filter and sort controls

| Control | Effect |
|---|---|
| **Store** | Show only cameras under the chosen Store. `*` shows all. |
| **State** | Show only cameras in a specific status (live / reconnecting / error / disabled). |
| **Recent events only** | Show only cameras that have triggered an event since you opened the page. Useful when watching for incidents. |
| **Sort by – Name** | Alphabetical by camera name (default). |
| **Sort by – Group path** | Sort by *Store / Floor / Section* path so cameras group together physically. |
| **Sort by – Last event** | Most recently active first — surfaces the cameras that need attention. |
| **Sort by – Alerts today** | Highest number of events first. |

### Workflow tips

- A red border on a card means a Dwell or Revisit just fired. Click through to **History** to review the snapshot and clip.
- Use **Sort by – Alerts today** at the start of a shift to see hot spots.
- Turning off a card from **Cameras → Display on dashboard** stops decoding entirely on the server, freeing CPU/GPU. Turn it back on later without losing camera config.

---

## 4. Cameras

Lists all cameras you can see and lets you add, edit, or delete them. Requires
the **Manage cameras** permission.

The page has two halves:

- **Left:** the existing camera list (Name, Resolution, Group, action icons).
- **Right:** the **Add camera** / **Edit** form.

### Camera fields

| Field | Default | What it does |
|---|---|---|
| **Name** | `Camera` | Display name on cards and tables. Must be unique within the same Group. Max 128 chars. |
| **RTSP URL** | (none) | The camera stream URL. Must start with `rtsp://` or `rtsps://`. May contain credentials, e.g. `rtsp://admin:Sup3rSecret!@192.168.1.42:554/stream1`. **Stored encrypted** — never appears in plaintext after save. |
| **W × H** (Resolution) | `1920 × 1080` | The resolution to expect from the camera. The Test Connection step verifies the camera actually delivers this; mismatch fails the save. Range 16–7680. |
| **Group** | — (Unassigned) | Which Store / Floor / Section node the camera belongs to. Drives Dashboard filtering, History `group_path`, and (most importantly) the ReID gallery scope — the system tries to recognise the same person across cameras within the same Store. Can be changed later from this form **or** the Groups page. |
| **Dwell limit (seconds)** | `180` (3 min) | Trigger a **Dwell** event when the *same* person has been continuously visible to *this* camera for at least this many seconds. Lower = more sensitive (more events). |
| **Appearance count limit** | `3` | Trigger a **Revisit** event when the same person has been seen by this camera at least N separate times within the rolling window below. |
| **Window (seconds)** | `86400` (24 h) | The rolling window the appearance count is measured over. A person who walked past 3 times in 25 hours doesn't trigger; 3 times in 23 hours does. |
| **Display on dashboard** | On | When off, the dashboard shows a *Disabled* placeholder and the worker stops decoding/inferring on this camera. Use to silence cameras temporarily without deleting them. |

### Add a camera

1. Fill in **Name**, **RTSP URL**, optionally adjust resolution / group / thresholds.
2. Click **Test connection**. The system probes the URL and decodes one frame within ~5 seconds.
3. If the test succeeds you'll see a green *Connection OK (1920×1080)* message; **Save** becomes enabled.
4. If it fails, you'll see one of these messages — fix the cause and re-test:

| Message | Probable cause |
|---|---|
| Authentication failed | Wrong username/password in the URL. |
| The camera could not be reached | IP unreachable, or wrong port. |
| The camera did not respond in time | Camera is too slow or behind a firewall/VPN. |
| The stream path is invalid | The path after the host is wrong. Try the camera vendor's "main stream" URL. |
| The camera's codec is not supported | Switch to H.264 in the camera's web UI. |
| The configured resolution does not match | The camera reports something other than what you typed in W×H. Update W×H to match. |

5. Click **Save**. The camera appears in the list and a worker starts processing it within seconds.

### Edit / delete

- Pencil icon → loads the row into the form for editing. Leave **RTSP URL** blank to keep the existing one (it's encrypted, so the form doesn't redisplay it).
- Trash icon → confirms then removes. All connection logs and **events for that camera** cascade-delete with it. Use *Display on dashboard = off* if you only want to silence, not destroy.

---

## 5. Groups

Groups model the physical layout: **Store → Floor → Section**, three levels
deep. Cameras can be attached at any level.

The page has two halves:

- **Left:** the tree of groups with attached cameras nested below each node.
- **Right:** the *Add / Rename* form, plus an *Unassigned cameras* panel.

### Tree node

| Element | Meaning |
|---|---|
| **Level chip** (Store / Floor / Section) | Where this node sits in the hierarchy. |
| **Group name** | The display name. |
| **Camera count chip** | If non-zero, how many cameras live directly under this group (excludes its descendants). |
| **Pencil** | Rename / change parent. |
| **Trash** | Delete the group. Cameras under it are *unassigned*, not deleted. |

Indented under each group are its attached cameras (📹 icon + name) with:

- **Move to…** — pick another group to relocate the camera.
- **Detach** (broken link icon) — sets the camera's group to *Unassigned*.

### Add / Rename form fields

| Field | What it does |
|---|---|
| **Title heading** | Changes based on the parent — *Add store* (no parent), *Add floor* (parent is L1), *Add section* (parent is L2). |
| **Name** | Display name. Required, 1–128 chars. |
| **Parent** | The parent group. Choose *No parent (top-level store)* to create a Store. Section-level groups (L3) cannot have children, so they don't appear in this dropdown. |

### Unassigned cameras panel

Lists every camera with no group set. Each row has an **Attach to…** dropdown
— pick a group and the camera moves there immediately.

### Workflow tips

- Build the hierarchy *before* adding many cameras: `Store A → Floor 1 → Cosmetics`. Then assigning cameras is just a single dropdown choice.
- Renaming a group does **not** rewrite past events — they keep the path snapshot from when they fired (so historical reports stay accurate).
- A group can be reassigned to another parent (move *Cosmetics* from *Floor 1* to *Floor 2*). The level recalculates automatically. You cannot move a deeper subtree under a node that would push it past 3 levels.

---

## 6. History

Lists all Dwell and Revisit events. The default date range is the **current
month** (1st of this month 00:00 → last day of this month 23:59).

### Filters

| Filter | What it does |
|---|---|
| **Date range (start / end)** | Restrict to events whose start time falls in this range. Picker uses your local time. |
| **Event type** | *Dwell* (person stayed too long) or *Revisit* (person showed up too many times). `*` shows both. |
| **Status** | Review state — *New*, *Reviewed*, *False positive*, *Escalated*. See the table further down. |
| **Person ID** | Exact match on the ReID-assigned person identifier (a 16-char hex string). Useful to track all events caused by the same suspected individual. |
| **Notes contain…** | Substring match in the *Notes* field operators have written. |

### List columns

| Column | Notes |
|---|---|
| **Time** | When the threshold was crossed. |
| **Camera** | Path captured at event time, e.g. *Store A / 1F / Cosmetics*. Survives later renames. |
| **Type** | *Dwell* or *Revisit*. |
| **Person** | The ReID-assigned global ID. The same person crossing thresholds on different cameras / different days will (usually) carry the same ID. |
| **Detail** | For Dwell: how long they stayed (`180s`). For Revisit: how many times in the rolling window (`×4`). |
| **Status** | Review state — see the next table. |

### Review states

| Status | Meaning | Set when |
|---|---|---|
| **New** | Default. No human has looked at it yet. | Auto, on every event. |
| **Reviewed** | An operator watched the snapshot/clip and acknowledged it. No further action. | After confirming a long-browsing customer or staff member. |
| **False positive** | The event should not have triggered. Useful signal for tuning. | E.g. ReID merged two different people, mannequin/poster, legitimate pause. |
| **Escalated** | Push up the chain — supervisor, security, or police. | Suspected theft or repeat offender. |

### Detail dialog

Click any row → a dialog opens with:

- **Snapshot** — a JPEG captured at the moment the threshold was crossed.
- **Clip** — a 10-second MP4 covering the moments before and after the event, dumped from the worker's in-memory ring buffer.
- **Review status** dropdown.
- **Notes** free-text box (searchable later via the Notes filter).
- **Save** — records your changes and stamps your user ID as the reviewer.

### Workflow tips

- Default view = current month, sorted newest first. Drill in by Camera or Person ID to investigate a pattern.
- Mark *False positive* aggressively when the system trips on customers who legitimately browse — the metric is helpful for managers reviewing detection accuracy.
- *Escalated* events are typically the input to physical security or police reports. Keep notes detailed enough to stand alone.

---

## 7. Users

Lists every user account. Requires **Manage users** permission.

### User fields

| Field | What it does |
|---|---|
| **Username** | Login name. Unique. 3–64 characters. Cannot be changed after creation — delete and recreate if you need to rename. |
| **Password** | Login password. 8–128 characters. Required when creating; leave blank when editing to keep the existing password. Stored as a bcrypt hash; never recoverable in plaintext. |
| **Language** | Default UI language for this user (EN or JA). They can still switch on the fly using the top-right selector. |
| **Manage users** | Can create, edit, delete users and grant permissions. The first admin has this permission. Be sparing — anyone with this can lock you out. |
| **Manage groups** | Can edit the Store/Floor/Section tree and attach cameras to groups. |
| **Manage cameras** | Can add, edit, delete cameras and run RTSP test-connection. |
| **Visibility** (collapsible) | Restricts which Stores / Floors / Sections / individual cameras this user can see on the Dashboard and in History. Selecting a Store implicitly grants visibility on every Floor / Section / camera below it. Leave empty to grant nothing — useful for an "auditor" who only needs explicit cameras. |

### Common patterns

| User role | Permissions | Visibility |
|---|---|---|
| **Store administrator** | Manage groups, Manage cameras | All Stores they administer. |
| **Loss-prevention operator** | (none — view-only) | The cameras they monitor. |
| **Regional auditor** | (none) | Multiple Stores via the Stores checkbox. |
| **System administrator** | Manage users + groups + cameras | All (no visibility filter applied for full admins). |

### Visibility behaviour

- A user with **all three** management permissions plus admin defaults sees everything (no visibility filter applied).
- Otherwise they see only the cameras under the groups/cameras explicitly checked in the Visibility section.
- Selecting a parent automatically covers descendants — picking *Store A* gives access to every Floor and Section below.
- The **History** page is filtered to events from cameras they can see.

### Workflow tips

- Create one *normal-user* account per person, never share logins. Audit logs identify the user, so shared accounts make incident attribution impossible.
- Grant *Manage users* to at most 2-3 trusted people per deployment; rest of the team should be *Manage groups + Manage cameras* at most.
- Use the **Visibility** Accordion to scope a junior operator to a single Store — they never see other locations' cameras or events.

---

## 8. Glossary

- **Dwell event** — A single person stayed continuously visible to *one* camera longer than that camera's *Dwell limit*. Default 3 minutes.
- **Revisit event** — A single person was seen by *one* camera at least N separate times inside the rolling window. Default: 3 visits within 24 hours.
- **Person Global ID** — A long-lived 16-character ID assigned by the ReID model. The same physical person keeps this ID even after walking out of frame and back in, **across cameras within the same Store**, for up to 24 hours of inactivity.
- **Group path** — The breadcrumb from Store down through Floor to Section, e.g. *Store A / Floor 1 / Cosmetics*. Captured at event time so historical reports stay accurate even if you later rename groups.
- **RTSP** — *Real Time Streaming Protocol*. The standard streaming protocol used by virtually all IP cameras.
- **Ring buffer** — A short rolling window of raw camera frames the worker keeps in memory (default 10 s). When an event fires, the surrounding frames are dumped to disk as the event's *Clip*.
- **ReID** — Re-identification. The process of matching a freshly-tracked person against a recent gallery to decide whether they're someone we've already seen.
