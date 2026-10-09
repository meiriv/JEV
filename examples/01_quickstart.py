"""
01_quickstart.py - Basic demonstration of TypeSafe AI's Jev model.

Demonstrates the 3 fundamental System One primitives:
- Choice: Categorical decision / classification
- Noul: Binary probability (0.0 - 1.0) for conditions / guardrails
- Score: Continuous spectrum ranking along an ordered rubric
"""

import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console = Console()

def check_api_key():
    api_key = os.getenv("TYPESAFE_API_KEY")
    if not api_key or api_key == "your_typesafe_api_key_here":
        console.print(
            Panel.fit(
                "[bold yellow]⚠️  TYPESAFE_API_KEY is not set.[/bold yellow]\n\n"
                "Please set your key in [bold cyan].env[/bold cyan] or export it:\n"
                "[green]export TYPESAFE_API_KEY='your_api_key'[/green]\n\n"
                "You can request early access at: [blue underline]https://typesafe.ai[/blue underline]",
                title="API Key Missing",
                border_style="yellow"
            )
        )
        return False
    return True

def run_quickstart():
    if not check_api_key():
        sys.exit(1)

    from typesafe_sdk import TypeSafeClient, Choice, Noul, Score, TypeSafeError

    sample_text = (
        "Customer message: 'I was double-charged on my annual invoice last week. "
        "I need this resolved immediately as it affected our department budget!'"
    )

    console.print(Panel(f"[bold cyan]Input Context (State):[/bold cyan]\n{sample_text}", title="Quickstart Evaluation"))

    # Define the 3 System One primitives
    questions = {
        # 1. Choice: Discrete classification
        "topic": Choice(
            instructions="What is the primary topic of this customer communication?",
            criteria={
                "billing": "Invoices, charges, refunds, or payment disputes",
                "technical": "Software bugs, service outages, or API errors",
                "sales": "New subscriptions, upgrades, or sales requests",
                "general": "Miscellaneous inquiries"
            }
        ),
        # 2. Noul: Calibrated probability (binary assessment)
        "is_urgent": Noul(
            instructions="Does this customer communication convey high urgency requiring immediate escalation?"
        ),
        # 3. Score: Ordered rubric rating (spectrum)
        "frustration_level": Score(
            instructions="Rate the customer's level of dissatisfaction or frustration.",
            criteria=["calm", "slightly_concerned", "frustrated", "infuriated"]
        )
    }

    try:
        console.print("[yellow]Sending request to Jev model via TypeSafe API...[/yellow]")
        with TypeSafeClient() as client:
            response = client.system_one(
                state={"document": sample_text},
                questions=questions,
                model="jev-latest"
            )

        console.print(f"[bold green]✓ Response received! Model: {response.model}[/bold green]\n")

        # Table for answers
        table = Table(title="System One Decision Results", show_lines=True)
        table.add_column("Question", style="cyan", no_wrap=True)
        table.add_column("Primitive", style="magenta")
        table.add_column("Result", style="green")
        table.add_column("Confidence / Probabilities", style="white")

        # 1. Choice answer
        topic_ans = response.choices["topic"]
        table.add_row(
            "topic",
            "Choice",
            f"[bold]{topic_ans.choice}[/bold]",
            f"Confidence: {topic_ans.confidence:.2f} | Probs: {topic_ans.probabilities}"
        )

        # 2. Noul answer
        urgent_ans = response.nouls["is_urgent"]
        table.add_row(
            "is_urgent",
            "Noul",
            f"P(urgent) = [bold]{urgent_ans.noul:.2%}[/bold]",
            f"Raw value: {urgent_ans.noul:.4f}"
        )

        # 3. Score answer
        frust_ans = response.scores["frustration_level"]
        table.add_row(
            "frustration_level",
            "Score",
            f"[bold]{frust_ans.score:.2f}[/bold] / {len(frust_ans.legend) - 1}",
            f"Rubric: {frust_ans.legend} | Confidence: {frust_ans.confidence:.2f}"
        )

        console.print(table)

        if response.usage:
            console.print(f"\n[dim]Usage: {response.usage}[/dim]")

    except TypeSafeError as err:
        console.print(f"[bold red]TypeSafe API Error:[/bold red] {err}")
    except Exception as err:
        console.print(f"[bold red]Unexpected Error:[/bold red] {err}")

if __name__ == "__main__":
    run_quickstart()
