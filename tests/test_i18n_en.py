"""Modo inglés para demostraciones (BOT_LANGUAGE=en)."""

import os
import subprocess
import sys

import pytest

from nflb.core.guardrails import find_forbidden
from nflb.core.safety import is_urgent_by_rules


@pytest.mark.parametrize(
    "text",
    [
        "You are entitled to this benefit.",
        "You're eligible for the IMV.",
        "I can't say if you qualify.",
        "You meet the requirements.",
        "You don't meet all the requirements.",
        "You will be granted the aid.",
        "They will give you the money soon, they'll grant it.",
        "You can receive the benefit from next month.",
    ],
)
def test_english_eligibility_phrases_blocked(text):
    assert find_forbidden(text)


@pytest.mark.parametrize(
    "text",
    [
        "You could ask about the Ingreso Mínimo Vital at your Social Work Unit.",
        "You will get a letter from the council.",
        "Social Services will assess your case.",
    ],
)
def test_english_safe_phrases_pass(text):
    assert not find_forbidden(text)


@pytest.mark.parametrize(
    "text,urgent",
    [
        ("Tonight we are sleeping on the street with the kids", True),
        ("My husband hits me", True),
        ("I want to kill myself", True),
        ("I'm afraid of my ex", True),
        ("What benefits are there for single mothers?", False),
    ],
)
def test_english_urgency_rules(text, urgent):
    assert is_urgent_by_rules(text) is urgent


def test_fixed_texts_switch_to_english():
    code = (
        "from nflb.core import texts, safety, requirement;"
        "from nflb.pdf.summary_pdf import DISCLAIMER;"
        "assert texts.CIERRE.startswith('Your social worker');"
        "assert 'Do you accept?' in texts.BIENVENIDA;"
        "assert '/summary' in texts.AYUDA;"
        "assert 'Emergencies' in safety.urgent_block();"
        "assert 'It is not an assessment' in DISCLAIMER;"
        "assert requirement.HOW_TO.startswith('📸 Send me');"
        "from nflb.i18n import llm_language_rule; assert 'English' in llm_language_rule()"
    )
    env = {**os.environ, "BOT_LANGUAGE": "en", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_spanish_is_default():
    from nflb.core import texts
    from nflb.i18n import llm_language_rule

    assert texts.CIERRE == "Quien valora tu caso es tu trabajadora social."
    assert llm_language_rule() == ""
