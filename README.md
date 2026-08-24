# Agent's Player to Club Model

A Streamlit application that helps football agencies find realistic transfer destinations for
their players. Given an agency (or the pool of unrepresented players), it filters by age,
position, and nationality, then returns ranked club recommendations with a plain-language
explanation for each match.

## What it does

- **Choose a population** — a specific agency, or players without an agency.
- **Filter** — age, position, nationality.
- **Select players** — one, several, or all matching players.
- **Get recommendations** — an initial Top 3 per player, expandable to Top 6 and Top 9, each
  showing a Match % and a written explanation of why the club fits.
- **Additional Match** — a further, clearly-labelled recommendation shown only when a player
  qualifies for one, in addition to their regular Top 9.
- Nationality and destination country/league are each shown with a local flag icon; no player
  photos or club badges are used anywhere in the app.
- A **Leagues Covered** section on the opening screen lists every country/league in scope.

## Run locally

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

Run from the project root. All paths the app uses are resolved relative to the repository itself
— no machine-specific configuration is required.

## Project structure

```
dashboard/                          Streamlit application (entry point: app.py)
  app.py                            Page flow / rendering
  app_config.py                     Paths and UI constants (relative, no local machine paths)
  data_loader.py                    Cached loading of the production data layer
  selection_logic.py                Agency/filter/player-selection logic
  results_view.py                   Recommendation cards, explanations, Additional Match
  nationality_flags.py              Local SVG flag rendering (no external image service)
  league_coverage.py                "Leagues Covered" section
  assets/flags/                     Local SVG flag assets

production/recommendation_engine/results/
                                     Precomputed, production data the app reads at runtime
                                     (players, recommendations, explanations, league coverage).
                                     This data is generated offline by the modeling pipeline
                                     under production/ — the deployed app only reads it.

production/                         Modeling pipeline (data preparation, scoring, evaluation)
                                     that produces the data above. Not required to run the app
                                     itself once the data files exist.

tests/                               Test suite (pytest)
docs/                                Internal engineering documentation
```

## Requirements

Runtime dependencies only (`requirements.txt`): `streamlit`, `pandas`, `numpy`. The app opens no
database connection and requires no API keys or other runtime secrets.

## Tests

```bash
pytest
```
