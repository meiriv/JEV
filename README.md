# Jev System One Model Project

A ready-to-run project for exploring and integrating **Jev**, the "System One" decision model by [TypeSafe AI](https://typesafe.ai/blog/introducing-system-one-models-and-jev).

---

## 💡 What is Jev & "System One"?

Traditional Large Language Models (LLMs) act like **System 2** thinking: slow, deliberative, and autoregressively streaming tokens word-by-word. While powerful for generative prose, this is overkill and too slow for core software automation tasks like routing, classification, triage, and guardrails.

**Jev** is a **System One** model inspired by Daniel Kahneman's concept of fast, automatic, intuitive judgment:
- **Non-Autoregressive:** Evaluates context against structured questions and returns typed data directly without token streaming.
- **Ultra-Fast & Cheap:** Up to **200× faster** (sub-20ms response times) and **400× lower cost** than general LLMs.
- **Calibrated Decisions:** Returns mathematical probabilities and confidence metrics, making thresholds and automated fallback logic reliable.

### The 3 Core Primitives

| Primitive | Purpose | Returns | Example Use Case |
| :--- | :--- | :--- | :--- |
| **`Choice`** | Categorical classification | Selected option, probabilities, confidence | Routing to tools, ticket categorization |
| **`Noul`** | Binary probability condition | Probability $P \in [0.0, 1.0]$ | Safety guardrails, prompt injection detection, escalation triggers |
| **`Score`** | Ordered rubric spectrum | Fractional score along a defined scale | Priority ranking, sentiment severity |

---

## 📁 Project Structure

```text
JEV/
├── .venv/                      # Python 3.12 virtual environment (pre-configured)
├── .env.example                # API key template
├── pyproject.toml              # Project metadata & dependencies
├── requirements.txt            # Dependency specification
├── jev_demo.py                 # Interactive playground CLI (includes dry-run mode)
└── examples/
    ├── 01_quickstart.py        # Introduction to Choice, Noul, and Score
    ├── 02_agent_routing.py     # Sub-millisecond agent tool & workflow routing
    ├── 03_guardrails_moderation.py # Prompt injection & PII detection filters
    ├── 04_support_triage.py    # Automated support ticket triage pipeline
    └── 05_email_classifier.py # Gmail fetching, categorization, and 3-level urgency triage
```

---

## 🚀 Quickstart

### 1. Configure Your API Key
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Open `.env` and set your TypeSafe API key (plus optional Gmail settings for example 05):
```ini
TYPESAFE_API_KEY="your_actual_key_here"

# Optional: Live Gmail credentials (or omit to use mock mode)
# GMAIL_EMAIL="your_email@gmail.com"
# GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
# MOCK_EMAILS=true
```
*(If you do not yet have an early-access key, you can still test the project architecture using the simulated dry-run in `jev_demo.py`).*

### 2. Activate the Virtual Environment
The virtual environment is already initialized with Python 3.12 and all dependencies:
```bash
source .venv/bin/activate
```

*(To re-install or update dependencies at any time:)*
```bash
pip install -r requirements.txt
```

---

## 🧪 Running the Examples

### Interactive CLI Playground
Test queries with live model evaluation (or simulated dry-run):
```bash
python jev_demo.py
```

### 1. Basic Quickstart (`examples/01_quickstart.py`)
Demonstrates how to declare questions using `Choice`, `Noul`, and `Score`:
```bash
python examples/01_quickstart.py
```

### 2. Agentic Routing (`examples/02_agent_routing.py`)
Routes user messages to tools (SQL, Knowledge Base, Human Fallback) in milliseconds:
```bash
python examples/02_agent_routing.py
```

### 3. Guardrails & Moderation (`examples/03_guardrails_moderation.py`)
Evaluates inputs for prompt injection, sensitive PII, or policy violations:
```bash
python examples/03_guardrails_moderation.py
```

### 4. Support Triage (`examples/04_support_triage.py`)
End-to-end pipeline assigning tickets, calculating SLA urgency, and scoring severity:
```bash
python examples/04_support_triage.py
```

### 5. Email Classifier & Urgency Triage (`examples/05_email_classifier.py`)
Fetches emails and classifies them into 7 practical inbox categories, triages urgency across 3 levels (**High**, **Medium**, **Low**), and detects if explicit action is required:
- **`category` (`Choice`)**: Work & Projects, Finance & Billing, Security Alerts, Client & Partner, Personal, Newsletters, Promotions.
- **`urgency` (`Choice` & `Score`)**: 3-level priority assessment with fractional urgency rating ($0.0 - 2.0$).
- **`action_required` (`Noul`)**: Calibrated probability ($P \in [0.0, 1.0]$) estimating whether a reply or follow-up is needed.

#### 🧪 Running in Mock Mode (No Gmail Connection Needed)
Run offline using realistic synthetic emails—zero Gmail credentials or internet connection to mail servers required:
```bash
# Run with default 10 sample emails:
python examples/05_email_classifier.py --mock

# Short flag with custom email count:
python examples/05_email_classifier.py -m -n 5
```
*(You can also set `MOCK_EMAILS=true` in `.env` to make mock mode the default).*

#### 📬 Running with Live Gmail
To connect to your real Gmail account via IMAP:
1. Generate a 16-character [Google App Password](https://myaccount.google.com/apppasswords) (requires 2-Step Verification).
2. Add your credentials to `.env`:
   ```ini
   GMAIL_EMAIL="your_address@gmail.com"
   GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
   ```
3. Run without flags:
   ```bash
   python examples/05_email_classifier.py
   ```

---

## 🧑‍💻 Code Reference

```python
from typesafe_sdk import TypeSafeClient, Choice, Noul, Score

with TypeSafeClient() as client:
    response = client.system_one(
        state={"document": "Customer input text here..."},
        questions={
            "intent": Choice(
                instructions="What is the user trying to do?",
                criteria={"billing": "Payment issues", "support": "Technical bugs"}
            ),
            "is_urgent": Noul(
                instructions="Does this require immediate escalation?"
            ),
            "severity": Score(
                instructions="Rate customer frustration.",
                criteria=["low", "medium", "high", "critical"]
            )
        }
    )

print(response.choices["intent"].choice)          # e.g. "billing"
print(response.nouls["is_urgent"].noul)            # e.g. 0.94
print(response.scores["severity"].score)           # e.g. 2.75
```

---

## 🔗 Resources
- **TypeSafe AI Announcement:** [typesafe.ai/blog/introducing-system-one-models-and-jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- **Official Documentation:** [docs.typesafe.ai](https://docs.typesafe.ai)
- **Python SDK on PyPI:** [typesafe-sdk](https://pypi.org/project/typesafe-sdk/)
