from importlib import import_module

MODULES = (
    "m1_sampling",
    "m2_calibration",
    "m3_alignment",
    "m4_elongation",
    "m5_verdicts",
    "m6_reconcile",
    "m7_runs",
)


def register(app):
    for name in MODULES:
        app.register_blueprint(import_module(f"app.modules.{name}.handler").router)
