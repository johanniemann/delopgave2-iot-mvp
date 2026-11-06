import pytest

from app.domain import DomainError, current_fault, require_case_gate, resolves_case


@pytest.mark.parametrize("value,fault", [(27.9,False), (28,False), (28.1,True), (0,False)])
def test_explicit_demo_rule_boundary(value, fault):
    result = current_fault([{"id": "r1", "value": value, "quality": "Usable"}])
    assert bool(result) is fault
    if fault:
        assert result["evidence"] == ["r1"]


def test_unusable_high_reading_cannot_raise_a_fault():
    assert current_fault([{"id":"r1", "value":99, "quality":"Invalid"}]) is None


@pytest.mark.parametrize("complete,verification,resolved", [(True,"Passed",True), (True,"Failed",False), (False,"Passed",False), (False,"Failed",False)])
def test_resolution_needs_both_conditions(complete, verification, resolved):
    assert resolves_case(complete, verification) is resolved


def test_rejected_risks_do_not_invalidate_a_completed_review():
    require_case_gate({"id":"incident"}, {"review_status":"Reviewed", "review":{"decisions":[]}})


@pytest.mark.parametrize("incident,forecast", [(None,None), ({"id":"i"},None), ({"id":"i"},{"review_status":"Pending"}), (None,{"review_status":"Reviewed"})])
def test_incomplete_case_gate_is_blocked(incident, forecast):
    with pytest.raises(DomainError):
        require_case_gate(incident, forecast)
