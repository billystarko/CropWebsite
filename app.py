import csv
import io
import math
import random
import statistics
from datetime import date, datetime

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    Response,
    url_for,
)
from models import db, Measurement, Plot, SiteBlock, Trait, Treatment, Trial

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///farm_trials.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "dev-secret-key-change-in-production"

db.init_app(app)

with app.app_context():
    db.create_all()

CROP_CATEGORIES = ["vegetable", "fruit", "turf", "ornamental", "other"]
TRAIT_TYPES = ["numeric", "rating", "categorical", "text"]

# ---------------------------------------------------------------------------
# Home / Trial list
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    trials = Trial.query.order_by(Trial.year.desc(), Trial.name).all()
    return render_template("index.html", trials=trials)

# ---------------------------------------------------------------------------
# Trial CRUD
# ---------------------------------------------------------------------------

@app.route("/trials/new", methods=["GET", "POST"])
def trial_new():
    if request.method == "POST":
        trial = Trial(
            name=request.form["name"],
            year=int(request.form["year"]),
            crop_category=request.form["crop_category"],
            pi_name=request.form.get("pi_name", ""),
            notes=request.form.get("notes", ""),
        )
        db.session.add(trial)
        db.session.commit()
        flash("Trial created.", "success")
        return redirect(url_for("trial_detail", trial_id=trial.id))
    return render_template("trial_form.html", trial=None, categories=CROP_CATEGORIES)


@app.route("/trials/<int:trial_id>")
def trial_detail(trial_id):
    trial = db.get_or_404(Trial, trial_id)
    return render_template("trial_detail.html", trial=trial)


@app.route("/trials/<int:trial_id>/edit", methods=["GET", "POST"])
def trial_edit(trial_id):
    trial = db.get_or_404(Trial, trial_id)
    if request.method == "POST":
        trial.name = request.form["name"]
        trial.year = int(request.form["year"])
        trial.crop_category = request.form["crop_category"]
        trial.pi_name = request.form.get("pi_name", "")
        trial.notes = request.form.get("notes", "")
        db.session.commit()
        flash("Trial updated.", "success")
        return redirect(url_for("trial_detail", trial_id=trial.id))
    return render_template("trial_form.html", trial=trial, categories=CROP_CATEGORIES)


@app.route("/trials/<int:trial_id>/delete", methods=["POST"])
def trial_delete(trial_id):
    trial = db.get_or_404(Trial, trial_id)
    db.session.delete(trial)
    db.session.commit()
    flash("Trial deleted.", "success")
    return redirect(url_for("index"))

# ---------------------------------------------------------------------------
# SiteBlock CRUD
# ---------------------------------------------------------------------------

@app.route("/trials/<int:trial_id>/blocks/new", methods=["GET", "POST"])
def block_new(trial_id):
    trial = db.get_or_404(Trial, trial_id)
    if request.method == "POST":
        block = SiteBlock(
            trial_id=trial.id,
            name=request.form["name"],
            description=request.form.get("description", ""),
            center_lat=float(request.form.get("center_lat", 35.7796)),
            center_lng=float(request.form.get("center_lng", -78.6382)),
            width_m=float(request.form.get("width_m", 50)),
            height_m=float(request.form.get("height_m", 50)),
            rotation_deg=float(request.form.get("rotation_deg", 0)),
            notes=request.form.get("notes", ""),
        )
        db.session.add(block)
        db.session.commit()
        flash("Site block created.", "success")
        return redirect(url_for("trial_detail", trial_id=trial.id))
    return render_template("block_form.html", trial=trial, block=None)


@app.route("/trials/<int:trial_id>/blocks/<int:block_id>/edit", methods=["GET", "POST"])
def block_edit(trial_id, block_id):
    trial = db.get_or_404(Trial, trial_id)
    block = db.get_or_404(SiteBlock, block_id)
    if request.method == "POST":
        block.name = request.form["name"]
        block.description = request.form.get("description", "")
        block.center_lat = float(request.form.get("center_lat", 35.7796))
        block.center_lng = float(request.form.get("center_lng", -78.6382))
        block.width_m = float(request.form.get("width_m", 50))
        block.height_m = float(request.form.get("height_m", 50))
        block.rotation_deg = float(request.form.get("rotation_deg", 0))
        block.notes = request.form.get("notes", "")
        db.session.commit()
        flash("Site block updated.", "success")
        return redirect(url_for("trial_detail", trial_id=trial.id))
    return render_template("block_form.html", trial=trial, block=block)

# ---------------------------------------------------------------------------
# Treatments
# ---------------------------------------------------------------------------

@app.route("/trials/<int:trial_id>/treatments", methods=["GET", "POST"])
def treatments(trial_id):
    trial = db.get_or_404(Trial, trial_id)
    if request.method == "POST":
        t = Treatment(
            trial_id=trial.id,
            name=request.form["name"],
            description=request.form.get("description", ""),
        )
        db.session.add(t)
        db.session.commit()
        flash("Treatment added.", "success")
        return redirect(url_for("treatments", trial_id=trial.id))
    return render_template("treatments.html", trial=trial)


@app.route("/trials/<int:trial_id>/treatments/<int:treatment_id>/delete", methods=["POST"])
def treatment_delete(trial_id, treatment_id):
    treatment = db.get_or_404(Treatment, treatment_id)
    # Only allow deletion if no plots reference this treatment
    plot_count = Plot.query.filter_by(treatment_id=treatment.id).count()
    if plot_count > 0:
        flash(f"Cannot delete treatment '{treatment.name}' — it is used by {plot_count} plot(s).", "error")
    else:
        db.session.delete(treatment)
        db.session.commit()
        flash("Treatment deleted.", "success")
    return redirect(url_for("treatments", trial_id=trial_id))

# ---------------------------------------------------------------------------
# Generate plots
# ---------------------------------------------------------------------------

@app.route("/trials/<int:trial_id>/generate_plots", methods=["GET", "POST"])
def generate_plots(trial_id):
    trial = db.get_or_404(Trial, trial_id)

    if request.method == "POST":
        block_id = int(request.form["site_block_id"])
        rows = int(request.form["rows"])
        cols = int(request.form["cols"])
        treatment_ids = request.form.getlist("treatment_ids", type=int)

        if not treatment_ids:
            flash("Select at least one treatment.", "error")
            return redirect(url_for("generate_plots", trial_id=trial.id))

        block = db.get_or_404(SiteBlock, block_id)

        # Delete existing plots for this trial/block
        Plot.query.filter_by(trial_id=trial.id, site_block_id=block.id).delete()

        total_cells = rows * cols
        # Fill treatment list to cover all cells
        trt_list = []
        while len(trt_list) < total_cells:
            trt_list.extend(treatment_ids)
        trt_list = trt_list[:total_cells]
        random.shuffle(trt_list)

        idx = 0
        for r in range(rows):
            for c in range(cols):
                plot = Plot(
                    trial_id=trial.id,
                    site_block_id=block.id,
                    plot_code=f"{block.name}-R{r+1}C{c+1}",
                    row_index=r,
                    col_index=c,
                    treatment_id=trt_list[idx],
                )
                db.session.add(plot)
                idx += 1

        db.session.commit()

        remainder = total_cells % len(treatment_ids)
        if remainder:
            flash(
                f"Generated {total_cells} plots. Note: treatments don't divide evenly "
                f"into {total_cells} cells ({remainder} extra slot(s) filled by repeating treatments).",
                "warning",
            )
        else:
            flash(f"Generated {total_cells} plots with randomized treatment assignment.", "success")
        return redirect(url_for("trial_detail", trial_id=trial.id))

    return render_template("generate_plots.html", trial=trial)

# ---------------------------------------------------------------------------
# Map layout view + JSON data endpoint
# ---------------------------------------------------------------------------

@app.route("/trials/<int:trial_id>/layout")
def layout_view(trial_id):
    trial = db.get_or_404(Trial, trial_id)
    trait_id = request.args.get("trait_id", type=int)
    traits = Trait.query.filter_by(trial_id=trial.id).all()
    return render_template("layout.html", trial=trial, traits=traits, selected_trait_id=trait_id)


@app.route("/trials/<int:trial_id>/layout_data")
def layout_data(trial_id):
    trial = db.get_or_404(Trial, trial_id)
    trait_id = request.args.get("trait_id", type=int)

    blocks_data = []
    for block in trial.site_blocks:
        plots = Plot.query.filter_by(trial_id=trial.id, site_block_id=block.id).all()
        # Determine grid dimensions
        if plots:
            max_row = max(p.row_index for p in plots) + 1
            max_col = max(p.col_index for p in plots) + 1
        else:
            max_row = 0
            max_col = 0

        plots_data = []
        for p in plots:
            trt_name = p.treatment.name if p.treatment else "Unassigned"

            measurement_val = None
            if trait_id:
                m = Measurement.query.filter_by(plot_id=p.id, trait_id=trait_id).order_by(
                    Measurement.date.desc()
                ).first()
                if m:
                    measurement_val = m.value

            plots_data.append({
                "id": p.id,
                "plot_code": p.plot_code,
                "row": p.row_index,
                "col": p.col_index,
                "treatment_id": p.treatment_id,
                "treatment_name": trt_name,
                "measurement": measurement_val,
            })

        blocks_data.append({
            "id": block.id,
            "name": block.name,
            "center_lat": block.center_lat,
            "center_lng": block.center_lng,
            "width_m": block.width_m,
            "height_m": block.height_m,
            "rotation_deg": block.rotation_deg,
            "rows": max_row,
            "cols": max_col,
            "plots": plots_data,
        })

    # Build a treatment color map
    treatments = Treatment.query.filter_by(trial_id=trial.id).all()
    palette = [
        "#4285F4", "#EA4335", "#FBBC05", "#34A853",
        "#FF6D01", "#46BDC6", "#7B1FA2", "#C2185B",
        "#00ACC1", "#FFB300", "#8D6E63", "#78909C",
    ]
    treatment_colors = {}
    for i, t in enumerate(treatments):
        treatment_colors[t.id] = palette[i % len(palette)]

    return jsonify({
        "blocks": blocks_data,
        "treatment_colors": treatment_colors,
    })

# ---------------------------------------------------------------------------
# Traits
# ---------------------------------------------------------------------------

@app.route("/trials/<int:trial_id>/traits", methods=["GET", "POST"])
def traits(trial_id):
    trial = db.get_or_404(Trial, trial_id)
    if request.method == "POST":
        min_val = request.form.get("min_val", "").strip()
        max_val = request.form.get("max_val", "").strip()
        trait = Trait(
            trial_id=trial.id,
            name=request.form["name"],
            type=request.form["type"],
            units=request.form.get("units", ""),
            min_val=float(min_val) if min_val else None,
            max_val=float(max_val) if max_val else None,
        )
        db.session.add(trait)
        db.session.commit()
        flash("Trait added.", "success")
        return redirect(url_for("traits", trial_id=trial.id))
    return render_template("traits.html", trial=trial, trait_types=TRAIT_TYPES)


@app.route("/trials/<int:trial_id>/traits/<int:trait_id>/delete", methods=["POST"])
def trait_delete(trial_id, trait_id):
    trait = db.get_or_404(Trait, trait_id)
    db.session.delete(trait)
    db.session.commit()
    flash("Trait deleted.", "success")
    return redirect(url_for("traits", trial_id=trial_id))

# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------

@app.route("/trials/<int:trial_id>/measurements", methods=["GET", "POST"])
def measurements(trial_id):
    trial = db.get_or_404(Trial, trial_id)

    if request.method == "POST":
        trait_id = int(request.form["trait_id"])
        mdate = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        trait = db.get_or_404(Trait, trait_id)

        plots = (
            Plot.query.filter_by(trial_id=trial.id)
            .order_by(Plot.site_block_id, Plot.row_index, Plot.col_index)
            .all()
        )

        saved = 0
        for p in plots:
            val = request.form.get(f"value_{p.id}", "").strip()
            note = request.form.get(f"note_{p.id}", "").strip()
            if not val and not note:
                continue

            # Basic validation
            if trait.type in ("numeric", "rating") and val:
                try:
                    fval = float(val)
                except ValueError:
                    flash(f"Plot {p.plot_code}: '{val}' is not a valid number. Skipped.", "error")
                    continue
                if trait.type == "rating":
                    if trait.min_val is not None and fval < trait.min_val:
                        flash(f"Plot {p.plot_code}: value {fval} below min {trait.min_val}. Skipped.", "error")
                        continue
                    if trait.max_val is not None and fval > trait.max_val:
                        flash(f"Plot {p.plot_code}: value {fval} above max {trait.max_val}. Skipped.", "error")
                        continue

            # Upsert by (plot_id, trait_id, date)
            existing = Measurement.query.filter_by(
                plot_id=p.id, trait_id=trait_id, date=mdate
            ).first()
            if existing:
                existing.value = val
                existing.note = note
            else:
                m = Measurement(
                    trial_id=trial.id,
                    plot_id=p.id,
                    trait_id=trait_id,
                    date=mdate,
                    value=val,
                    note=note,
                )
                db.session.add(m)
            saved += 1

        db.session.commit()
        flash(f"Saved {saved} measurement(s).", "success")
        return redirect(url_for("measurements", trial_id=trial.id, trait_id=trait_id, date=mdate.isoformat()))

    # GET — render form
    trait_id = request.args.get("trait_id", type=int)
    mdate_str = request.args.get("date", date.today().isoformat())
    try:
        mdate = datetime.strptime(mdate_str, "%Y-%m-%d").date()
    except ValueError:
        mdate = date.today()

    trait_obj = None
    if trait_id:
        trait_obj = Trait.query.get(trait_id)

    plots = (
        Plot.query.filter_by(trial_id=trial.id)
        .order_by(Plot.site_block_id, Plot.row_index, Plot.col_index)
        .all()
    )

    # Pre-load existing measurements for this trait/date
    existing_map = {}
    if trait_obj:
        existing = Measurement.query.filter_by(
            trial_id=trial.id, trait_id=trait_obj.id, date=mdate
        ).all()
        for m in existing:
            existing_map[m.plot_id] = m

    return render_template(
        "measurements.html",
        trial=trial,
        plots=plots,
        trait=trait_obj,
        mdate=mdate,
        existing_map=existing_map,
    )

# ---------------------------------------------------------------------------
# Analytics / summary
# ---------------------------------------------------------------------------

@app.route("/trials/<int:trial_id>/summary")
def trial_summary(trial_id):
    trial = db.get_or_404(Trial, trial_id)
    trait_id = request.args.get("trait_id", type=int)

    summary_data = []
    selected_trait = None

    if trait_id:
        selected_trait = Trait.query.get(trait_id)
        if selected_trait and selected_trait.type in ("numeric", "rating"):
            for trt in trial.treatments:
                # Get measurements for this treatment and trait
                plot_ids = [p.id for p in trt.plots if p.trial_id == trial.id]
                if not plot_ids:
                    continue
                ms = Measurement.query.filter(
                    Measurement.trait_id == trait_id,
                    Measurement.plot_id.in_(plot_ids),
                ).all()
                values = []
                for m in ms:
                    try:
                        values.append(float(m.value))
                    except (ValueError, TypeError):
                        pass
                n = len(values)
                mean = statistics.mean(values) if values else None
                sd = statistics.stdev(values) if len(values) > 1 else None
                summary_data.append({
                    "treatment": trt.name,
                    "n": n,
                    "mean": round(mean, 3) if mean is not None else None,
                    "sd": round(sd, 3) if sd is not None else None,
                })

    return render_template(
        "summary.html",
        trial=trial,
        summary_data=summary_data,
        selected_trait=selected_trait,
    )

# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

@app.route("/trials/<int:trial_id>/export")
def export_csv(trial_id):
    trial = db.get_or_404(Trial, trial_id)
    export_type = request.args.get("type", "measurements")

    si = io.StringIO()
    writer = csv.writer(si)

    if export_type == "layout":
        writer.writerow(["trial_name", "year", "site_block", "plot_code", "row_index", "col_index", "treatment"])
        plots = (
            Plot.query.filter_by(trial_id=trial.id)
            .order_by(Plot.site_block_id, Plot.row_index, Plot.col_index)
            .all()
        )
        for p in plots:
            writer.writerow([
                trial.name,
                trial.year,
                p.site_block.name if p.site_block else "",
                p.plot_code,
                p.row_index,
                p.col_index,
                p.treatment.name if p.treatment else "",
            ])
        filename = f"{trial.name.replace(' ', '_')}_layout.csv"
    else:
        writer.writerow([
            "trial_name", "year", "site_block", "plot_code",
            "row_index", "col_index", "treatment",
            "trait", "date", "value", "note",
        ])
        ms = (
            Measurement.query.filter_by(trial_id=trial.id)
            .order_by(Measurement.date, Measurement.plot_id)
            .all()
        )
        for m in ms:
            plot = m.plot
            writer.writerow([
                trial.name,
                trial.year,
                plot.site_block.name if plot.site_block else "",
                plot.plot_code,
                plot.row_index,
                plot.col_index,
                plot.treatment.name if plot.treatment else "",
                m.trait.name if m.trait else "",
                m.date.isoformat() if m.date else "",
                m.value,
                m.note,
            ])
        filename = f"{trial.name.replace(' ', '_')}_measurements.csv"

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
