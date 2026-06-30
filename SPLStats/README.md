When updating database make sure to run these

py build_lr_season.py
py build_all_time.py
py build_teams.py


2026-06-16 update

Note for Future Darth;
Should run these scripts, in this order:

python build_lr_season.py
python build_all_time.py
python build_career_totals.py
python build_franchises.py


// if team records are involved run:
python build_team_records.py
python build_teams.py


# ------------------------------------------
# IGNORE THE ABOVE IF NOT NAMED DARTHTAKSIL
# ------------------------------------------

This begins the REAL documentation, the above are ancient texts that are only meant to serve as reminders that they exist to their creators.




## LOCAL HOSTING THE SITE

Go to /SPLStats/
cd ~/Documents/DarthLabs/taksillabs.github.io/SPLStats

Run this command
python3 -m http.server 8000





## Updating rosters

run this from .\SPLStats
python tools/live/active_roster_editor.py





## Shot Maps

run this from ./SPLStats
python tools/live/shot_map_editor.py





## Changing Team Themes

run this from .\SPLStats
python tools/team_theme_builder.py





## Live Tools

Both these start with 
(on the top left action bar) `Terminal` -> `New Terminal`
->
cd SPLStats

To change active rosters:
python tools/live/active_roster_editor.py

When adding a new log run:
python tools/live/build_preseason.py





## Making Articles

run this from .\SPLStats
python tools/news_article_builder.py





# SEASON PREP 




## Regular Season




### Importing the Schedules

Import each division's .csv table from the scheduleboard.

    Make sure to set all the Team's Division and Conference.
        If there are no conferences leave blank.
    
    run `active_roster_editor.py` from the SPLStats root to do this.

Then (again) from /SPLStats/ run:
python tools/live/import_regular_schedule.py

This will generate the schedule.json for the whole league.

If team names have errors in the console, edit `SPLStats/data/live_season/summer_2026/team_aliases.json` then rerun the command.

After that runs without error, we can run:
python tools/live/update_regular_season.py

To set our division information.




### importing game logs

Run this single command
python tools/live/update_regular_season.py



What this command does:

1. Sort/copy incoming M1NNBot game-log folders into raw_live_logs/.../by_match/
python tools/live/import_incoming_regular_logs.py

2. Parse imported logs into matches.json + match_details/*.json
python tools/live/build_regular_matches.py

3. Build standings.json from schedule + completed matches
python tools/live/build_regular_standings.py

4. Build compact leaders.json / player stat rows
python tools/live/build_regular_leaders.py