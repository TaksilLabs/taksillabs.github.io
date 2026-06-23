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

## Updating rosters

run this from .\SPLStats
py tools/live/active_roster_editor.py



## Shot Maps

run this from .\SPLStats
py tools\live\shot_map_editor.py



## Changing Team Themes

run this from .\SPLStats
py tools\team_theme_builder.py



## Live Tools

Both these start with New Terminal -> cd SPLStats

To change active rosters:
py tools\live\active_roster_editor.py

When adding a new log run:
py tools\live\build_preseason.py



## Making Articles

run this from .\SPLStats
py tools\news_article_builder.py