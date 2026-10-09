"""
04_support_triage.py - End-to-end customer support triage pipeline.

Combines Choice (Department), Noul (SLA Escalation), and Score (Severity)
to automatically classify incoming support tickets without prompt engineering.
"""

import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()

def triage_ticket(ticket_body: str):
    from typesafe_sdk import TypeSafeClient, Choice, Noul, Score

    questions = {
        "department": Choice(
            instructions="Assign this ticket to the appropriate team.",
            criteria={
                "it_support": "Workstation problems, password resets, hardware and office IT",
                "billing_finance": "Invoices, wire transfers, payment disputes, tax documentation",
                "customer_success": "Onboarding questions, training, workflow best practices",
                "security_eng": "Data breach reports, suspicious activity, vulnerability disclosures"
            }
        ),
        "escalation_required": Noul(
            instructions="Does this issue indicate a critical SLA breach or outage affecting multiple users?"
        ),
        "severity": Score(
            instructions="Assess the business impact and operational severity.",
            criteria=["P4_trivial", "P3_minor", "P2_major", "P1_critical"]
        )
    }

    with TypeSafeClient() as client:
        return client.system_one(
            state={"ticket": ticket_body},
            questions=questions
        )

if __name__ == "__main__":
    if not os.getenv("TYPESAFE_API_KEY"):
        console.print("[bold red]Please set TYPESAFE_API_KEY in .env to run this example.[/bold red]")
        sys.exit(1)

    tickets = [
        "Production API is throwing HTTP 500 errors across all US-East regions. Users cannot checkout!",
        "Could you please send an updated W-9 form and the latest quarterly invoice receipt?",
        "How do I invite team members to our workspace and assign them admin privileges?",
        "My laptop screen is flickering when connected to the HDMI dock in conference room 3."
    ]

    table = Table(title="Support Ticket Triage Automation", show_lines=True)
    table.add_column("Ticket Excerpt", max_width=40)
    table.add_column("Team (Choice)", style="cyan")
    table.add_column("Severity (Score)", style="yellow")
    table.add_column("Escalate? (Noul)", style="red")

    for t in tickets:
        res = triage_ticket(t)
        dept = res.choices["department"].choice
        sev_idx = int(round(res.scores["severity"].score))
        sev = res.scores["severity"].legend[sev_idx]
        escalate = "🚨 YES" if res.nouls["escalation_required"].noul > 0.5 else "No"

        table.add_row(t, dept, f"{sev} ({res.scores['severity'].score:.2f})", escalate)

    console.print(table)
