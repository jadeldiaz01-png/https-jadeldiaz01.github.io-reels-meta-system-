from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal


PatternFamily = Literal[
    "physical_risk_action",
    "animal_expression",
    "human_reaction",
    "transformation_reveal",
    "sports_payoff",
    "comedic_fail",
]


@dataclass(frozen=True)
class CreativePattern:
    family: PatternFamily
    hook: str
    escalation: str
    payoff: str
    camera_bias: str
    motion_bias: str
    audio_bias: str
    text_dependency: str
    ideal_duration_seconds: tuple[float, float]
    required_traits: tuple[str, ...]
    forbidden_traits: tuple[str, ...] = ()


PATTERNS: dict[PatternFamily, CreativePattern] = {
    "physical_risk_action": CreativePattern(
        family="physical_risk_action",
        hook="show the risky or unusual physical setup immediately",
        escalation="preserve spatial geography and anticipation before the action",
        payoff="complete the physical action and hold long enough for consequence/reaction",
        camera_bias="stable wide/medium geography, then tighter reaction only when motivated",
        motion_bias="natural high-motion with clear trajectory and contact physics",
        audio_bias="location ambience plus synchronized impacts/splashes/foley",
        text_dependency="none",
        ideal_duration_seconds=(10.0, 24.0),
        required_traits=("clear_subject", "spatial_context", "natural_motion", "physics_coherence"),
        forbidden_traits=("fake_injury_bait", "unsafe_instruction"),
    ),
    "animal_expression": CreativePattern(
        family="animal_expression",
        hook="introduce the animal and the unusual behavior or expression in the first beat",
        escalation="move from behavior to readable face/body reaction",
        payoff="hold the strongest expression/reaction rather than cutting away early",
        camera_bias="medium-to-close progression with eye-line readable and background uncluttered",
        motion_bias="small natural movements; avoid synthetic facial morphing",
        audio_bias="natural animal/location sound; music secondary",
        text_dependency="optional-minimal",
        ideal_duration_seconds=(8.0, 18.0),
        required_traits=("identity_consistency", "eye_detail", "fur_feather_detail", "expression_readability"),
        forbidden_traits=("anthropomorphic_face_warp", "duplicated_limbs"),
    ),
    "human_reaction": CreativePattern(
        family="human_reaction",
        hook="establish the interaction and emotional premise immediately",
        escalation="preserve cause before reaction so the viewer understands why it matters",
        payoff="prioritize authentic facial/body reaction and a short after-beat",
        camera_bias="locked or gently handheld medium shot with reaction close-up only if continuity permits",
        motion_bias="natural performance with restrained camera movement",
        audio_bias="dialogue/room tone first; music must not mask reaction",
        text_dependency="optional",
        ideal_duration_seconds=(9.0, 22.0),
        required_traits=("face_consistency", "eyeline_continuity", "cause_effect_clarity", "reaction_hold"),
        forbidden_traits=("identity_drift", "lip_sync_failure"),
    ),
    "transformation_reveal": CreativePattern(
        family="transformation_reveal",
        hook="show the before-state and an obvious unresolved visual question",
        escalation="delay the full reveal while maintaining object/scene continuity",
        payoff="clean reveal with visible before/after relationship",
        camera_bias="repeatable framing or match-on-action to make transformation legible",
        motion_bias="controlled; transformation may be dynamic but camera should remain readable",
        audio_bias="build then release; use a motivated reveal impact",
        text_dependency="minimal",
        ideal_duration_seconds=(8.0, 20.0),
        required_traits=("before_after_legibility", "object_persistence", "match_geometry", "reveal_timing"),
        forbidden_traits=("unmotivated_object_spawn", "continuity_jump"),
    ),
    "sports_payoff": CreativePattern(
        family="sports_payoff",
        hook="show the setup and target immediately",
        escalation="maintain full-body/trajectory visibility during attempt",
        payoff="retain completion and reaction; replay only when additive",
        camera_bias="wide enough for biomechanics and target, minimal reframing during action",
        motion_bias="high-motion with strong temporal coherence and accurate contact",
        audio_bias="impact/landing/ambient crowd or room sound synchronized to event",
        text_dependency="none",
        ideal_duration_seconds=(8.0, 24.0),
        required_traits=("trajectory_visibility", "biomechanics", "contact_physics", "payoff_hold"),
        forbidden_traits=("body_warp", "teleport_motion"),
    ),
    "comedic_fail": CreativePattern(
        family="comedic_fail",
        hook="show the normal expectation before the failure",
        escalation="preserve timing and causality; do not over-cut",
        payoff="the failure/reversal must be visually understandable in one viewing",
        camera_bias="simple observational framing; reaction can become the final beat",
        motion_bias="natural timing over exaggerated synthetic motion",
        audio_bias="realistic foley/impact plus optional restrained comedic accent",
        text_dependency="none-to-minimal",
        ideal_duration_seconds=(7.0, 18.0),
        required_traits=("expectation_setup", "causal_clarity", "reaction_or_consequence", "loopability"),
        forbidden_traits=("humiliation_targeting", "graphic_harm"),
    ),
}


@dataclass(frozen=True)
class ConceptSignals:
    has_animal: bool = False
    has_human_reaction: bool = False
    has_physical_risk: bool = False
    has_sports_action: bool = False
    has_transformation: bool = False
    has_comedic_failure: bool = False


def choose_pattern(signals: ConceptSignals) -> CreativePattern:
    # Deterministic priority: safety/geography-sensitive action first, then the core payoff type.
    if signals.has_physical_risk:
        return PATTERNS["physical_risk_action"]
    if signals.has_sports_action:
        return PATTERNS["sports_payoff"]
    if signals.has_transformation:
        return PATTERNS["transformation_reveal"]
    if signals.has_animal:
        return PATTERNS["animal_expression"]
    if signals.has_human_reaction:
        return PATTERNS["human_reaction"]
    if signals.has_comedic_failure:
        return PATTERNS["comedic_fail"]
    return PATTERNS["human_reaction"]


def validate_pattern_traits(pattern: CreativePattern, observed_traits: Iterable[str]) -> list[str]:
    observed = set(observed_traits)
    missing = [trait for trait in pattern.required_traits if trait not in observed]
    present_forbidden = [trait for trait in pattern.forbidden_traits if trait in observed]
    return [f"missing:{x}" for x in missing] + [f"forbidden:{x}" for x in present_forbidden]
