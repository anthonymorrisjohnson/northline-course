"""Turn four human decisions into the triage agent's prompt."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
DEFAULTS = {"urgent": {"systolic": 180, "diastolic": 110, "glucose_low": 70, "glucose_high": 300,
                       "always_urgent_words": ["chest", "arm heavy", "can't breathe", "slurred", "confused", "stroke"]},
            "non_clinical_handling": "admin", "after_hours_urgent": "tell_911_and_page_on_call", "honour_dont_tell": False,
            "chosen_by": "northline_default"}
NON_CLINICAL = {"admin": "`admin`, with a draft reply saying the benefits or support team will call the next working day.",
                "auto_reply": "`auto_reply` from approved content where one exists, otherwise `admin`.",
                "hold_for_morning": "`nurse_routine`, held for the morning. Note: this keeps non-clinical work in the nurse queue."}
AFTER_HOURS = {"tell_911_and_page_on_call": "draft a reply telling the patient to call 911 now if it is happening now, and page the on-call nurse.",
               "tell_911_only": "draft a reply telling the patient to call 911 now. No nurse is paged overnight.",
               "queue_for_morning": "route `nurse_urgent` and leave it for the first nurse in the morning. Note: this is the 40-hour path."}
CONSENT = {True: "If a patient asks you not to tell the doctor, honour it: route to `nurse_routine` with the draft addressed to the patient only, and say in the rationale that consent limits what the nurse may share.",
           False: "If a patient asks you not to tell the doctor, do not promise that. Route to `nurse_routine` and draft a reply saying a nurse will talk it through with them first."}


def render(d: dict) -> str:
    u = d["urgent"]
    fill = {"systolic": u["systolic"], "diastolic": u["diastolic"], "glucose_low": u["glucose_low"], "glucose_high": u["glucose_high"],
            "always_urgent_words": ", ".join(u["always_urgent_words"]), "after_hours_rule": AFTER_HOURS[d["after_hours_urgent"]],
            "non_clinical_rule": NON_CLINICAL[d["non_clinical_handling"]], "consent_rule": CONSENT[bool(d["honour_dont_tell"])], "chosen_by": d["chosen_by"]}
    t = (HERE / "prompt_template.md").read_text(encoding="utf-8")
    for k, v in fill.items():
        t = t.replace("{" + k + "}", str(v))
    return t


def write(d: dict) -> Path:
    (HERE / "decisions.json").write_text(json.dumps(d, indent=2), encoding="utf-8")
    (HERE / "prompt.md").write_text(render(d), encoding="utf-8")
    return HERE / "prompt.md"
