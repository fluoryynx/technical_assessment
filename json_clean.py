from typing import Any, Dict, List, Tuple

def validate_tool_call(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:

    # reject non-dict payloads early
    if not isinstance(payload, dict):
        return {}, ["Payload must be a dictionary"]
    
    errors: List[str] = []
    clean: Dict[str, Any] = {}

    VALID_ACTIONS = {"search", "answer"}

    # Validate 'action'
    raw_action = payload.get("action")
    if raw_action is None:
        errors.append("Missing required field: 'action'.")
        return {}, errors

    if isinstance(raw_action, str):
        action = raw_action.strip()
    else:
        errors.append(f"Invalid type for 'action': expected str, got {type(raw_action).__name__}.")
        return {}, errors

    if action not in VALID_ACTIONS:
        errors.append(f"Invalid value for 'action': '{action}'. Must be 'search' or 'answer'.")
        return {}, errors

    clean["action"] = action

    # Validate 'k' (optional, default 3) 
    raw_k = payload.get("k", 3)
    if isinstance(raw_k, bool):
        errors.append("Invalid type for 'k': bool is not allowed.")
        k = 3  # fall back to default; non-fatal
    elif isinstance(raw_k, int):
        k = raw_k
    elif isinstance(raw_k, str):
        try:
            k = int(raw_k.strip())
        except ValueError:
            errors.append(f"Cannot coerce 'k' value '{raw_k}' to int; using default 3.")
            k = 3
    elif isinstance(raw_k, float) and raw_k.is_integer():
        k = int(raw_k)
    else:
        errors.append(f"Invalid type for 'k': expected int, got {type(raw_k).__name__}; using default 3.")
        k = 3

    if not (1 <= k <= 5):
        errors.append(f"'k' value {k} out of range [1, 5]; clamping to default 3.")
        k = 3

    clean["k"] = k

    # Validate 'q' 
    if action == "search":
        raw_q = payload.get("q")
        if raw_q is None:
            errors.append("Missing required field: 'q' when action is 'search'.")
            return {}, errors

        if not isinstance(raw_q, str):
            errors.append(f"Invalid type for 'q': expected str, got {type(raw_q).__name__}.")
            return {}, errors

        q = raw_q.strip()
        if not q:
            errors.append("Field 'q' must be a non-empty string.")
            return {}, errors

        clean["q"] = q

    # if action == "answer": silently ignore 'q' if present

    return clean, errors


######## test cases ######### 

# Valid cases
def test_valid_search_payload():
    payload = {
        "action": "search",
        "q": "refund policy",
        "k": 2
    }

    clean, errors = validate_tool_call(payload)

    assert errors == []
    assert clean == {
        "action": "search",
        "q": "refund policy",
        "k": 2
    }
    print("test_valid_search_payload passed")


def test_valid_search_with_string_k():
    payload = {
        "action": "search",
        "q": "refund policy",
        "k": "4"
    }

    clean, errors = validate_tool_call(payload)

    assert errors == []
    assert clean["k"] == 4
    print("test_valid_search_with_string_k passed")


def test_trim_strings():
    payload = {
        "action": " search ",
        "q": " refund policy ",
        "k": " 3 "
    }

    clean, errors = validate_tool_call(payload)

    assert errors == []
    assert clean == {
        "action": "search",
        "q": "refund policy",
        "k": 3
    }
    print("test_trim_strings passed")


def test_default_k_value():
    payload = {
        "action": "search",
        "q": "refund policy"
    }

    clean, errors = validate_tool_call(payload)

    assert errors == []
    assert clean["k"] == 3
    print("test_default_k_value passed")


def test_ignore_unknown_fields():
    payload = {
        "action": "search",
        "q": "refund policy",
        "extra": "should be removed"
    }

    clean, errors = validate_tool_call(payload)

    assert "extra" not in clean
    print("test_ignore_unknown_fields passed")


def test_answer_action_ignores_q():
    payload = {
        "action": "answer",
        "q": "this should be ignored"
    }

    clean, errors = validate_tool_call(payload)

    assert clean["action"] == "answer"
    assert "q" not in clean
    print("test_answer_action_ignores_q passed")


# Fatal errors

def test_missing_action():
    payload = {
        "q": "hello"
    }

    clean, errors = validate_tool_call(payload)

    assert clean == {}
    assert len(errors) > 0
    print("test_missing_action passed")


def test_invalid_action():
    payload = {
        "action": "delete",
        "q": "test"
    }

    clean, errors = validate_tool_call(payload)

    assert clean == {}
    assert len(errors) > 0
    print("test_invalid_action passed")


def test_search_missing_q():
    payload = {
        "action": "search"
    }

    clean, errors = validate_tool_call(payload)

    assert clean == {}
    assert len(errors) > 0
    print("test_search_missing_q passed")


def test_search_empty_q():
    payload = {
        "action": "search",
        "q": "   "
    }

    clean, errors = validate_tool_call(payload)

    assert clean == {}
    assert len(errors) > 0
    print("test_search_empty_q passed")


# Non-fatal k errors
def test_k_out_of_range():
    payload = {
        "action": "search",
        "q": "test",
        "k": 10
    }

    clean, errors = validate_tool_call(payload)

    assert clean["k"] == 3
    assert len(errors) == 1
    print("test_k_out_of_range passed")


def test_k_invalid_string():
    payload = {
        "action": "search",
        "q": "test",
        "k": "abc"
    }

    clean, errors = validate_tool_call(payload)

    assert clean["k"] == 3
    assert len(errors) == 1
    print("test_k_invalid_string passed")


def test_k_bool_invalid():
    payload = {
        "action": "search",
        "q": "test",
        "k": True
    }

    clean, errors = validate_tool_call(payload)

    assert clean["k"] == 3
    assert len(errors) == 1
    print("test_k_bool_invalid passed")


# Mixed: non-fatal k error + fatal q error


def test_bool_k_and_missing_q():
    """
    bool k triggers a non-fatal warning, but missing q is fatal.
    Expect: ({}, errors) with both errors reported.
    """
    payload = {"action": "search", "k": True}
    clean, errors = validate_tool_call(payload)

    assert clean == {}
    assert any("bool" in e.lower() or "'k'" in e for e in errors)   # k error present
    assert any("'q'" in e for e in errors)                           # q error present
    assert len(errors) == 2
    print("test_bool_k_and_missing_q passed")


# edge cases


def test_non_dict_payload():
    """Payload is not a dict at all."""
    clean, errors = validate_tool_call("action=search")

    assert clean == {}
    assert len(errors) > 0
    print("test_non_dict_payload passed")


def test_action_is_none_explicitly():
    """action key exists but value is None."""
    payload = {"action": None, "q": "test"}
    clean, errors = validate_tool_call(payload)

    assert clean == {}
    assert len(errors) > 0
    print("test_action_is_none_explicitly passed")


def test_action_is_integer():
    """action is an integer, not a string."""
    payload = {"action": 1, "q": "test"}
    clean, errors = validate_tool_call(payload)

    assert clean == {}
    assert len(errors) > 0
    print("test_action_is_integer passed")


def test_action_case_sensitive():
    """'Search' (capitalized) should be rejected — schema requires lowercase."""
    payload = {"action": "Search", "q": "test"}
    clean, errors = validate_tool_call(payload)

    assert clean == {}
    assert len(errors) > 0
    print("test_action_case_sensitive passed")


def test_q_is_only_whitespace_multiline():
    """q contains only newlines/tabs — still counts as empty after strip."""
    payload = {"action": "search", "q": "\n\t\n"}
    clean, errors = validate_tool_call(payload)

    assert clean == {}
    assert len(errors) > 0
    print("test_q_is_only_whitespace_multiline passed")


def test_k_as_float_whole_number():
    """k=3.0 is a whole-number float — should coerce to int 3."""
    payload = {"action": "search", "q": "test", "k": 3.0}
    clean, errors = validate_tool_call(payload)

    assert errors == []
    assert clean["k"] == 3
    assert isinstance(clean["k"], int)
    print("test_k_as_float_whole_number passed")


def test_k_as_float_fractional():
    """k=2.7 is not a whole number — should error and fall back to 3."""
    payload = {"action": "search", "q": "test", "k": 2.7}
    clean, errors = validate_tool_call(payload)

    assert clean["k"] == 3
    assert len(errors) == 1
    print("test_k_as_float_fractional passed")


def test_k_as_false_bool():
    """k=False — bool guard catches it; int(False)=0 would fail range anyway."""
    payload = {"action": "search", "q": "test", "k": False}
    clean, errors = validate_tool_call(payload)

    assert clean["k"] == 3
    assert len(errors) == 1
    print("test_k_as_false_bool passed")


def test_k_boundary_values():
    """k=1 and k=5 are the inclusive boundary values — both should pass."""
    for boundary in [1, 5]:
        clean, errors = validate_tool_call({"action": "search", "q": "test", "k": boundary})
        assert errors == []
        assert clean["k"] == boundary
    print("test_k_boundary_values passed")


def test_empty_payload():
    """Completely empty dict — action is missing, fatal error."""
    clean, errors = validate_tool_call({})

    assert clean == {}
    assert len(errors) > 0
    print("test_empty_payload passed")


def test_answer_with_no_fields_beyond_action():
    """Minimal valid answer payload — no q, no k."""
    clean, errors = validate_tool_call({"action": "answer"})

    assert errors == []
    assert clean == {"action": "answer", "k": 3}
    assert "q" not in clean
    print("test_answer_with_no_fields_beyond_action passed")


test_valid_search_payload()
test_valid_search_with_string_k()
test_trim_strings()
test_default_k_value()
test_ignore_unknown_fields()
test_answer_action_ignores_q()
test_missing_action()
test_invalid_action()
test_search_missing_q()
test_search_empty_q()
test_k_out_of_range()
test_k_invalid_string()
test_k_bool_invalid()
test_bool_k_and_missing_q()
test_bool_k_and_missing_q()
test_non_dict_payload()
test_action_is_none_explicitly()
test_action_is_integer()
test_action_case_sensitive()
test_q_is_only_whitespace_multiline()
test_k_as_float_whole_number()
test_k_as_float_fractional()
test_k_as_false_bool()
test_k_boundary_values()
test_empty_payload()
test_answer_with_no_fields_beyond_action()
