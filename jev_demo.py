"""
jev_demo.py - Interactive CLI tool for TypeSafe AI Jev System One Model.

Provides:
1. Environment & API key status check
2. Live interactive testing against the Jev model (with TYPESAFE_API_KEY)
3. Simulated dry-run mode for trying out the SDK architecture before getting an API key
"""

import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

load_dotenv()
console = Console()

def print_banner():
    console.print(
        Panel.fit(
            "[bold cyan]TypeSafe AI - Jev (System One Model) Playground[/bold cyan]\n"
            "[white]Fast, non-autoregressive, calibrated decision-making for software systems.[/white]",
            border_style="cyan"
        )
    )

def check_env():
    api_key = os.getenv("TYPESAFE_API_KEY")
    if not api_key or api_key == "your_typesafe_api_key_here":
        return None
    return api_key

def run_live_test(text: str):
    from typesafe_sdk import TypeSafeClient, Choice, Noul, Score, TypeSafeError

    questions = {
        "intent": Choice(
            instructions="Identify the primary intent of this statement.",
            criteria={
                "inquiry": "Asking for information or clarification",
                "complaint": "Expressing dissatisfaction, bugs, or problems",
                "request_action": "Asking for a specific action, refund, change, or purchase",
                "feedback": "Providing general observations or feedback"
            }
        ),
        "is_negative_sentiment": Noul(
            instructions="Does this statement convey an unhappy or dissatisfied sentiment?"
        ),
        "priority_level": Score(
            instructions="Determine the operational priority level for handling this text.",
            criteria=["low", "medium", "high", "urgent"]
        )
    }

    try:
        with TypeSafeClient() as client:
            response = client.system_one(
                state={"text": text},
                questions=questions
            )

        render_results(response, text, is_simulation=False)
    except TypeSafeError as e:
        console.print(f"[bold red]API Error:[/bold red] {e}")

def run_simulation(text: str):
    """Provides a realistic simulation when API key is not configured."""
    text_lower = text.lower()
    
    # Simple heuristic mock for simulation
    is_neg = any(w in text_lower for w in ["bad", "terrible", "broken", "angry", "double", "fail", "slow", "wrong"])
    urgent = any(w in text_lower for w in ["urgent", "asap", "immediately", "outage", "emergency", "critical"])

    intent = "complaint" if is_neg else ("request_action" if urgent else "inquiry")
    sentiment_p = 0.88 if is_neg else 0.12
    score_val = 3.0 if urgent else (2.0 if is_neg else 0.75)

    class MockAnswer:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class MockResponse:
        model = "jev-1.13.0 (Simulated)"
        usage = {"total_evaluations": 3, "cached": False}
        choices = {
            "intent": MockAnswer(
                choice=intent,
                confidence=0.92,
                probabilities={"inquiry": 0.05, "complaint": 0.88, "request_action": 0.05, "feedback": 0.02}
            )
        }
        nouls = {
            "is_negative_sentiment": MockAnswer(noul=sentiment_p)
        }
        scores = {
            "priority_level": MockAnswer(
                score=score_val,
                legend=["low", "medium", "high", "urgent"],
                confidence=0.89,
                probabilities=[0.05, 0.10, 0.20, 0.65] if urgent else [0.70, 0.20, 0.08, 0.02]
            )
        }

    render_results(MockResponse(), text, is_simulation=True)

def render_results(response, input_text: str, is_simulation: bool):
    tag = "[yellow](Simulated Dry-Run)[/yellow]" if is_simulation else "[green](Live Jev API)[/green]"
    console.print(f"\n[bold]Model:[/bold] {response.model} {tag}")
    
    table = Table(title=f"Evaluation for: \"{input_text[:60]}...\"", show_lines=True)
    table.add_column("Question Key", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Output Decision", style="green bold")
    table.add_column("Confidence & Metrics", style="white")

    # Choice
    c = response.choices["intent"]
    table.add_row("intent", "Choice", str(c.choice), f"Confidence: {c.confidence:.1%}")

    # Noul
    n = response.nouls["is_negative_sentiment"]
    table.add_row("is_negative_sentiment", "Noul", f"P = {n.noul:.1%}", f"Threshold met: {n.noul > 0.5}")

    # Score
    s = response.scores["priority_level"]
    idx = min(len(s.legend) - 1, int(round(s.score)))
    level_name = s.legend[idx]
    table.add_row("priority_level", "Score", f"{level_name} ({s.score:.2f})", f"Rubric: {s.legend}")

    console.print(table)

def main():
    print_banner()
    key = check_env()

    if key:
        console.print("[green]✓ TYPESAFE_API_KEY detected in environment.[/green]\n")
    else:
        console.print(
            "[yellow]ℹ TYPESAFE_API_KEY not found.[/yellow]\n"
            "You can test the full project architecture right now using [bold cyan]Simulation mode[/bold cyan],\n"
            "or set your key in [bold].env[/bold] to run live against the model.\n"
        )

    while True:
        console.print("\n[bold]Choose an option:[/bold]")
        console.print("1. Run with sample query")
        console.print("2. Enter custom text input")
        console.print("3. Exit")
        
        choice = Prompt.ask("Select", choices=["1", "2", "3"], default="1")
        
        if choice == "3":
            console.print("[dim]Goodbye![/dim]")
            break

        if choice == "1":
            text = "Your billing portal charged me twice for our subscription renewal. Fix this ASAP!"
        else:
            text = Prompt.ask("Enter text to evaluate with Jev")

        if key:
            run_live_test(text)
        else:
            run_simulation(text)

if __name__ == "__main__":
    main()
