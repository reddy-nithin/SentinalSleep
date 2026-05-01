"""Unit tests for the Phase 4 pure state machine.

Tests every transition in the table using table-driven test cases.
"""

from __future__ import annotations

import pytest

from sentinelsleep import config
from sentinelsleep.db.schema import States
from sentinelsleep.orchestrator.state_machine import Observation, StateMachine


def test_initial_state():
    """Verify the SM starts in LISTENING state."""
    sm = StateMachine()
    assert sm.state == States.LISTENING


@pytest.mark.parametrize(
    "current_state, dss, nightmare_confirmed, expected_state, expected_action",
    [
        # LISTENING transitions
        (States.LISTENING, config.DSS_FLAG_THRESHOLD - 0.1, False, States.LISTENING, "none"),
        (States.LISTENING, config.DSS_FLAG_THRESHOLD + 0.1, False, States.FLAGGED, "none"),

        # FLAGGED transitions
        (States.FLAGGED, config.DSS_FLAG_THRESHOLD + 0.1, False, States.FLAGGED, "none"),
        (States.FLAGGED, config.DSS_FLAG_THRESHOLD + 0.1, True, States.INTERVENING, "intervene"),
        (States.FLAGGED, config.DSS_FLAG_THRESHOLD - 0.1, False, States.LISTENING, "none"),

        # INTERVENING transitions (ignoring persistence timeout for now)
        (States.INTERVENING, config.DSS_FLAG_THRESHOLD + 0.1, False, States.INTERVENING, "none"),
        (States.INTERVENING, config.DSS_FLAG_THRESHOLD - 0.1, False, States.RESOLVED, "none"),

        # ESCALATING transitions
        (States.ESCALATING, config.DSS_FLAG_THRESHOLD + 0.1, False, States.ESCALATING, "none"),

        # RESOLVED / AWAKE auto-return
        (States.RESOLVED, 0.0, False, States.LISTENING, "none"),
        (States.AWAKE, 0.0, False, States.LISTENING, "none"),
    ]
)
def test_transitions(current_state, dss, nightmare_confirmed, expected_state, expected_action):
    """Test transitions without time-based constraints or manual resets."""
    sm = StateMachine(state=current_state)
    obs = Observation(dss=dss, nightmare_confirmed=nightmare_confirmed)
    new_state, action = sm.update(obs)

    assert new_state == expected_state
    assert action == expected_action
    assert sm.state == expected_state


def test_intervening_escalation_timeout(monkeypatch):
    """Test that INTERVENING escalates if distress persists too long."""
    import time
    sm = StateMachine(state=States.INTERVENING)
    # Mock monotonic to be exactly ESCALATION_PERSISTENCE_SECONDS after entering state
    monkeypatch.setattr(time, "monotonic", lambda: sm._state_entered_at + config.ESCALATION_PERSISTENCE_SECONDS)

    obs = Observation(dss=config.DSS_FLAG_THRESHOLD + 0.1)
    new_state, action = sm.update(obs)

    assert new_state == States.ESCALATING
    assert action == "escalate"


def test_manual_reset_from_any_state():
    """Test that manual_reset always returns to LISTENING."""
    for state in States.ALL:
        sm = StateMachine(state=state)
        obs = Observation(dss=0.9, manual_reset=True)
        new_state, action = sm.update(obs)

        assert new_state == States.LISTENING
        assert action == "reset"
