import pytest
from src.aggregation.group_standings import rank_group, TeamRecord


def _results(*args):
    """Helper: each arg is (home, away, hg, ag)."""
    return [{"home": h, "away": a, "home_goals": hg, "away_goals": ag} for h, a, hg, ag in args]


class TestRankGroup:
    def test_basic_ranking(self):
        results = _results(
            ("ARG", "FRA", 2, 0),
            ("ARG", "GER", 1, 0),
            ("FRA", "GER", 1, 1),
        )
        standings = rank_group(["ARG", "FRA", "GER"], results)
        assert standings[0].code == "ARG"
        assert standings[0].points == 6

    def test_goal_difference_tiebreaker(self):
        results = _results(
            ("A", "B", 1, 0),
            ("C", "D", 1, 0),
            ("A", "C", 0, 0),
            ("B", "D", 0, 0),
            ("A", "D", 0, 0),
            ("B", "C", 1, 0),
        )
        standings = rank_group(["A", "B", "C", "D"], results)
        # A: 5pts GD+1; B: 4pts GD=0 GF=1; C: 4pts GD=0 GF=1; D: 1pt
        # B and C tied on pts/GD/GF → H2H: B beat C → B ranks above C
        assert standings[0].code == "A"
        assert standings[1].code == "B"
        assert standings[-1].code == "D"

    def test_goals_for_tiebreaker(self):
        # A: 3pts GD=0 GF=2; B: 3pts GD=0 GF=3; C: 3pts GD=-1
        results = _results(
            ("A", "B", 2, 1),
            ("B", "C", 2, 1),
            ("A", "C", 0, 1),
        )
        standings = rank_group(["A", "B", "C"], results)
        # B: GF=3 GD=0; A: GF=2 GD=0; C: GF=2 GD=0
        # B is first (highest GF); A and C tied → H2H: C beat A → C second
        assert standings[0].code == "B"
        assert standings[1].code == "C"
        assert standings[2].code == "A"

    def test_all_teams_accounted_for(self):
        results = _results(
            ("X", "Y", 1, 1),
            ("X", "Z", 2, 0),
            ("Y", "Z", 0, 0),
        )
        standings = rank_group(["X", "Y", "Z"], results)
        assert len(standings) == 3
        codes = {s.code for s in standings}
        assert codes == {"X", "Y", "Z"}

    def test_team_record_properties(self):
        results = _results(
            ("A", "B", 3, 1),
            ("A", "C", 1, 1),
        )
        standings = rank_group(["A", "B", "C"], results)
        a = next(s for s in standings if s.code == "A")
        assert a.wins == 1
        assert a.draws == 1
        assert a.losses == 0
        assert a.goals_for == 4
        assert a.goals_against == 2
        assert a.goal_difference == 2
        assert a.points == 4
