# Casualty checks: manual test checklist

For: Najdi. This is a copy of the real data with all the casualty work applied. Nothing you do here
touches the real database, so feel free to click everything.

## 1. Getting in

| What | Where |
|---|---|
| Website (use this) | http://localhost:5175 |
| Backend (only if you want to look at the API) | http://localhost:8002 (health: http://localhost:8002/health, API docs: http://localhost:8002/docs) |
| Database (read only, for checks) | localhost:5435, database `war_news_casualty_test`, user `postgres`, password `casualty_test` |
| Login | `casualty_test_admin` / `CasualtyTest!2026` (super admin, exists only in this test copy) |

Run these from the repository folder in PowerShell:

```powershell
# start (if it is stopped)
docker compose -f docker-compose.casualty-test.yml up -d
# stop (keeps the data)
docker compose -f docker-compose.casualty-test.yml stop
# put the data back to the starting state (see section 5)
powershell -ExecutionPolicy Bypass -File scripts\rollout\reset_scratch.ps1
```

This test copy has no Telegram, CNRS or AI workers, so no new news arrives while you test.
Flags show up at once here (the real site waits 2 hours before showing a new flag).

**Starting numbers** (Incidents page, default dates 20 Aug 2026 to today):
Matching incidents 1,378. Needs verification 42 (3 duplicates, 18 missing number, 22 aggregate
toll; one incident has two checks). Reported casualties 48.

## 2. The 12 test incidents

Open an incident directly with `http://localhost:5175/superadmin/incidents/<id>`, or find it on the
Incidents page with the Village filter and the date.

| # | What it is | Incident id | Village | Event date | What you should see |
|---|---|---|---|---|---|
| 1 | Aggregate toll, bulletin 32095 (3 deaths, 23 injured over 5 places) | b1097a42-47f4-43e1-9ff5-1cf89cd01cf9 | Rmadiye | 4 Sep 2026 | "Needs verification" badge, "Aggregate toll" chip, reason "Total of 3 deaths and 23 injuries reported across …" |
| 2 | Same bulletin | baf456b2-2089-4ec1-8e36-5efa17e3d5c2 | Kfar Roummane | 4 Sep 2026 | Same badge, chip and reason |
| 3 | Same bulletin | 14e7607c-0683-4ce6-a61e-f14a518d5734 | Mayfadoun | 4 Sep 2026 | Same badge, chip and reason |
| 4 | Missing number: «شهيد وعدد من الجرحى» | 78145585-421c-4c24-8c04-dbf701cb7bcb | Rmadiye | 4 Sep 2026 | "Missing number" chip, reason quotes the Arabic sentence |
| 5 | Missing number: «وتسجيل إصابات» | b8b041c7-ecfc-457d-9c45-8936a1e28d6e | Rmadiye | 4 Sep 2026 | "Missing number" chip |
| 6 | Duplicate | b0e6b1e4-01dd-4a82-874d-ca75f2046157 | Mansouri Sour | 11 Sep 2026 | "Possible duplicate" badge, "Duplicate" chip, reason "Possible cross-source duplicate segment …", button "Resolve duplicate" |
| 7 | Duplicate with no saved reason | 44f26eb7-fcf2-43c1-a7e8-dfeac1a5b06e | Nabatiyeh El-Faouka | 7 Sep 2026 | "Duplicate" chip, reason "Possible duplicate of another incident" |
| 8 | Single place, exact numbers (must NOT be flagged) | 9f5855d0-e7ff-4a68-b706-4d6b79a137b4 | Kfar Roummane | 7 Sep 2026 | 1 death, 2 injured, no badge, no chip, no Casualty check card |
| 9 | Obituary style, one named death «الشهيدة إسراء بهجة … إرتقت» (must NOT be flagged) | 5105bf71-96b0-4853-b3b5-f494017e60d9 | Jibchit | 6 Sep 2026 | 1 death, no badge, no Casualty check card |
| 10 | Dual word «شهيدان» (must NOT be flagged) | b2e88fe2-0407-4b48-87be-f2ad13535e73 | Kfar Roummane | 4 Sep 2026 | No badge, no Casualty check card (note: the number 2 is not stored yet; known issue) |
| 11 | Already resolved (bulletin 31863) | 219cd4f5-4f0e-4cce-a0c6-777afd23e1a3 | Nabatieh Et-Tahta | 5 Sep 2026 | 1 death, 3 injured, not in "Needs verification", no Casualty check card |
| 12 | Outside the default dates | 0b2067c7-0bcb-4a23-9af3-8cc348ef2f8e | Mayfadoun | 19 Aug 2026 | Not in the list until you set From to 19 Aug or earlier |

Extra: **8bf5fa89-00a6-4e87-923c-388c4b707443** (Kfar Roummane, 5 Sep 2026) has two checks at once:
"Missing number" and "Aggregate toll".

No flagged incident is older than 20 Aug in this data, so the "more flagged incidents outside this
date range" notice only shows when you narrow the dates yourself (scenario C).

## 3. Scenarios

Tick Pass or Fail and write what you saw if it failed.

### A. Needs verification list

| Step | Do this | You should see | Pass / Fail |
|---|---|---|---|
| A1 | Open Incidents. Set Verification = "Needs verification". | 42 results. Every row has the yellow "Needs verification" badge, at least one grey chip and a one-line reason. | |
| A2 | Look for incidents 1 to 7 and the extra one. | All are there. The extra one shows both chips. | |
| A3 | Look for incidents 8, 9, 10 and 11. | None of them are there. | |
| A4 | Read the three cards at the top. | Matching incidents 42, Needs verification 42. Reported casualties 10. | |
| A5 | Under the result count. | "42 results \| sorted by event date, newest first". | |

### B. Cards follow the filters

| Step | Do this | You should see | Pass / Fail |
|---|---|---|---|
| B1 | Clear filters. | Matching incidents 1,378, Needs verification 42, Reported casualties 48. "Clear filters" is hidden. The first card says "Total incidents". | |
| B2 | Village = Nabatieh. | Needs verification 2. Switch Verification to "Needs verification": exactly 2 rows. | |
| B3 | Clear, then tick "Show only incidents with casualties". | Matching 48, Needs verification 10. With Verification = "Needs verification": 10 rows. | |
| B4 | Clear, then set From 5 Sep and To 7 Sep. | Matching 374, Needs verification 26, casualties 39. | |

### C. Dates and the "outside this range" notice

| Step | Do this | You should see | Pass / Fail |
|---|---|---|---|
| C1 | Clear filters. | From = 20 Aug 2026, To = today. | |
| C2 | Verification = "Needs verification", then set From = 6 Sep 2026. | 20 rows, and a notice "22 more flagged incidents outside this date range" with a "Show all dates" button. | |
| C3 | Click "Show all dates". | From becomes 1 Jan 2000 and To 31 Dec 2100. 42 rows. The notice is gone. | |
| C4 | Set Verification back to "All verification states" and keep From = 6 Sep. | No notice (it is only for verification views). | |
| C5 | Set From = 19 Aug. | Incident 12 appears. | |

### D. Verified and All states

| Step | Do this | You should see | Pass / Fail |
|---|---|---|---|
| D1 | Verification = "Verified". | No rows here (nothing is verified in this copy). No row ever has a check chip. | |
| D2 | Verification = "All verification states". | Flagged rows still show their badge, chips and reason. | |

### E. Check type filter

| Step | Do this | You should see | Pass / Fail |
|---|---|---|---|
| E1 | Check type = Duplicate. | 3 rows (incidents 6, 7 and 5bebb17e). | |
| E2 | Check type = Missing number. | 18 rows, all with the "Missing number" chip. | |
| E3 | Check type = Aggregate toll. | 22 rows, all with the "Aggregate toll" chip. | |
| E4 | Keep Aggregate toll, set Verification = "Needs verification". | Still 22. With Verification = "Verified": 0. | |
| E5 | Look at the address bar, then reload the page. | `verification_type=…` and `verification_status=…` are in the address. After the reload the same filters and rows are there. | |
| E6 | Click "Clear filters". | Everything is reset, including Check type. The dates go back to 20 Aug to today. Rows per page stays as you set it. | |

### F. Pages and sorting

| Step | Do this | You should see | Pass / Fail |
|---|---|---|---|
| F1 | Clear filters, 50 per page. Click Next until the end. | 1,378 incidents over 28 pages, no row twice. | |
| F2 | Verification = "Needs verification", Date order = "Oldest to newest". | Still 42 rows. The first row is from 4 Sep. The note says "oldest first". | |
| F3 | Switch to 150 per page. | Same 42 rows, and you go back to page 1. | |

### G. Reviewing a casualty check

| Step | Do this | You should see | Pass / Fail |
|---|---|---|---|
| G1 | On incident 1 (Rmadiye) click Review. | The Casualty check window opens. It shows the Health Ministry bulletin with the key sentence highlighted, the 5 places with "Unknown" counts, totals 3 deaths and 23 injured, a form per place, Save and Dismiss. | |
| G2 | For Rmadiye only, type 1 death and 15 injured. Save. | A green "Resolved: Rmadiye." message. **The window stays open** on the other 4 places, and remaining now shows 2 deaths and 8 injured. | |
| G3 | Close the window and look at the list and cards. | Rmadiye has left the list. Needs verification 41, Reported casualties 49. Opening Rmadiye shows 1 death and 15 injured and no Casualty check card. | |
| G4 | Review Kfar Roummane and type too many deaths (for example 5). | Red "Assigned values cannot exceed the bulletin total", and Save is disabled. | |
| G5 | Fill the rest: Kfar Roummane 2 deaths, Mayfadoun 4 injured, Houmine El-Faouqa 3 injured, Aain Et-Tine 1 injured. Save. | The window closes. The four rows leave the list and Needs verification drops to 37. | |
| G6 | Open the extra incident (8bf5fa89) and click Review. | The first check opens. After you finish or dismiss it, the second one opens by itself. | |
| G7 | On its Missing number check, click Dismiss and leave the reason empty. | The Dismiss button stays disabled (needs at least 3 characters). | |
| G8 | Type a reason and Dismiss. | The row stays in "Needs verification" with only the "Aggregate toll" chip, and the count does not change. | |
| G9 | Open incident 11 (already resolved). Then open any flag you resolved in G2 (use the "Open incident" link in the window). | The saved values are shown read-only, with no form. | |

(Note: the bulletin names «النبطية الفوقا», but this location is stored as Houmine El-Faouqa. That
is a place-matching question in the data, not a problem with the check itself.)

### H. Incident detail page

| Step | Do this | You should see | Pass / Fail |
|---|---|---|---|
| H1 | Open incident 4 (78145585). | A "Casualty check" card with the Arabic sentence highlighted, current counts, the number boxes, "Confirm unknown", Save and Dismiss. | |
| H2 | Open incident 2 (Kfar Roummane, aggregate). | The card lists all places in the bulletin. | |
| H3 | Open incidents 8, 9, 10 and 11. | No Casualty check card. | |

### I. Duplicates still work as before

| Step | Do this | You should see | Pass / Fail |
|---|---|---|---|
| I1 | Incident 6: click "Resolve duplicate". | The incident page with the duplicate comparison and the usual choices. | |
| I2 | Resolve it as "not a duplicate". | It leaves "Needs verification", and the Duplicate count drops by 1. | |

### J. Hidden low-confidence rows

About 405 older incidents are stored as "needs verification" only because the village match was
unsure. They are hidden on purpose for now.

| Step | Do this | You should see | Pass / Fail |
|---|---|---|---|
| J1 | Verification = "Needs verification". | Still only the 42 flagged or duplicate rows. None of the 405 appear. | |

### K. Empty, loading and error

| Step | Do this | You should see | Pass / Fail |
|---|---|---|---|
| K1 | Village = "zzzz". | "No matching incidents" with a hint to clear filters. All three cards show 0. | |
| K2 | Reload the page on a slow network (DevTools, "Slow 3G"). | A loading table, then the rows. | |
| K3 | Run `docker compose -f docker-compose.casualty-test.yml stop backend`, then reload. Start it again with `... start backend`. | "Could not load incidents" while it is stopped. The list comes back after the restart. | |

## 4. When you find a problem

Write down the incident id, what you clicked and what you saw. A screenshot helps.

## 5. Starting over

`scripts\rollout\reset_scratch.ps1` stops the test backend, drops and rebuilds `war_news_casualty_test`
from `backups\scratch\war_news_casualty_test_baseline.dump`, starts the backend again and resets the
test login. It refuses to run against any other database name. It takes about a minute.

`-RerunScripts` only re-runs the migrations and the four casualty scripts and keeps what you
resolved by hand.
