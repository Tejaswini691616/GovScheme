# PATH: GovScheme/automation/scheme_validator.py
"""Basic validation for candidate scheme records before they enter the
Scheme Master database (spec section 24)."""

REQUIRED_FIELDS = ["scheme_id", "scheme_name", "category"]


def validate_scheme(candidate: dict) -> tuple[bool, list]:
    errors = []
    for field in REQUIRED_FIELDS:
        if not candidate.get(field):
            errors.append(f"Missing required field: {field}")

    for numeric_field in ["min_age", "max_age", "income_limit"]:
        val = candidate.get(numeric_field)
        if val is not None:
            try:
                float(val)
            except (TypeError, ValueError):
                errors.append(f"{numeric_field} must be numeric, got {val!r}")

    min_age, max_age = candidate.get("min_age"), candidate.get("max_age")
    if min_age is not None and max_age is not None:
        try:
            if float(min_age) > float(max_age):
                errors.append("min_age cannot be greater than max_age")
        except (TypeError, ValueError):
            pass

    return (len(errors) == 0), errors
