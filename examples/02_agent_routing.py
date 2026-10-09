"""
02_agent_routing.py - Agentic Workflow & Tool Routing with Jev.

Demonstrates using Jev as a high-speed router to select the next agent / tool:
- Fast latency (<20ms vs 500ms+ for traditional LLMs)
- Calibrated confidence to trigger human fallback if uncertain
"""

import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

load_dotenv()
console = Console()

def route_user_query(query: str):
    from typesafe_sdk import TypeSafeClient, Choice, Noul, TypeSafeError

    questions = {
        "target_tool": Choice(
            instructions="Determine which backend tool or service should handle this query.",
            criteria={
                "sql_database": "Queries requiring structured relational queries, order lookups, user records",
                "knowledge_search": "Company policies, product documentation, FAQs, conceptual questions",
                "calculator": "Arithmetic calculations, unit conversions, financial estimations",
                "human_handoff": "Requests explicitly asking for a person, complex escalations, complaints"
            }
        ),
        "needs_confirmation": Noul(
            instructions="Does this action perform a destructive or sensitive modification requiring confirmation?"
        )
    }

    try:
        with TypeSafeClient() as client:
            response = client.system_one(
                state={"user_message": query},
                questions=questions
            )

        route = response.choices["target_tool"]
        destructive = response.nouls["needs_confirmation"].noul > 0.65

        console.print(f"[bold cyan]Query:[/bold cyan] {query}")
        console.print(f"[bold green]Routed Tool:[/bold green] {route.choice} (Confidence: {route.confidence:.2%})")
        console.print(f"[bold yellow]Requires User Confirmation:[/bold yellow] {'Yes' if destructive else 'No'}")
        
        # Confidence check for automated routing
        if route.confidence < 0.60:
            console.print("[dim red]⚠️ Routing confidence below threshold. Suggesting human fallback.[/dim red]")
        console.print("-" * 50)

    except TypeSafeError as e:
        console.print(f"[red]Error:[/red] {e}")

if __name__ == "__main__":
    if not os.getenv("TYPESAFE_API_KEY"):
        console.print("[bold red]Please set TYPESAFE_API_KEY in .env to run this example.[/bold red]")
        sys.exit(1)

    queries = [
        "What was the total revenue of order #84920?",
        "Can you explain your 30-day return policy?",
        "Delete my account and erase all my purchase history.",
        "Calculate 18% tip on a $125.40 dinner."
    ]

    console.print(Panel.fit("[bold blue]Agent Tool Router Demo (Powered by Jev)[/bold blue]"))
    for q in queries:
        route_user_query(q)
