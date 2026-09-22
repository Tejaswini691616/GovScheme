from database.db import get_db_connection


def check_eligibility(user_id):
    """
    Check the user's eligibility against all active government schemes.

    Returns a list of eligibility results.
    """

    conn = get_db_connection()

    try:
        # ---------------------------------------------------------
        # 1. Get citizen profile
        # ---------------------------------------------------------

        profile = conn.execute(
            """
            SELECT *
            FROM citizen_profiles
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if not profile:
            return {
                "success": False,
                "message": "Citizen profile not found.",
                "results": []
            }

        # ---------------------------------------------------------
        # 2. Get all active schemes
        # ---------------------------------------------------------

        schemes = conn.execute(
            """
            SELECT *
            FROM schemes
            WHERE is_active = 1
            ORDER BY id
            """
        ).fetchall()

        results = []

        # ---------------------------------------------------------
        # 3. Check every scheme
        # ---------------------------------------------------------

        for scheme in schemes:

            failed_criteria = []
            passed_criteria = []

            # =====================================================
            # AGE CHECK
            # =====================================================

            age = profile["age"]

            if age is not None:

                if scheme["min_age"] is not None:

                    if age < scheme["min_age"]:
                        failed_criteria.append(
                            f"Minimum age is {scheme['min_age']} years."
                        )
                    else:
                        passed_criteria.append("Age requirement satisfied.")

                if scheme["max_age"] is not None:

                    if age > scheme["max_age"]:
                        failed_criteria.append(
                            f"Maximum age is {scheme['max_age']} years."
                        )
                    else:
                        passed_criteria.append("Age requirement satisfied.")

            # =====================================================
            # INCOME CHECK
            # =====================================================

            income = profile["annual_family_income"]

            if (
                scheme["income_limit"] is not None
                and income is not None
            ):

                if income > scheme["income_limit"]:

                    failed_criteria.append(
                        f"Annual income must not exceed ₹{scheme['income_limit']:,.0f}."
                    )

                else:

                    passed_criteria.append(
                        "Income requirement satisfied."
                    )

            # =====================================================
            # CASTE CHECK
            # =====================================================

            caste_requirement = scheme["caste_requirement"]

            if caste_requirement:

                user_caste = profile["caste"]

                if not user_caste:

                    failed_criteria.append(
                        f"Caste requirement: {caste_requirement}."
                    )

                else:

                    allowed_castes = [
                        caste.strip().upper()
                        for caste in caste_requirement.split("/")
                    ]

                    if user_caste.strip().upper() not in allowed_castes:

                        failed_criteria.append(
                            f"Scheme is available for {caste_requirement} category."
                        )

                    else:

                        passed_criteria.append(
                            "Caste requirement satisfied."
                        )

            # =====================================================
            # FARMER CHECK
            # =====================================================

            if scheme["farmer_required"] == 1:

                farmer = str(profile["farmer"] or "").strip().lower()

                if farmer not in ["yes", "y", "true", "1"]:

                    failed_criteria.append(
                        "Applicant must be a farmer."
                    )

                else:

                    passed_criteria.append(
                        "Farmer requirement satisfied."
                    )

            # =====================================================
            # BPL CHECK
            # =====================================================

            if scheme["bpl_required"] == 1:

                bpl = str(profile["bpl"] or "").strip().lower()

                if bpl not in ["yes", "y", "true", "1"]:

                    failed_criteria.append(
                        "Applicant must belong to the BPL category."
                    )

                else:

                    passed_criteria.append(
                        "BPL requirement satisfied."
                    )

            # =====================================================
            # DISABILITY CHECK
            # =====================================================

            if scheme["disability_required"] == 1:

                disability = str(
                    profile["disability"] or ""
                ).strip().lower()

                if disability not in ["yes", "y", "true", "1"]:

                    failed_criteria.append(
                        "Applicant must have a disability."
                    )

                else:

                    passed_criteria.append(
                        "Disability requirement satisfied."
                    )

            # =====================================================
            # STUDENT CHECK
            # =====================================================

            if scheme["student_required"] == 1:

                student = str(
                    profile["student"] or ""
                ).strip().lower()

                if student not in ["yes", "y", "true", "1"]:

                    failed_criteria.append(
                        "Applicant must be a student."
                    )

                else:

                    passed_criteria.append(
                        "Student requirement satisfied."
                    )

            # =====================================================
            # WIDOW CHECK
            # =====================================================

            if scheme["widow_required"] == 1:

                widow = str(
                    profile["widow"] or ""
                ).strip().lower()

                if widow not in ["yes", "y", "true", "1"]:

                    failed_criteria.append(
                        "Applicant must be a widow."
                    )

                else:

                    passed_criteria.append(
                        "Widow requirement satisfied."
                    )

            # =====================================================
            # FINAL ELIGIBILITY
            # =====================================================

            if len(failed_criteria) == 0:

                eligibility_status = "Eligible"

            else:

                eligibility_status = "Not Eligible"

            # -----------------------------------------------------
            # Eligibility score
            # -----------------------------------------------------

            total_criteria = (
                len(failed_criteria)
                + len(passed_criteria)
            )

            if total_criteria > 0:

                eligibility_score = round(
                    (len(passed_criteria) / total_criteria) * 100,
                    2
                )

            else:

                eligibility_score = 100.0

            # -----------------------------------------------------
            # Recommendation reason
            # -----------------------------------------------------

            if eligibility_status == "Eligible":

                recommendation_reason = (
                    f"You appear eligible for {scheme['scheme_name']} "
                    "based on the available profile information."
                )

            else:

                recommendation_reason = (
                    f"You are currently not eligible for "
                    f"{scheme['scheme_name']} because "
                    + " ".join(failed_criteria)
                )

            # -----------------------------------------------------
            # Store result
            # -----------------------------------------------------

            conn.execute(
                """
                INSERT INTO eligibility_results (
                    user_id,
                    scheme_id,
                    eligibility_status,
                    eligibility_score,
                    failed_criteria,
                    recommendation_reason
                )
                VALUES (?, ?, ?, ?, ?, ?)

                ON CONFLICT(user_id, scheme_id)
                DO UPDATE SET

                    eligibility_status =
                        excluded.eligibility_status,

                    eligibility_score =
                        excluded.eligibility_score,

                    failed_criteria =
                        excluded.failed_criteria,

                    recommendation_reason =
                        excluded.recommendation_reason,

                    checked_at =
                        CURRENT_TIMESTAMP
                """,
                (
                    user_id,
                    scheme["id"],
                    eligibility_status,
                    eligibility_score,
                    " | ".join(failed_criteria)
                    if failed_criteria
                    else None,
                    recommendation_reason
                )
            )

            # -----------------------------------------------------
            # Add result to response
            # -----------------------------------------------------

            results.append(
                {
                    "scheme_id": scheme["id"],
                    "scheme_code": scheme["scheme_id"],
                    "scheme_name": scheme["scheme_name"],
                    "category": scheme["category"],
                    "status": eligibility_status,
                    "score": eligibility_score,
                    "failed_criteria": failed_criteria,
                    "passed_criteria": passed_criteria,
                    "reason": recommendation_reason
                }
            )

        # ---------------------------------------------------------
        # Commit all results
        # ---------------------------------------------------------

        conn.commit()

        return {
            "success": True,
            "message": "Eligibility check completed successfully.",
            "results": results
        }

    except Exception as e:

        conn.rollback()

        return {
            "success": False,
            "message": f"Eligibility check failed: {str(e)}",
            "results": []
        }

    finally:

        conn.close()


# ================================================================
# GET ONLY ELIGIBLE SCHEMES
# ================================================================

def get_eligible_schemes(user_id):

    result = check_eligibility(user_id)

    if not result["success"]:
        return result

    eligible = [
        scheme
        for scheme in result["results"]
        if scheme["status"] == "Eligible"
    ]

    return {
        "success": True,
        "message": "Eligible schemes retrieved successfully.",
        "results": eligible
    }


# ================================================================
# GET ONLY NON-ELIGIBLE SCHEMES
# ================================================================

def get_not_eligible_schemes(user_id):

    result = check_eligibility(user_id)

    if not result["success"]:
        return result

    not_eligible = [
        scheme
        for scheme in result["results"]
        if scheme["status"] == "Not Eligible"
    ]

    return {
        "success": True,
        "message": "Non-eligible schemes retrieved successfully.",
        "results": not_eligible
    }