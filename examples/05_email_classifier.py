"""
05_email_classifier.py - Gmail Fetching, Categorization, and Urgency Classification.

Fetches the last 10 emails from Gmail (via IMAP) OR runs in mock mode using realistic
sample emails, and uses TypeSafe AI's Jev model to:
1. Categorize emails into relevant workplace/personal categories (Choice).
2. Classify urgency across 3 levels: High, Medium, Low (Choice & Score).
3. Determine whether explicit action or reply is needed (Noul).

Usage:
    # Run in mock mode (no Gmail connection or credentials needed):
    python examples/05_email_classifier.py --mock

    # Run with live Gmail connection (requires GMAIL_EMAIL & GMAIL_APP_PASSWORD in .env):
    python examples/05_email_classifier.py
"""

import argparse
import email
import email.message
from email.message import Message
import imaplib
import os
import re
import sys
from email.header import decode_header
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

load_dotenv()
console = Console()

# ---------------------------------------------------------------------------
# Fallback Demo Dataset (10 realistic emails covering diverse scenarios)
# ---------------------------------------------------------------------------
DEMO_EMAILS: List[Dict[str, str]] = [
    {
        "from": "sarah.chen@acme-corp.com",
        "subject": "URGENT: Production DB migration failed - rollback decision needed",
        "date": "Today, 09:15 AM",
        "body": "The migration script timed out at step 4. Customer writes are queued. We need your go/no-go on rolling back within the next 20 minutes before peak traffic starts."
    },
    {
        "from": "billing@cloudservices.com",
        "subject": "Invoice #INV-2026-8891 Payment Past Due - Service Suspension Notice",
        "date": "Today, 08:30 AM",
        "body": "Your payment of $420.00 was declined. Please update your billing method immediately to avoid disruption of your active container clusters."
    },
    {
        "from": "security-noreply@auth.google.com",
        "subject": "Security Alert: New login from unrecognized device in Frankfurt",
        "date": "Yesterday, 11:42 PM",
        "body": "We detected a login attempt from Chrome on Linux (IP 194.26.29.11). If this was not you, please secure your account immediately and reset your password."
    },
    {
        "from": "david.miller@client-partners.com",
        "subject": "Q4 Enterprise Contract Renewal - Question on SLA terms",
        "date": "Yesterday, 04:10 PM",
        "body": "Hi team, we reviewed the draft MSA. Our legal team had one question regarding Section 5.2 (99.9% uptime SLA penalties). Could you send clarification by Friday?"
    },
    {
        "from": "alex.kumar@company.internal",
        "subject": "Design Review sync for Thursday 2 PM",
        "date": "Yesterday, 02:00 PM",
        "body": "Hey, let's sync on the new dashboard components this Thursday at 2 PM. I uploaded the Figma mockups to the project folder for early feedback."
    },
    {
        "from": "tldr-ai@tldrnewsletter.com",
        "subject": "TLDR AI: New reasoning benchmarks and fast non-autoregressive models",
        "date": "Yesterday, 10:15 AM",
        "body": "Today's highlights: Anthropic releases Claude updates, new research explores non-autoregressive decision models, and open-source embedding leaderboard updates."
    },
    {
        "from": "mom@family.com",
        "subject": "Dinner this Sunday?",
        "date": "2 days ago, 06:45 PM",
        "body": "Hi honey! Are you free this Sunday evening around 6:30 for family dinner? Let me know if you want me to make lasagna or chicken."
    },
    {
        "from": "orders@amazon.com",
        "subject": "Your package has been delivered to the front door",
        "date": "2 days ago, 01:20 PM",
        "body": "Order #112-984213-90218: Ergonomic keyboard wrist rest was delivered at 1:18 PM. Photo of delivery attached in tracking link."
    },
    {
        "from": "deals@nordic-travel.com",
        "subject": "FLASH SALE: 40% off flights to Iceland this winter! ❄️",
        "date": "3 days ago, 09:00 AM",
        "body": "Book by midnight Sunday to unlock exclusive winter rates on flights to Reykjavik. Limited seats available. Use promo code AURORA40."
    },
    {
        "from": "github-notifications@github.com",
        "subject": "[JEV] meiriv pushed 3 commits to branch main",
        "date": "3 days ago, 08:30 AM",
        "body": "Commits: feat(examples): add customer support triage workflow; chore: update dependencies; docs: update README."
    }
]

# ---------------------------------------------------------------------------
# Gmail IMAP Fetching Helpers
# ---------------------------------------------------------------------------
def decode_mime_header(header_value: Optional[str]) -> str:
    """Safely decode RFC 2047 encoded email headers."""
    if not header_value:
        return ""
    decoded_fragments = []
    for fragment, encoding in decode_header(header_value):
        if isinstance(fragment, bytes):
            try:
                decoded_fragments.append(fragment.decode(encoding or "utf-8", errors="replace"))
            except Exception:
                decoded_fragments.append(fragment.decode("latin1", errors="replace"))
        else:
            decoded_fragments.append(str(fragment))
    return " ".join(decoded_fragments).strip()

def clean_body_text(raw_text: str) -> str:
    """Strip excess whitespace and simple HTML markup for concise context."""
    # Strip basic HTML tags if plain text wasn't found
    text = re.sub(r"<[^>]+>", " ", raw_text)
    # Collapse multiple whitespaces/newlines
    text = re.sub(r"\s+", " ", text).strip()
    return text[:800]  # Cap snippet to 800 chars for optimal latency

def extract_email_body(msg: email.message.Message) -> str:
    """Extract plain text or HTML payload from an email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                continue
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
                    break
            elif content_type == "text/html" and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body = payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace")
    return clean_body_text(body)

def fetch_gmail_emails(count: int = 10) -> Optional[List[Dict[str, str]]]:
    """
    Connect to Gmail via IMAP (SSL port 993) and fetch the last `count` emails.
    Requires GMAIL_EMAIL and GMAIL_APP_PASSWORD in environment.
    """
    email_user = os.getenv("GMAIL_EMAIL") or os.getenv("GMAIL_USER")
    app_password = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("GMAIL_PASSWORD")

    if not email_user or not app_password:
        return None

    try:
        console.print(f"[cyan]Connecting to Gmail IMAP ({email_user})...[/cyan]")
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(email_user, app_password)
        mail.select("INBOX", readonly=True)

        # Search for all messages in INBOX
        status, search_data = mail.search(None, "ALL")
        if status != "OK" or not search_data[0]:
            console.print("[yellow]Inbox is empty or search returned no results.[/yellow]")
            mail.logout()
            return []

        message_ids = search_data[0].split()
        target_ids = message_ids[-count:]
        target_ids.reverse()  # Most recent first

        fetched_emails: List[Dict[str, str]] = []
        for msg_id in target_ids:
            res_status, data = mail.fetch(msg_id, "(RFC822)")
            if res_status != "OK" or not data or not data[0]:
                continue
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = decode_mime_header(msg.get("Subject"))
            sender = decode_mime_header(msg.get("From"))
            date_str = decode_mime_header(msg.get("Date"))
            body = extract_email_body(msg)

            fetched_emails.append({
                "from": sender,
                "subject": subject,
                "date": date_str,
                "body": body
            })

        mail.logout()
        return fetched_emails
    except Exception as e:
        console.print(f"[bold red]Gmail connection failed:[/bold red] {e}")
        return None

# ---------------------------------------------------------------------------
# TypeSafe Jev Classification Pipeline
# ---------------------------------------------------------------------------
def classify_email(client: Any, email_data: Dict[str, str]) -> Dict[str, Any]:
    """
    Classify an email using TypeSafe AI's Jev model.
    Evaluates:
    - category (Choice): 7 relevant inbox categories
    - urgency (Choice): High, Medium, Low
    - urgency_score (Score): Continuous 0.0 - 2.0 ranking
    - action_required (Noul): Calibrated probability whether reply/action is needed
    """
    from typesafe_sdk import Choice, Noul, Score

    email_context = (
        f"From: {email_data.get('from', '')}\n"
        f"Subject: {email_data.get('subject', '')}\n"
        f"Date: {email_data.get('date', '')}\n\n"
        f"Content:\n{email_data.get('body', '')}"
    )

    questions = {
        # 1. Thoughtfully selected inbox categories
        "category": Choice(
            instructions="What is the primary category for this email?",
            criteria={
                "work_projects": "Internal team syncs, code reviews, project deadlines, task assignments, engineering discussions",
                "finance_billing": "Invoices, wire transfers, payment receipts, bank notices, billing warnings, expenses",
                "security_alerts": "2FA codes, password resets, suspicious logins, account security notices",
                "client_customer": "Client correspondence, customer requests, sales inquiries, external partner updates",
                "personal_social": "Messages from friends, family, personal invitations, social media updates",
                "newsletters_tech": "Tech digests, Substacks, engineering articles, webinars, educational newsletters",
                "promotions_deals": "Discounts, marketing campaigns, flash sales, ecommerce deals, advertisements"
            }
        ),
        # 2. Urgency Level: High, Medium, Low
        "urgency": Choice(
            instructions="What is the urgency level of this email?",
            criteria={
                "High": "Requires immediate response or action within 24 hours (critical blocker, outage, security alert, payment past due, emergency)",
                "Medium": "Requires attention or reply within standard timeframe (1-3 days), routine work or partnership matters",
                "Low": "Informational only, newsletter, receipt, promotional offer, or requires no user action"
            }
        ),
        # 3. Urgency Spectrum (Score Primitive)
        "urgency_score": Score(
            instructions="Rate the urgency level from Low to High.",
            criteria=["Low", "Medium", "High"]
        ),
        # 4. Action / Reply Needed (Noul Binary Probability)
        "action_required": Noul(
            instructions="Does this email require an explicit reply, follow-up, or action from the recipient?"
        )
    }

    response = client.system_one(
        state={"email": email_context},
        questions=questions,
        model="jev-latest"
    )

    return {
        "category": response.choices["category"].choice,
        "category_conf": response.choices["category"].confidence,
        "urgency": response.choices["urgency"].choice,
        "urgency_conf": response.choices["urgency"].confidence,
        "urgency_score": response.scores["urgency_score"].score,
        "action_prob": response.nouls["action_required"].noul,
        "raw_response": response
    }

# ---------------------------------------------------------------------------
# Styling and Display Helpers
# ---------------------------------------------------------------------------
CATEGORY_STYLES = {
    "work_projects": "[bold cyan]Work & Projects[/bold cyan]",
    "finance_billing": "[bold yellow]Finance & Billing[/bold yellow]",
    "security_alerts": "[bold red]Security Alert[/bold red]",
    "client_customer": "[bold blue]Client & Partner[/bold blue]",
    "personal_social": "[bold magenta]Personal[/bold magenta]",
    "newsletters_tech": "[bold green]Newsletter[/bold green]",
    "promotions_deals": "[dim]Promotion[/dim]"
}

URGENCY_STYLES = {
    "High": "[bold white on red] HIGH [/bold white on red]",
    "Medium": "[bold black on yellow] MEDIUM [/bold black on yellow]",
    "Low": "[bold white on dark_green] LOW [/bold white on dark_green]"
}

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and classify emails with TypeSafe AI's Jev model.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--mock", "-m",
        action="store_true",
        help="Run in mock mode using sample emails without connecting to Gmail."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Alias for --mock."
    )
    parser.add_argument(
        "--live", "-l",
        action="store_true",
        help="Force live connection to Gmail account via IMAP."
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=10,
        help="Number of emails to evaluate."
    )
    args = parser.parse_args()

    typesafe_key = os.getenv("TYPESAFE_API_KEY")
    if not typesafe_key or typesafe_key == "your_typesafe_api_key_here":
        console.print(
            Panel.fit(
                "[bold yellow]⚠️  TYPESAFE_API_KEY is not set in .env[/bold yellow]\n\n"
                "Please add your TypeSafe API key to [bold cyan].env[/bold cyan]:\n"
                "[green]TYPESAFE_API_KEY=your_key_here[/green]\n\n"
                "Request access at: [blue underline]https://typesafe.ai[/blue underline]",
                title="TypeSafe Key Missing",
                border_style="yellow"
            )
        )
        sys.exit(1)

    from typesafe_sdk import TypeSafeClient

    # Determine execution mode: Mock vs Live
    mock_env = os.getenv("MOCK_EMAILS", "").lower() in ("1", "true", "yes")
    has_gmail_creds = bool((os.getenv("GMAIL_EMAIL") or os.getenv("GMAIL_USER")) and 
                           (os.getenv("GMAIL_APP_PASSWORD") or os.getenv("GMAIL_PASSWORD")))

    if args.live:
        use_mock = False
    elif args.mock or args.demo or mock_env:
        use_mock = True
    else:
        # Default to mock if credentials are not configured
        use_mock = not has_gmail_creds

    emails: List[Dict[str, str]] = []

    if use_mock:
        console.print(
            Panel(
                f"[bold cyan]🧪 Running in MOCK Mode (No Gmail Connection)[/bold cyan]\n\n"
                f"Evaluating [bold white]{min(args.count, len(DEMO_EMAILS))}[/bold white] realistic sample emails.\n"
                "[dim]Tip: To connect to live Gmail, set GMAIL_EMAIL & GMAIL_APP_PASSWORD in .env or pass --live[/dim]",
                title="Mode: Mock / Offline",
                border_style="cyan"
            )
        )
        emails = DEMO_EMAILS[:args.count]
    else:
        if not has_gmail_creds:
            console.print(
                Panel(
                    "[bold red]❌ Gmail credentials not detected in .env[/bold red]\n\n"
                    "To connect to live Gmail, add to your [bold cyan].env[/bold cyan]:\n"
                    "  [green]GMAIL_EMAIL=\"your_address@gmail.com\"[/green]\n"
                    "  [green]GMAIL_APP_PASSWORD=\"xxxx xxxx xxxx xxxx\"[/green]\n\n"
                    "Or run in mock mode without credentials:\n"
                    "  [bold yellow]python examples/05_email_classifier.py --mock[/bold yellow]",
                    title="Credentials Missing",
                    border_style="red"
                )
            )
            sys.exit(1)

        console.print(Panel(f"[bold green]Connecting to Gmail to fetch last {args.count} emails...[/bold green]", title="Gmail Integration"))
        fetched = fetch_gmail_emails(count=args.count)
        if fetched:
            emails = fetched
            console.print(f"[green]✓ Successfully fetched {len(emails)} emails from your Gmail inbox.[/green]\n")
        else:
            console.print("[yellow]Falling back to mock emails...[/yellow]\n")
            emails = DEMO_EMAILS[:args.count]

    # Process and classify emails with Jev
    results = []
    console.print(f"[bold cyan]Classifying {len(emails)} emails with Jev System One model...[/bold cyan]\n")

    with TypeSafeClient() as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[yellow]Evaluating emails...", total=len(emails))
            for idx, em in enumerate(emails, 1):
                progress.update(task, description=f"[yellow]Evaluating email {idx}/{len(emails)}: [white]{em['subject'][:35]}...[/white]")
                classification = classify_email(client, em)
                results.append((em, classification))
                progress.advance(task)

    # -----------------------------------------------------------------------
    # Render Classification Results Table
    # -----------------------------------------------------------------------
    table = Table(
        title="📬 Gmail Inbox Classification & Urgency Triage",
        show_lines=True,
        header_style="bold magenta"
    )
    table.add_column("#", justify="center", style="dim", width=3)
    table.add_column("From", style="cyan", max_width=28)
    table.add_column("Subject", style="white", min_width=35)
    table.add_column("Category", justify="center")
    table.add_column("Urgency", justify="center")
    table.add_column("Score", justify="right")
    table.add_column("Action Needed?", justify="center")

    high_urgency_emails = []
    category_counts: Dict[str, int] = {}
    urgency_counts: Dict[str, int] = {"High": 0, "Medium": 0, "Low": 0}

    for i, (em, res) in enumerate(results, 1):
        cat = res["category"]
        cat_styled = CATEGORY_STYLES.get(cat, cat)
        urg = res["urgency"]
        urg_styled = URGENCY_STYLES.get(urg, urg)
        urg_score = f"{res['urgency_score']:.2f}"

        action_needed = res["action_prob"] > 0.5
        action_label = f"[bold red]🚨 YES ({res['action_prob']*100:.0f}%)[/bold red]" if action_needed else "[dim]No[/dim]"

        sender_clean = em["from"].split("<")[0].strip().replace('"', '') or em["from"]
        table.add_row(
            str(i),
            sender_clean,
            em["subject"],
            cat_styled,
            urg_styled,
            urg_score,
            action_label
        )

        category_counts[cat] = category_counts.get(cat, 0) + 1
        urgency_counts[urg] = urgency_counts.get(urg, 0) + 1

        if urg == "High":
            high_urgency_emails.append((em, res))

    console.print(table)
    console.print()

    # -----------------------------------------------------------------------
    # Summary Insights
    # -----------------------------------------------------------------------
    stats_table = Table(title="📊 Inbox Breakdown", show_header=True, header_style="bold")
    stats_table.add_column("Urgency Level", style="bold")
    stats_table.add_column("Count", justify="center")
    stats_table.add_column("Top Categories", style="dim")

    for level in ["High", "Medium", "Low"]:
        count = urgency_counts.get(level, 0)
        styled_level = URGENCY_STYLES[level]
        stats_table.add_row(styled_level, str(count), f"{count / len(results) * 100:.0f}% of inbox")

    console.print(stats_table)
    console.print()

    # Highlight High Urgency items
    if high_urgency_emails:
        high_panel_lines = ["[bold red]The following emails require immediate attention:[/bold red]\n"]
        for em, res in high_urgency_emails:
            high_panel_lines.append(
                f"• [bold red][{res['urgency']}][/bold red] [bold white]{em['subject']}[/bold white]\n"
                f"  From: [cyan]{em['from']}[/cyan] | Category: [yellow]{res['category']}[/yellow] | Action needed: [red]{res['action_prob']*100:.0f}%[/red]\n"
                f"  [dim]Excerpt: {em['body'][:120]}...[/dim]\n"
            )
        console.print(Panel("\n".join(high_panel_lines), title="🚨 Urgent Action Items", border_style="red"))
    else:
        console.print(Panel("[green]No high urgency emails found. Your inbox is calm![/green]", title="Status", border_style="green"))


if __name__ == "__main__":
    main()
