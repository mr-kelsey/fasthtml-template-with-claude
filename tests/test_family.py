from family import FAMILY_MEMBERS, get_member


def test_get_member_returns_matching_member():
    first_member = FAMILY_MEMBERS[0]
    assert get_member(first_member["id"]) == first_member


def test_get_member_returns_none_for_unknown_id():
    assert get_member("nonexistent") is None
