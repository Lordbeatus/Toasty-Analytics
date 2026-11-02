#!/usr/bin/env python3
"""
ToastyAnalytics CLI - Command-line interface for grading and analytics
"""

import json
from pathlib import Path

import click

from toastyanalytics.core.types import GradingDimension
from toastyanalytics.database.models import DatabaseManager
from toastyanalytics.graders import get_grader_for_dimension
from toastyanalytics.meta_learning.engine import MetaLearner


@click.group()
@click.option("--db-url", envvar="TOASTYANALYTICS_DB_URL", help="Database URL")
@click.pass_context
def cli(ctx, db_url):
    """ToastyAnalytics - AI Agent Self-Improvement System"""
    ctx.ensure_object(dict)
    ctx.obj["db_manager"] = DatabaseManager(db_url)
    ctx.obj["meta_learner"] = MetaLearner(ctx.obj["db_manager"])


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--user-id", required=True, help="User identifier")
@click.option("--language", default="python", help="Programming language")
@click.option(
    "--dimension", "-d", multiple=True, help="Grading dimensions (can specify multiple)"
)
@click.option("--output", "-o", type=click.File("w"), help="Output file (JSON)")
@click.pass_context
def grade(ctx, file, user_id, language, dimension, output):
    """
    Grade a code file

    Example:
        toastyanalytics grade myfile.py --user-id user123 -d code_quality -d speed
    """
    # Read code file
    code = Path(file).read_text()

    # Default to code_quality if no dimensions specified
    dimensions = list(dimension) if dimension else ["code_quality"]

    meta_learner = ctx.obj["meta_learner"]
    results = {}

    click.echo(f"Grading {file}...")
    click.echo(f"User: {user_id}")
    click.echo(f"Dimensions: {', '.join(dimensions)}\n")

    for dim_str in dimensions:
        try:
            dim = GradingDimension(dim_str)
        except ValueError:
            click.echo(f"Unknown dimension: {dim_str}", err=True)
            continue

        # Get grader
        grader = get_grader_for_dimension(dim)

        # Apply user's learned strategies
        meta_learner.apply_strategies_to_grader(grader, user_id)

        # Grade
        result = grader.grade(code=code, language=language)

        # Display results
        click.echo(f"{'='*60}")
        click.echo(f"{dim.value.upper()}")
        click.echo(f"{'='*60}")
        click.echo(
            f"Score: {result.score:.1f}/{result.max_score} ({result.percentage:.1f}%)"
        )
        click.echo("\n Feedback:")
        click.echo(f"{result.feedback}")

        if result.suggestions:
            click.echo("\n Suggestions:")
            for i, suggestion in enumerate(result.suggestions, 1):
                click.echo(f"{i}. [{suggestion.category}] {suggestion.description}")
                click.echo(f"Impact: {suggestion.expected_impact}")

        click.echo()

        results[dim.value] = result.to_dict()

    # Output JSON if requested
    if output:
        json.dump(results, output, indent=2)
        click.echo(f"\n Results saved to {output.name}")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option("--user-id", required=True, help="User identifier")
@click.option("--pattern", default="*.py", help="File pattern to match")
@click.option("--dimension", "-d", multiple=True, help="Grading dimensions")
@click.pass_context
def grade_all(ctx, directory, user_id, pattern, dimension):
    """
    Grade all files in a directory

    Example:
        toastyanalytics grade-all ./toastyanalytics --user-id user123 --pattern "*.py"
    """
    dir_path = Path(directory)
    files = list(dir_path.rglob(pattern))

    if not files:
        click.echo(f"No files matching '{pattern}' found in {directory}", err=True)
        return

    click.echo(f"Found {len(files)} files matching '{pattern}'")
    click.echo("Starting batch grading...\n")

    for i, file in enumerate(files, 1):
        click.echo(f"[{i}/{len(files)}] {file}")
        ctx.invoke(
            grade,
            file=str(file),
            user_id=user_id,
            language="python",
            dimension=dimension,
        )
        click.echo()


@cli.command()
@click.option("--user-id", required=True, help="User identifier")
@click.pass_context
def show_strategies(ctx, user_id):
    """
    Show learned strategies for a user

    Example:
        toastyanalytics show-strategies --user-id user123
    """
    meta_learner = ctx.obj["meta_learner"]
    strategies = meta_learner.get_user_strategies(user_id)

    if not strategies:
        click.echo(f"No learned strategies found for user {user_id}")
        return

    click.echo(f"Learned Strategies for {user_id}\n")
    click.echo(f"{'='*60}")

    for strategy_type, data in strategies.items():
        click.echo(f"\n {strategy_type.upper()}")
        click.echo(f"Effectiveness: {data['effectiveness']:.2%}")
        click.echo(f"Times Applied: {data['times_applied']}")

        if data.get("weights"):
            click.echo(f"Weights: {data['weights']}")
        if data.get("thresholds"):
            click.echo(f"Thresholds: {data['thresholds']}")
        if data.get("feedback_template"):
            click.echo(f"Feedback Style: {data['feedback_template']}")


@cli.command()
@click.option("--user-id", required=True, help="User identifier")
@click.option("--session-id", required=True, help="Session identifier")
@click.option("--score", type=float, help="Feedback score (0-10)")
@click.option("--too-detailed", is_flag=True, help="Feedback was too detailed")
@click.option("--want-more-detail", is_flag=True, help="Want more detailed feedback")
@click.pass_context
def feedback(ctx, user_id, session_id, score, too_detailed, want_more_detail):
    """
    Submit feedback on a grading session

    Example:
        toastyanalytics feedback --user-id user123 --session-id sess_abc --score 8
    """
    meta_learner = ctx.obj["meta_learner"]

    explicit_feedback = {}
    if too_detailed:
        explicit_feedback["too_detailed"] = True
    if want_more_detail:
        explicit_feedback["want_more_detail"] = True

    result = meta_learner.learn_from_session(
        user_id=user_id,
        session_id=session_id,
        user_feedback_score=score,
        explicit_feedback=explicit_feedback if explicit_feedback else None,
    )

    click.echo("Feedback submitted!")
    click.echo(f"Learning Status: {result['status']}")

    if result.get("updated_strategies"):
        click.echo(f"Updated {len(result['updated_strategies'])} strategies")
        for strategy in result["updated_strategies"]:
            click.echo(f"- {strategy['strategy_type']}")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=8000, help="Server port")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def serve(host, port, reload):
    """
    Start the HTTP API server

    Example:
        toastyanalytics serve --port 8000 --reload
    """
    import uvicorn

    from toastyanalytics.api import app

    click.echo("Starting ToastyAnalytics API...")
    click.echo(f"Server: http://{host}:{port}")
    click.echo(f"API Docs: http://{host}:{port}/docs")
    click.echo(f"Reload: {'Enabled' if reload else 'Disabled'}\n")

    uvicorn.run(app, host=host, port=port, reload=reload)


@cli.command()
@click.option("--user-id", help="Filter by user ID")
@click.option("--days", default=30, help="Number of days to analyze")
@click.pass_context
def stats(ctx, user_id, days):
    """
    Show analytics and statistics

    Example:
        toastyanalytics stats --user-id user123 --days 7
    """
    from datetime import datetime, timedelta

    from toastyanalytics.database.models import GradingHistory

    db_manager = ctx.obj["db_manager"]
    session = db_manager.get_session()

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = session.query(GradingHistory).filter(
            GradingHistory.timestamp >= cutoff_date
        )

        if user_id:
            query = query.filter(GradingHistory.user_id == user_id)

        gradings = query.all()

        if not gradings:
            click.echo(f"No data available for the last {days} days")
            return

        # Calculate statistics
        total = len(gradings)
        avg_score = sum(g.percentage for g in gradings) / total

        # Dimension breakdown
        from collections import defaultdict

        dim_scores = defaultdict(list)
        for g in gradings:
            dim_scores[g.dimension].append(g.percentage)

        click.echo("Analytics Report")
        click.echo(f"{'='*60}")
        click.echo(f"Period: Last {days} days")
        if user_id:
            click.echo(f"User: {user_id}")
        click.echo("\n Overall Statistics")
        click.echo(f"Total Gradings: {total}")
        click.echo(f"Average Score: {avg_score:.1f}%")

        click.echo("\n By Dimension:")
        for dim, scores in sorted(dim_scores.items()):
            avg = sum(scores) / len(scores)
            click.echo(f"{dim:20} {avg:5.1f}% ({len(scores)} gradings)")

    finally:
        session.close()


if __name__ == "__main__":
    cli(obj={})
