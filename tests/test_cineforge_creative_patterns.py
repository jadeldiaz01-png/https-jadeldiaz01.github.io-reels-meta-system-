from cineforge.creative_patterns import ConceptSignals, choose_pattern, validate_pattern_traits


def test_physical_risk_takes_priority_for_spatial_safety():
    pattern = choose_pattern(ConceptSignals(has_physical_risk=True, has_comedic_failure=True))
    assert pattern.family == "physical_risk_action"
    assert "spatial_context" in pattern.required_traits


def test_animal_pattern_requires_identity_and_expression_readability():
    pattern = choose_pattern(ConceptSignals(has_animal=True))
    assert pattern.family == "animal_expression"
    errors = validate_pattern_traits(pattern, ["identity_consistency", "eye_detail"])
    assert "missing:fur_feather_detail" in errors
    assert "missing:expression_readability" in errors


def test_sports_pattern_requires_contact_physics():
    pattern = choose_pattern(ConceptSignals(has_sports_action=True))
    assert pattern.family == "sports_payoff"
    errors = validate_pattern_traits(pattern, ["trajectory_visibility", "biomechanics", "payoff_hold"])
    assert errors == ["missing:contact_physics"]


def test_good_comedic_fail_traits_pass():
    pattern = choose_pattern(ConceptSignals(has_comedic_failure=True))
    errors = validate_pattern_traits(
        pattern,
        ["expectation_setup", "causal_clarity", "reaction_or_consequence", "loopability"],
    )
    assert errors == []
