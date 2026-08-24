"""
Stage 4, Sprint 4.4 -- Opponent-adjustability classification of the 30 LOCKED CORE Team
Environment features (production/club_pattern_model/locked_team_environment_features.py).

Per the explicit Sprint 4.4 instruction: "Do not assume every Team Style feature should be
adjusted." Every one of the 30 CORE features is classified into exactly one of:

  OPPONENT-ADJUSTABLE -- there is a meaningful concept of what the opponent normally
      allows/induces for this feature (an attacking output the opponent's defense
      typically concedes, or a defensive outcome the opponent's own attacking tendency
      typically induces in whoever plays them).
  TEAM-INTRINSIC -- opponent adjustment would not make football/mathematical sense: the
      feature describes a STYLE CHOICE (how the team chooses to play), not an outcome the
      opponent meaningfully shapes.
  REVIEW -- plausibly adjustable but requires a methodological judgment call this sprint
      does not force (see each entry's `note`).

This classification does not, by itself, decide which features get an actual candidate
opponent-relative dataset built (see build_opponent_relative_features.py's
SELECTED_FOR_CANDIDATE_BUILD -- a deliberately narrower, representative subset spanning every
family and both directions of adjustment, per the explicit instruction not to blindly
opponent-adjust all 30).
"""

OPPONENT_ADJUSTABLE = "OPPONENT-ADJUSTABLE"
TEAM_INTRINSIC = "TEAM-INTRINSIC"
REVIEW = "REVIEW"

# (feature_name, family, classification, football-interpretation note)
CLASSIFICATION = [
    # --- Game Control ---
    ("Pass Accuracy", "Game Control", OPPONENT_ADJUSTABLE,
     "How cleanly a team completes passes is shaped by the opposing press: some opponents "
     "let teams pass freely, others force miscompletions. Opponent baseline = what pass "
     "accuracy this opponent's OTHER opponents typically achieve against them."),
    ("Backward Pass Rate", "Game Control", TEAM_INTRINSIC,
     "A ball-circulation STYLE choice (how much a team recycles possession backward), not "
     "primarily an outcome the opponent forces. A high press could nudge this up, but the "
     "feature is fundamentally about the team's own game-management approach."),
    ("Long Ball Rate", "Game Control", TEAM_INTRINSIC,
     "A directness STYLE choice -- some teams choose to play long regardless of opponent. "
     "Not classified REVIEW: unlike Long Ball Success (an outcome), the RATE at which a "
     "team attempts long balls is a tactical preference set by the team's own gameplan."),
    ("Long Ball Success", "Game Control", OPPONENT_ADJUSTABLE,
     "Once a team chooses to play long, whether it succeeds depends heavily on the "
     "opponent's aerial/defensive ability to contest long balls. Opponent baseline = long "
     "ball success typically achieved against this opponent."),
    ("Possession Loss Rate", "Game Control", OPPONENT_ADJUSTABLE,
     "How often a team loses the ball per touch is directly shaped by the opponent's "
     "pressing intensity. Opponent baseline = possession-loss rate this opponent typically "
     "induces in whoever plays them."),
    ("Progressive Passing Preference", "Game Control", TEAM_INTRINSIC,
     "A structural-passing-vs-long-ball STYLE ratio -- describes HOW a team chooses to "
     "progress the ball, not an opponent-forced outcome."),

    # --- Chance Creation ---
    ("Final Third Progression Rate", "Chance Creation", REVIEW,
     "Plausibly opponent-adjustable (a deep, compact opponent block makes final-third entry "
     "harder) but also reflects the team's own buildup patience/directness -- a genuine mix "
     "of style and opponent resistance; needs a judgment call this sprint does not force."),
    ("Key Pass Rate", "Chance Creation", OPPONENT_ADJUSTABLE,
     "Chance creation volume is shaped by how much space/time the opponent's defensive "
     "shape concedes. Opponent baseline = key-pass rate typically produced against this "
     "opponent."),
    ("Dribble Rate", "Chance Creation", TEAM_INTRINSIC,
     "How often a team ATTEMPTS dribbles is primarily a stylistic choice (some teams build "
     "their identity around 1v1 carrying), distinct from whether those attempts succeed."),
    ("Dribble Success", "Chance Creation", OPPONENT_ADJUSTABLE,
     "Once a dribble is attempted, whether it succeeds depends on the opponent's tackling "
     "ability. Opponent baseline = dribble success typically achieved against this opponent."),
    ("Cross Rate", "Chance Creation", TEAM_INTRINSIC,
     "A wide-play STYLE preference -- some teams build around crossing regardless of "
     "opponent, others rarely cross by design."),
    ("Cross Accuracy", "Chance Creation", OPPONENT_ADJUSTABLE,
     "Whether crosses find a teammate depends on the opponent's aerial/box defending. "
     "Opponent baseline = cross accuracy typically achieved against this opponent."),
    ("Key Pass Conversion", "Chance Creation", REVIEW,
     "Blends chance-creation quality (team-controlled: how good the pass is) with the "
     "opponent's defensive shape at the moment of the pass -- a genuine mix, not cleanly "
     "assignable to either side without a modelling judgment call."),
    ("Assist Conversion", "Chance Creation", REVIEW,
     "Blends creation quality with the TEAM's OWN finishing (assists depend on a teammate "
     "scoring), which is a team-intrinsic factor entangled with any opponent defensive "
     "effect -- a mixed metric, not cleanly opponent-adjustable alone."),
    ("Verticality Index", "Chance Creation", TEAM_INTRINSIC,
     "A forward-vs-backward progression STYLE ratio -- describes the team's own approach, "
     "not an opponent-forced outcome."),

    # --- Finishing ---
    ("Goal Conversion", "Finishing", OPPONENT_ADJUSTABLE,
     "The canonical opponent-adjustable metric: how many of a team's shots become goals is "
     "heavily shaped by the opposing defense/goalkeeping. Opponent baseline = goal "
     "conversion typically allowed by this opponent."),
    ("Shot Accuracy", "Finishing", REVIEW,
     "A genuine mix: shot SELECTION (the team's own decision of when/where to shoot) drives "
     "on-target rate as much as opponent pressure at the moment of the shot -- included here "
     "specifically as a documented REVIEW case, not resolved either way this sprint."),
    ("Shot Patience", "Finishing", TEAM_INTRINSIC,
     "A decision-making STYLE ratio (shoot early vs develop the attack first) -- the team's "
     "own choice, not an opponent-forced outcome."),

    # --- Defending ---
    ("Tackle Success", "Defending", OPPONENT_ADJUSTABLE,
     "How often tackles succeed depends on the opponent's ball-carrying/dribbling ability. "
     "Opponent baseline = tackle success typically achieved by whoever plays this opponent "
     "(i.e. is this opponent generally easy or hard to dispossess)."),
    ("Duel Success", "Defending", OPPONENT_ADJUSTABLE,
     "Duel outcomes depend on the opponent's own physical/technical duel strength. Opponent "
     "baseline = duel success typically achieved against this opponent."),
    ("Aerial Success", "Defending", OPPONENT_ADJUSTABLE,
     "Aerial-duel outcomes depend on the opponent's aerial threat. Opponent baseline = "
     "aerial success typically achieved against this opponent."),
    ("Dribbled Past Rate", "Defending", OPPONENT_ADJUSTABLE,
     "Whether a team gets dribbled past depends heavily on the opponent's dribbling ability, "
     "not only the team's own defending. Opponent baseline = dribbled-past rate this "
     "opponent's ball-carriers typically induce in whoever defends them."),
    ("Interception Preference", "Defending", TEAM_INTRINSIC,
     "A defensive-METHOD style ratio (anticipate vs tackle) -- describes HOW a team defends, "
     "not how effectively, so an opponent baseline for 'preference' is not a meaningful "
     "construction (a preference is not something an opponent 'allows')."),
    ("Clearance Preference", "Defending", TEAM_INTRINSIC,
     "Same reasoning as Interception Preference -- a defensive-method style choice, not an "
     "opponent-induced outcome."),

    # --- Pressing Actions ---
    ("Defensive Action Rate", "Pressing Actions", OPPONENT_ADJUSTABLE,
     "IMPORTANT CAVEAT: the raw feature's own formula "
     "((ball_recoveries+tackles+interceptions)/opponent_passes) already normalizes by THIS "
     "fixture's own opponent pass volume -- a fixture-level opponent adjustment is already "
     "baked in. A further opponent-relative layer here asks a DIFFERENT question: is this "
     "rate high/low relative to what THIS SPECIFIC opponent's passing tempo typically induces "
     "across ALL its matches (not just this one) -- i.e. does this opponent generally invite "
     "or resist pressing, beyond this one match's raw pass count. Not redundant with the raw "
     "formula's own denominator, but the two must never be conflated as the same adjustment."),
    ("Ball Recovery Rate", "Pressing Actions", OPPONENT_ADJUSTABLE,
     "Same caveat as Defensive Action Rate -- fixture-level opponent-pass normalization is "
     "already in the raw formula; a season-level opponent-relative layer asks a different, "
     "additional question (see Defensive Action Rate's note)."),
    ("Interception Rate vs Opponent Passes", "Pressing Actions", OPPONENT_ADJUSTABLE,
     "Same caveat as Defensive Action Rate."),
    ("Pressure Intensity Ratio", "Pressing Actions", TEAM_INTRINSIC,
     "Describes the CONSISTENCY of the team's OWN pressing effort across a match (peak vs "
     "average), not an opponent-induced outcome -- a team-intrinsic pressing-management "
     "trait."),
    ("Ball-Winning Preference", "Pressing Actions", TEAM_INTRINSIC,
     "A ball-winning-METHOD style ratio (recoveries vs tackles vs interceptions), describing "
     "HOW a team wins the ball back, not an opponent-forced outcome."),
    ("Recovery Preference", "Pressing Actions", TEAM_INTRINSIC,
     "Same reasoning as Ball-Winning Preference -- a defensive-method style choice."),
]

assert len(CLASSIFICATION) == 30

OPPONENT_ADJUSTABLE_FEATURES = [f for f, _, c, _ in CLASSIFICATION if c == OPPONENT_ADJUSTABLE]
TEAM_INTRINSIC_FEATURES = [f for f, _, c, _ in CLASSIFICATION if c == TEAM_INTRINSIC]
REVIEW_FEATURES = [f for f, _, c, _ in CLASSIFICATION if c == REVIEW]


if __name__ == "__main__":
    print(f"OPPONENT-ADJUSTABLE ({len(OPPONENT_ADJUSTABLE_FEATURES)}): {OPPONENT_ADJUSTABLE_FEATURES}")
    print(f"TEAM-INTRINSIC ({len(TEAM_INTRINSIC_FEATURES)}): {TEAM_INTRINSIC_FEATURES}")
    print(f"REVIEW ({len(REVIEW_FEATURES)}): {REVIEW_FEATURES}")
