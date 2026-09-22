# PATH: GovScheme/tests/test_language_service.py
from ai.language_service import detect_language


def test_high_confidence_script_detection():
    assert detect_language("यह योजना मेरे लिए है", "English")[0] == "Hindi"
    assert detect_language("இந்த திட்டம் என்ன?", "English")[0] == "Tamil"


def test_ambiguous_bengali_assamese_script_has_lower_confidence():
    language, confidence = detect_language("এই ভাষা", "English")
    assert language == "Bengali"
    assert confidence < 0.75


def test_latin_input_uses_preference_with_low_detection_confidence():
    language, confidence = detect_language("scheme for farmer", "Hindi")
    assert language == "Hindi"
    assert confidence < 0.75
