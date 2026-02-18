# Farm Trial Manager

A web app for planning and visualizing agricultural research trials. Manage trials, treatments, plots, traits, and measurements with a map-based layout view.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Google Maps API key

In `templates/layout.html`, replace `YOUR_API_KEY` with a valid Google Maps JavaScript API key. The map view will not render without a valid key, but all other functionality works independently.

### 3. Initialize the database and run

The SQLite database is created automatically on first run:

```bash
python app.py
```

The server starts at `http://localhost:5000`.

## Project structure

```
app.py              Flask application entry point with all routes
models.py           SQLAlchemy database models
requirements.txt    Python dependencies
templates/          Jinja2 HTML templates
  base.html         Base layout with navbar
  index.html        Trial list (home page)
  trial_form.html   Create/edit trial
  trial_detail.html Trial detail with all sections
  block_form.html   Create/edit site block
  treatments.html   Manage treatments
  generate_plots.html  Generate randomized plot layout
  traits.html       Manage traits
  measurements.html Enter measurement data
  layout.html       Google Maps layout view
  summary.html      Analytics summary with bar chart
static/
  style.css         Stylesheet
  layout.js         Google Maps plot overlay logic
```

## Workflows

1. **Create a trial** — define name, year, crop category, PI
2. **Add a site block** — rectangular area on the farm with lat/lng, dimensions, rotation
3. **Define treatments** — the experimental treatments to compare
4. **Generate plots** — randomized assignment of treatments to a grid of plots within a block
5. **View layout** — see plots on a Google Maps satellite view, colored by treatment or trait value
6. **Define traits** — measurable characteristics (numeric, rating, categorical, text)
7. **Enter measurements** — record values per plot for a given trait and date
8. **View summary** — treatment means, standard deviations, and bar chart
9. **Export CSV** — download measurements or layout as CSV for analysis in R/SAS
