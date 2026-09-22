# PATH: GovScheme/ai/intent_classifier.py
"""
Lightweight, dependency-free intent classifier (spec section 36).
Keyword/rule based - deterministic and explainable, appropriate for a
final-year prototype and works fully offline. It also does not need a
trained model or training data of its own, so it can't silently drift.
"""

INTENT_KEYWORDS = {
    "NAVIGATE": [],  # handled separately via language_service.match_navigation_command
    "COMPLAINT_STATUS": ["complaint status", "latest complaint response", "what did support say", "customer care response", "support response"],
    "COMPLAINT": ["complaint", "not working", "isn't working", "not updating", "stuck",
                  "problem with", "broken", "error occurred", "raise a complaint",
                  "customer support", "customer care", "grievance", "issue with my"],
    "WHY_RECOMMENDED": ["why recommend", "why is this", "why was this", "reason for recommend"],
    "RECOMMENDATIONS": ["recommend", "suggest", "best scheme", "what schemes do you"],
    "ELIGIBILITY": ["eligible", "eligibility", "qualify", "am i eligible", "can i apply"],
    "APPLICATION_STATUS": ["application status", "track my application", "status of my application"],
    "APPLICATION_PROCESS": ["how to apply", "apply for", "application process", "how do i apply", "how can i apply", "apply scheme"],
    "SAVED_SCHEMES": ["saved scheme", "my saved", "bookmarked"],
    "NEW_SCHEMES": ["new scheme", "latest scheme", "recently added", "new and updated", "updated schemes"],
    "DOCUMENT_READINESS": ["check my documents", "document readiness", "documents for this scheme", "which documents are missing", "missing documents", "do i have the documents", "open digilocker", "connect my digilocker"],
    "DOCUMENTS": ["document", "documents required", "papers needed"],
    "BENEFITS": ["benefit", "benefits of"],
    "FARMER_SCHEMES": ["farmer scheme", "for farmers", "kisan"],
    "STUDENT_SCHEMES": ["student scheme", "scholarship", "for students"],
    "SENIOR_CITIZEN_SCHEMES": ["senior citizen scheme", "for elderly", "old age"],
    "DISABILITY_SCHEMES": ["disability scheme", "for disabled", "divyang"],
    "WOMEN_SCHEMES": ["women scheme", "for women", "widow scheme"],
    "HOUSING": ["housing scheme", "house scheme", "pmay", "shelter"],
    "HEALTH": ["health scheme", "health insurance", "ayushman"],
    "EDUCATION": ["education scheme", "scholarship scheme"],
    "STATE_SEARCH": ["schemes in", "state scheme"],
    "CATEGORY_SEARCH": ["category", "type of scheme"],
    "SCHEME_DETAILS": ["tell me about", "details of", "what is"],
    "SCHEME_SEARCH": ["find scheme", "search scheme", "look for scheme"],
}


def classify_intent(message: str) -> str:
    text = message.lower().strip()
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return intent
    return "GENERAL_SCHEME_QUERY"
