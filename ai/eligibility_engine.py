# PATH: GovScheme/ai/eligibility_engine.py
"""
Deterministic, rule-based eligibility engine.

Responsibility (per project spec):
    "Is the citizen potentially eligible according to the configured
    scheme criteria?"

This engine is intentionally NOT machine learning. It reads each scheme's
configured rule fields (min_age, max_age, income_limit, caste_requirement,
farmer_required, bpl_required, disability_required, student_required,
widow_required, land_limit_required) from the `schemes` table and evaluates
a citizen dict against only the criteria that are actually configured for
that scheme. It never fabricates criteria.

A criterion is "configured" when its value is not NULL/None (for numeric /
categorical fields) or is truthy (for the *_required boolean flags).
"""
from dataclasses import dataclass, field
from typing import Optional


def _normalize_yes_no(value) -> Optional[bool]:
    """Handle Yes/No, True/False, 1/0, blanks, mixed case/whitespace."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value in (0, 1):
            return bool(value)
        return None
    text = str(value).strip().lower()
    if text in ("", "nan", "none", "null"):
        return None
    if text in ("yes", "y", "true", "1"):
        return True
    if text in ("no", "n", "false", "0"):
        return False
    return None


@dataclass
class EligibilityResult:
    scheme_id: str
    scheme_name: str
    is_eligible: bool
    matched: list = field(default_factory=list)     # human-readable ✓ lines
    failed: list = field(default_factory=list)       # human-readable ✗ lines
    criteria_evaluated: int = 0

    def explanation_text(self) -> str:
        lines = []
        if self.matched:
            lines.append("Potentially eligible because:" if self.is_eligible else "Criteria that matched:")
            lines.extend(f"✓ {m}" for m in self.matched)
        if self.failed:
            lines.append("Criteria that did not match:")
            lines.extend(f"✗ {m}" for m in self.failed)
        if not self.matched and not self.failed:
            lines.append("No specific demographic criteria are configured for this scheme in the prototype dataset.")
        return "\n".join(lines)


def evaluate_eligibility(citizen: dict, scheme: dict) -> EligibilityResult:
    """
    citizen: dict with keys such as age, annual_income (or annual_family_income),
             caste, farmer, bpl, disability, student, widow, land_holding_acres
             Values may be "Yes"/"No" strings, bools, or numbers.
    scheme:  a row from the `schemes` table (dict-like) with the configured
             rule fields described in the module docstring.
    """
    matched, failed = [], []
    criteria_evaluated = 0

    def citizen_val(*keys):
        for k in keys:
            if k in citizen and citizen[k] is not None:
                return citizen[k]
        return None

    # ---- Age ----
    age = citizen_val("age", "Age")
    min_age = scheme.get("min_age")
    max_age = scheme.get("max_age")
    if min_age is not None and age is not None:
        criteria_evaluated += 1
        if float(age) >= float(min_age):
            matched.append(f"Age ({int(age)}) meets the configured minimum age ({int(min_age)}).")
        else:
            failed.append(f"Age ({int(age)}) is below the configured minimum age ({int(min_age)}).")
    if max_age is not None and age is not None:
        criteria_evaluated += 1
        if float(age) <= float(max_age):
            matched.append(f"Age ({int(age)}) is within the configured maximum age ({int(max_age)}).")
        else:
            failed.append(f"Age ({int(age)}) exceeds the configured maximum age ({int(max_age)}).")

    # ---- Income ----
    income_limit = scheme.get("income_limit")
    income = citizen_val("annual_income", "annual_family_income", "Annual_Family_Income")
    if income_limit is not None and income is not None:
        criteria_evaluated += 1
        if float(income) <= float(income_limit):
            matched.append(f"Annual family income (₹{int(income):,}) is within the configured limit (₹{int(income_limit):,}).")
        else:
            failed.append(f"Annual family income (₹{int(income):,}) exceeds the configured limit (₹{int(income_limit):,}).")

    # ---- Caste ----
    caste_req = scheme.get("caste_requirement")
    caste = citizen_val("caste", "Caste")
    if caste_req and str(caste_req).strip():
        criteria_evaluated += 1
        allowed = [c.strip().upper() for c in str(caste_req).split("/")]
        if caste and str(caste).strip().upper() in allowed:
            matched.append(f"Caste category ({caste}) matches the configured requirement ({caste_req}).")
        else:
            failed.append(f"Caste category ({caste or 'not provided'}) does not match the configured requirement ({caste_req}).")

    # ---- Yes/No flag criteria ----
    flag_criteria = [
        ("farmer_required", ("farmer", "Farmer"), "Farmer status"),
        ("bpl_required", ("bpl", "BPL"), "BPL status"),
        ("disability_required", ("disability", "Disability"), "Disability status"),
        ("student_required", ("student", "Student"), "Student status"),
        ("widow_required", ("widow", "Widow"), "Widow status"),
    ]
    for scheme_flag_key, citizen_keys, label in flag_criteria:
        required = _normalize_yes_no(scheme.get(scheme_flag_key))
        if required:  # only evaluate when the scheme actually requires it
            criteria_evaluated += 1
            citizen_flag = _normalize_yes_no(citizen_val(*citizen_keys))
            if citizen_flag is True:
                matched.append(f"{label} matches the configured requirement.")
            else:
                failed.append(f"{label} does not match the configured requirement.")

    # ---- Land limit ----
    # NOTE: in the current prototype dataset, Land_Limit is a boolean flag with
    # no numeric acreage value configured for any scheme, so this branch only
    # activates if land_limit_required is set AND a numeric land_limit_acres
    # is present (future-proofed; currently inert with this dataset).
    land_required = _normalize_yes_no(scheme.get("land_limit_required"))
    land_limit_acres = scheme.get("land_limit_acres")
    land_holding = citizen_val("land_holding_acres", "Land_Holding_Acres")
    if land_required and land_limit_acres is not None and land_holding is not None:
        criteria_evaluated += 1
        if float(land_holding) <= float(land_limit_acres):
            matched.append(f"Land holding ({land_holding} acres) is within the configured limit ({land_limit_acres} acres).")
        else:
            failed.append(f"Land holding ({land_holding} acres) exceeds the configured limit ({land_limit_acres} acres).")

    is_eligible = criteria_evaluated > 0 and len(failed) == 0

    return EligibilityResult(
        scheme_id=scheme.get("scheme_id"),
        scheme_name=scheme.get("scheme_name"),
        is_eligible=is_eligible,
        matched=matched,
        failed=failed,
        criteria_evaluated=criteria_evaluated,
    )


def evaluate_all_schemes(citizen: dict, schemes: list) -> list:
    """Returns a list of EligibilityResult, one per scheme."""
    return [evaluate_eligibility(citizen, scheme) for scheme in schemes]
