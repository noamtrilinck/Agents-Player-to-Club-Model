"""
Different-country destination rule -- documented and stubbed in Stage 1,
NOT wired into any filtering yet.

Rule (approved as part of Stage 1 scope, per the project's core objective):
a recommendation must be for a club competing in a DIFFERENT LEAGUE COUNTRY
from the player's current club.

Canonical project definition (2026-08 semantic correction): "country" here
ALWAYS means the country of the LEAGUE a club competes in
(`leagues.country_id`), never a club's own nationality/geographic identity
(`teams.country_id`). This project's recruitment question is "is the
destination club in a different national league system," not "is the club's
own hometown/nationality in a different country." Concretely: a player
currently at Swansea City (Wales, but competing in England's league system)
moving to another England-league club is SAME-country under this rule, even
though Swansea is geographically Welsh -- and a move to FC Andorra (which
competes in Spain's league system) is a Spain-country destination, not an
Andorra-country one. See docs/stage1_scope_and_eligibility.md's
"Canonical club country = league country" section for the full rationale and
worked examples.

This project's core objective is to recommend a player's next move abroad --
so every candidate club considered for a given player must compete in a
league-country different from that player's current club's league-country.
This module exists now purely to record that rule in code (and give it one
obvious, testable home) so it is not lost or reinvented differently later. It
is intentionally NOT called from build_candidate_clubs.py or anywhere else
yet -- applying it requires a specific player's current-club league-country,
which is a recommendation-engine-time input (Stage 7), not a property of the
static candidate-club universe built in Stage 1.
"""


def is_cross_country_candidate(player_current_league_country_id, candidate_club_league_country_id):
    """True if a candidate club's LEAGUE country differs from the player's current
    club's LEAGUE country. Both arguments are `leagues.country_id` values (via
    `leagues.country_id` -> `countries.country_id`) -- NEVER `teams.country_id` (a
    club's own nationality/geographic identity, which this project deliberately does
    not use for country logic; see the module docstring). Returns False (not a valid
    candidate) if either id is missing -- missing country data must never silently
    pass this check."""
    if player_current_league_country_id is None or candidate_club_league_country_id is None:
        return False
    return player_current_league_country_id != candidate_club_league_country_id
