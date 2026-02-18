from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Trial(db.Model):
    __tablename__ = "trials"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    crop_category = db.Column(db.String(50), nullable=False, default="other")
    pi_name = db.Column(db.String(200), default="")
    notes = db.Column(db.Text, default="")

    site_blocks = db.relationship("SiteBlock", backref="trial", cascade="all, delete-orphan", lazy=True)
    treatments = db.relationship("Treatment", backref="trial", cascade="all, delete-orphan", lazy=True)
    plots = db.relationship("Plot", backref="trial", cascade="all, delete-orphan", lazy=True)
    traits = db.relationship("Trait", backref="trial", cascade="all, delete-orphan", lazy=True)
    measurements = db.relationship("Measurement", backref="trial", cascade="all, delete-orphan", lazy=True)


class SiteBlock(db.Model):
    __tablename__ = "site_blocks"

    id = db.Column(db.Integer, primary_key=True)
    trial_id = db.Column(db.Integer, db.ForeignKey("trials.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    center_lat = db.Column(db.Float, nullable=False, default=35.7796)
    center_lng = db.Column(db.Float, nullable=False, default=-78.6382)
    width_m = db.Column(db.Float, nullable=False, default=50.0)
    height_m = db.Column(db.Float, nullable=False, default=50.0)
    rotation_deg = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.Text, default="")

    plots = db.relationship("Plot", backref="site_block", cascade="all, delete-orphan", lazy=True)


class Treatment(db.Model):
    __tablename__ = "treatments"

    id = db.Column(db.Integer, primary_key=True)
    trial_id = db.Column(db.Integer, db.ForeignKey("trials.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")

    plots = db.relationship("Plot", backref="treatment", lazy=True)


class Plot(db.Model):
    __tablename__ = "plots"

    id = db.Column(db.Integer, primary_key=True)
    trial_id = db.Column(db.Integer, db.ForeignKey("trials.id"), nullable=False, index=True)
    site_block_id = db.Column(db.Integer, db.ForeignKey("site_blocks.id"), nullable=False, index=True)
    plot_code = db.Column(db.String(50), nullable=False)
    row_index = db.Column(db.Integer, nullable=False)
    col_index = db.Column(db.Integer, nullable=False)
    treatment_id = db.Column(db.Integer, db.ForeignKey("treatments.id"), nullable=True)
    notes = db.Column(db.Text, default="")

    measurements = db.relationship("Measurement", backref="plot", cascade="all, delete-orphan", lazy=True)


class Trait(db.Model):
    __tablename__ = "traits"

    id = db.Column(db.Integer, primary_key=True)
    trial_id = db.Column(db.Integer, db.ForeignKey("trials.id"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False, default="numeric")  # numeric, rating, categorical, text
    units = db.Column(db.String(50), default="")
    min_val = db.Column(db.Float, nullable=True)
    max_val = db.Column(db.Float, nullable=True)

    measurements = db.relationship("Measurement", backref="trait", cascade="all, delete-orphan", lazy=True)


class Measurement(db.Model):
    __tablename__ = "measurements"

    id = db.Column(db.Integer, primary_key=True)
    trial_id = db.Column(db.Integer, db.ForeignKey("trials.id"), nullable=False, index=True)
    plot_id = db.Column(db.Integer, db.ForeignKey("plots.id"), nullable=False, index=True)
    trait_id = db.Column(db.Integer, db.ForeignKey("traits.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    value = db.Column(db.String(500), default="")
    note = db.Column(db.Text, default="")

    __table_args__ = (
        db.Index("ix_measurement_lookup", "plot_id", "trait_id", "date"),
    )
