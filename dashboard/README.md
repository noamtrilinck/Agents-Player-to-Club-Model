# Player Recommendation Search — Streamlit App

Stage 7, Sprint 7.2. Agency/player selection and filtering only — recommendation results are
built in Sprint 7.3.

## Run

```
pip install -r requirements.txt
streamlit run dashboard/app.py
```

Run from the project root (or any directory — paths inside the app are resolved relative to
`dashboard/config.py`'s own file location, not the working directory).

## Structure

- `app.py` — the Streamlit page (rendering only; contains no filtering logic of its own).
- `selection_logic.py` — pure Python/pandas agency/filter/selection logic, framework-independent
  and unit-tested directly (`tests/test_dashboard_selection_logic.py`).
- `data_loader.py` — cached (`st.cache_data`) loading of the Sprint 7.1 production data layer.
- `app_config.py` — relative paths and UI constants (no machine-specific paths; named
  `app_config` rather than `config` deliberately, to avoid colliding with the many other
  stage-specific `config.py` modules elsewhere in this project when running under pytest).

## Data source

Reads only `production/recommendation_engine/results/players.csv` and `recommendations.csv` (the
locked Sprint 7.1 data layer). Never queries research outputs, never opens a database connection
at runtime, never recomputes agency/player/recommendation methodology.

## Tests

```
pytest tests/test_dashboard_selection_logic.py tests/test_dashboard_app_smoke.py -v
```

`test_dashboard_app_smoke.py` uses Streamlit's official headless testing API
(`streamlit.testing.v1.AppTest`) to drive the real app end-to-end without a browser.
