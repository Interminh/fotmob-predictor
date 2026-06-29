from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import box

from src.config import DEFAULT_CONFIG, OUTPUTS_DIR
from src.engine.lambda_calculator import compute_lambdas
from src.engine.monte_carlo import simulate_match_raw, build_score_matrix, outcome_probabilities, top_n_scores
from src.engine.knockout_resolver import resolve_knockout
from src.engine.score_optimizer import optimize_prediction
from src.io.loader import load_team_profiles, load_tournament_schedule, load_scoring_rules, get_h2h_data
from src.io.exporter import export_results_json, export_results_csv, export_heatmap, export_advancement_json
from src.models.result import SimulationResult, ScoreEntry, OutcomeProbabilities, OptimalPrediction, KnockoutResolution

app = typer.Typer(name="worldcup", help="World Cup 2026 Monte Carlo Predictor")
console = Console()

logging.basicConfig(level=logging.WARNING)


def _load_all(
    profiles_path: Optional[Path] = None,
    schedule_path: Optional[Path] = None,
    rules_path: Optional[Path] = None,
):
    teams, h2h, profile_config = load_team_profiles(profiles_path)
    tournament = load_tournament_schedule(schedule_path)
    scoring_rules = load_scoring_rules(rules_path)
    config = {**DEFAULT_CONFIG, **profile_config}
    return teams, h2h, tournament, scoring_rules, config


def _simulate_match_full(
    home_code: str,
    away_code: str,
    match_id: str,
    stage_type: str,
    teams,
    h2h,
    tournament,
    scoring_rules,
    config,
    n: int,
    seed: Optional[int],
) -> SimulationResult:
    if home_code not in teams:
        raise typer.BadParameter(f"Unknown team code: {home_code}")
    if away_code not in teams:
        raise typer.BadParameter(f"Unknown team code: {away_code}")

    team_a = teams[home_code]
    team_b = teams[away_code]
    h2h_data = get_h2h_data(home_code, away_code, h2h)

    neutral = True
    for stage in tournament.stages:
        for m in stage.matches:
            if m.match_id == match_id:
                neutral = m.neutral_venue
                break

    lam_h, lam_a = compute_lambdas(team_a, team_b, tournament.host_nations, neutral, h2h_data, config)
    home_g, away_g = simulate_match_raw(lam_h, lam_a, n, seed)
    matrix = build_score_matrix(home_g, away_g, config["cap_display_goals"])
    out_probs = outcome_probabilities(home_g, away_g)
    top3 = top_n_scores(matrix, 3)
    opt = optimize_prediction(matrix, scoring_rules, config["cap_ev_goals"])

    ko_resolution = None
    if stage_type == "knockout":
        ko_raw = resolve_knockout(home_g, away_g, team_a.elo_rating, team_b.elo_rating, lam_h, lam_a, config, seed)
        score_ref = scoring_rules.get("score_reference_for_knockout", "90min")
        ko_resolution = KnockoutResolution(
            drawn_after_90min_probability=ko_raw["drawn_after_90min_probability"],
            drawn_after_120min_probability=ko_raw["drawn_after_120min_probability"],
            home_advances_probability=ko_raw["home_advances_probability"],
            away_advances_probability=ko_raw["away_advances_probability"],
            score_reference_used=score_ref,
        )

    return SimulationResult(
        match_id=match_id,
        home_team=home_code,
        away_team=away_code,
        lambda_home=round(lam_h, 4),
        lambda_away=round(lam_a, 4),
        simulations_run=n,
        top_3_scores=[ScoreEntry(s["score"], s["probability"]) for s in top3],
        outcome_probabilities=OutcomeProbabilities(**out_probs),
        optimal_prediction=OptimalPrediction(score=opt["optimal_score"], expected_points=opt["expected_points"]),
        score_matrix=matrix,
        knockout_resolution=ko_resolution,
    )


def _print_match_result(result: SimulationResult, home_name: str, away_name: str) -> None:
    title = f"{home_name} vs {away_name}  (lam_home={result.lambda_home}, lam_away={result.lambda_away}, N={result.simulations_run:,})"
    console.print(f"\n[bold cyan]{title}[/bold cyan]")

    table = Table(box=box.SIMPLE_HEAVY)
    table.add_column("Rank", style="bold")
    table.add_column("Score", style="green")
    table.add_column("Probability", style="yellow")
    for i, s in enumerate(result.top_3_scores, 1):
        table.add_row(str(i), s.score, f"{s.probability:.1%}")
    console.print(table)

    op = result.outcome_probabilities
    console.print(
        f"Outcome:  [green]Home {op.home_win:.0%}[/green] | "
        f"[yellow]Draw {op.draw:.0%}[/yellow] | "
        f"[red]Away {op.away_win:.0%}[/red]"
    )
    opt = result.optimal_prediction
    console.print(f"[bold yellow]* EV-Optimal Pick: {opt.score}  (expected points: {opt.expected_points:.2f})[/bold yellow]")

    if result.knockout_resolution:
        ko = result.knockout_resolution
        console.print(
            f"\nKnockout: drawn after 90' {ko.drawn_after_90min_probability:.1%} | "
            f"drawn after 120' {ko.drawn_after_120min_probability:.1%}"
        )
        console.print(
            f"Advances: [green]{home_name} {ko.home_advances_probability:.0%}[/green] | "
            f"[red]{away_name} {ko.away_advances_probability:.0%}[/red]  "
            f"(score ref: {ko.score_reference_used})"
        )


@app.command("predict-match")
def predict_match(
    home: str = typer.Argument(..., help="Home team code (e.g. ARG)"),
    away: str = typer.Argument(..., help="Away team code (e.g. FRA)"),
    stage: str = typer.Option("group", help="Stage type: group or knockout"),
    n: int = typer.Option(10_000, help="Number of simulations"),
    seed: Optional[int] = typer.Option(None, help="RNG seed for reproducibility"),
    heatmap: bool = typer.Option(False, help="Export score-matrix heatmap PNG"),
    json_out: bool = typer.Option(False, help="Export result as JSON"),
):
    """Predict a single match and display top-3 scores + EV-optimal pick."""
    teams, h2h, tournament, scoring_rules, config = _load_all()
    result = _simulate_match_full(
        home.upper(), away.upper(), f"{home}_{away}", stage, teams, h2h, tournament, scoring_rules, config, n, seed
    )
    _print_match_result(result, teams[home.upper()].name, teams[away.upper()].name)

    if heatmap:
        p = export_heatmap(result.score_matrix, home.upper(), away.upper(), result.match_id)
        console.print(f"\nHeatmap saved: [blue]{p}[/blue]")

    if json_out:
        p = export_results_json([result], OUTPUTS_DIR / f"match_{home}_{away}.json")
        console.print(f"JSON saved: [blue]{p}[/blue]")


@app.command("predict-group")
def predict_group(
    group: str = typer.Argument(..., help="Group name (e.g. 'Group A')"),
    n: int = typer.Option(10_000, help="Simulations per match"),
    seed: Optional[int] = typer.Option(None, help="RNG seed"),
    export: bool = typer.Option(False, help="Export predictions to CSV and JSON"),
):
    """Predict all matches in a group stage."""
    teams, h2h, tournament, scoring_rules, config = _load_all()

    target_stage = None
    for stage in tournament.stages:
        if stage.stage_name.lower() == group.lower() and stage.type == "group":
            target_stage = stage
            break

    if not target_stage:
        console.print(f"[red]Group '{group}' not found.[/red]")
        raise typer.Exit(1)

    results = []
    for match in target_stage.matches:
        if match.home.startswith("TBD") or match.away.startswith("TBD"):
            continue
        if match.status == "walkover":
            console.print(f"  [yellow]Skipping walkover: {match.match_id}[/yellow]")
            continue
        result = _simulate_match_full(
            match.home, match.away, match.match_id, "group",
            teams, h2h, tournament, scoring_rules, config, n, seed,
        )
        results.append(result)
        _print_match_result(result, teams[match.home].name, teams[match.away].name)

    if export and results:
        p1 = export_results_json(results, OUTPUTS_DIR / "group_stage_predictions.json")
        p2 = export_results_csv(results, OUTPUTS_DIR / "tournament_summary.csv")
        console.print(f"\nJSON: [blue]{p1}[/blue]")
        console.print(f"CSV:  [blue]{p2}[/blue]")


@app.command("predict-knockout")
def predict_knockout(
    stage_name: str = typer.Argument(..., help="Stage name (e.g. 'Round of 16')"),
    n: int = typer.Option(10_000, help="Simulations per match"),
    seed: Optional[int] = typer.Option(None, help="RNG seed"),
    export: bool = typer.Option(False, help="Export predictions"),
):
    """Predict all matches in a knockout stage (teams must be resolved — no TBD)."""
    teams, h2h, tournament, scoring_rules, config = _load_all()

    target_stage = None
    for stage in tournament.stages:
        if stage.stage_name.lower() == stage_name.lower() and stage.type == "knockout":
            target_stage = stage
            break

    if not target_stage:
        console.print(f"[red]Knockout stage '{stage_name}' not found.[/red]")
        raise typer.Exit(1)

    results = []
    for match in target_stage.matches:
        if match.home.startswith("TBD") or match.away.startswith("TBD"):
            console.print(f"  [dim]Skipping unresolved match {match.match_id}: {match.home} vs {match.away}[/dim]")
            continue
        if match.status == "walkover":
            continue
        result = _simulate_match_full(
            match.home, match.away, match.match_id, "knockout",
            teams, h2h, tournament, scoring_rules, config, n, seed,
        )
        results.append(result)
        _print_match_result(result, teams[match.home].name, teams[match.away].name)

    if export and results:
        p1 = export_results_json(results, OUTPUTS_DIR / "knockout_predictions.json")
        p2 = export_results_csv(results)
        console.print(f"\nJSON: [blue]{p1}[/blue]")
        console.print(f"CSV:  [blue]{p2}[/blue]")


@app.command("predict-tournament")
def predict_tournament(
    n_trials: int = typer.Option(100_000, help="Tournament-level simulation trials"),
    seed: Optional[int] = typer.Option(None, help="RNG seed"),
    top: int = typer.Option(10, help="Show top N teams by title probability"),
    export: bool = typer.Option(True, help="Export advancement probabilities"),
):
    """Run bracket simulator and report tournament advancement probabilities."""
    teams, h2h, tournament, scoring_rules, config = _load_all()

    from src.aggregation.bracket_simulator import simulate_tournament

    group_stages = [s for s in tournament.stages if s.type == "group"]
    knockout_stages = [s for s in tournament.stages if s.type == "knockout"]

    console.print(f"\n[bold]Running {n_trials:,} tournament simulations…[/bold]")
    adv = simulate_tournament(
        teams, h2h, group_stages, knockout_stages, tournament.host_nations, config, n_trials, seed
    )

    # Sort by title probability (winner key)
    winner_key = "final"
    sorted_teams = sorted(adv.items(), key=lambda x: x[1].get(winner_key, 0.0), reverse=True)

    table = Table(title="Tournament Advancement Probabilities", box=box.SIMPLE_HEAVY)
    table.add_column("Team", style="bold")
    table.add_column("Advance GS", style="cyan")
    table.add_column("Win Title", style="yellow")

    for code, probs in sorted_teams[:top]:
        name = teams[code].name if code in teams else code
        table.add_row(
            name,
            f"{probs.get('group_advance', 0):.1%}",
            f"{probs.get(winner_key, 0):.1%}",
        )
    console.print(table)

    if export:
        p = export_advancement_json(adv)
        console.print(f"\nAdvancement probabilities saved: [blue]{p}[/blue]")


@app.command("fetch-data")
def fetch_data(
    force_refresh: bool = typer.Option(False, help="Bypass cache and re-fetch everything"),
):
    """Fetch live fixtures and team stats from API-Football and update team_profiles.json."""
    from dotenv import load_dotenv
    load_dotenv()

    console.print("[bold]Fetching live data from API-Football…[/bold]")
    try:
        from src.data_ingestion.profile_builder import run_ingestion
        run_ingestion(force_refresh=force_refresh)
        console.print("[green]Data refresh complete.[/green]")
    except EnvironmentError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)
    except Exception as exc:
        console.print(f"[red]Ingestion failed: {exc}[/red]")
        raise typer.Exit(1)
