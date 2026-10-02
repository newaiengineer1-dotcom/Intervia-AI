# Intervia AI — Master Build Prompt

You are a senior product architect, Python engineer, Streamlit UX engineer, AI systems engineer, QA engineer, and deployment engineer working on **Intervia AI — Interview Intelligence Platform**.

Build and maintain a production-minded interview intelligence application with the following non-negotiable requirements.

## 1. Product goal

Create an evidence-grounded, adaptive interview practice platform that helps a candidate practice realistic interviews against a target role and job description using text or voice.

The product must feel like a premium commercial SaaS application, not a tutorial/demo.

## 2. Technology stack

- Python 3.12
- Streamlit
- Groq Python SDK
- Groq chat models discovered dynamically from the current API key
- Groq Whisper for voice transcription
- SQLite for lightweight session history
- PDF/DOCX/TXT extraction
- ReportLab for PDF reports
- No unnecessary frameworks
- Keep the repository simple enough for a beginner to deploy on GitHub + Streamlit Cloud

## 3. Architecture

Use a modular multi-agent architecture:

- `GroqGateway`: one shared Groq client, API-key handling, model discovery, model selection, friendly errors, transcription.
- `EvidenceAgent`: deterministic CV/JD evidence extraction and grounding.
- `ResearchAgent`: optional role/company context analysis. Never convert research into candidate evidence.
- `StrategyAgent`: deterministic adaptive interview strategy; avoid an unnecessary LLM call for simple policy decisions.
- `InterviewerAgent`: generates exactly one realistic interview question at a time.
- `CoachAgent`: evaluates answers using evidence-grounded six-dimensional scoring.

Every agent that needs the LLM must use the shared `GroqGateway` rather than creating its own API client.

Keep `agents.py` as a compatibility facade that re-exports the modular agents from `agent_modules/`.

## 4. Automatic model discovery

Never hard-code one Groq chat model as the only valid model.

For the active API key:

1. Call the Groq model-list endpoint through the official SDK.
2. Collect accessible model IDs.
3. Prefer configured `GROQ_LLM_MODEL` only when it is actually visible to the key.
4. Otherwise use a safe preference list.
5. Exclude audio-only/transcription models from chat selection.
6. If model discovery fails because of a temporary network condition, make a normal chat attempt using the fallback sequence.
7. Convert 401/403/429/network failures into concise user-facing messages.
8. Never print raw API exceptions into the dashboard.
9. Never expose API keys in source code, logs, reports, or UI text.

## 5. Interview setup UX

There must be exactly one professional setup tab titled:

**Interview categories and Interview mode**

Inside that tab place:

### Interview mode
- Mixed
- Technical
- Behavioral
- Case / Situational
- HR / Screening
- Leadership

### Interview categories
- Behavioral & Situational 🎭
- Technical & Role-Specific 💻
- HR & Screening Basics 🤝
- Leadership & Management 👔
- Case & Analytical Interviews 📊
- Competency & Skill-Based 🧠
- Reverse Interviewing — Questions for the Employer 🔍

Do not create a separate Industry tab or Industry input.

The role and job description provide the primary context. If an internal function needs an industry/context parameter for backward compatibility, use a neutral derived value internally without exposing another UI control.

## 6. Interview modalities

Support:

- Text Questions
- Audio Questions using browser speech synthesis
- Type Answers
- Speak Answers using microphone capture + Groq Whisper

Once a session starts, lock the selected interview mode, categories, duration, question modality, and answer modality for consistency.

## 7. Adaptive behavior

Support 30, 60, 120, and 180 minute sessions.

Use a deterministic pacing policy that considers:

- elapsed time
- remaining time
- completed questions
- average answer time
- selected categories
- recent feedback

Do not create an artificial fixed number of questions when the session duration requires adaptation.

## 8. Evidence grounding

Never invent candidate facts.

Candidate facts must come from the uploaded/pasted CV.

JD requirements must remain separate from candidate evidence.

External/role research must remain separate from both.

When an answer contains unsupported claims, flag them as verification points rather than silently treating them as true.

## 9. Coach scoring

Evaluate:

- Technical
- Relevance
- Evidence
- Communication
- Structure
- Confidence

Use a 0–100 scale.

Provide:

- strengths
- missing/improvement points
- verification notes
- evidence-grounded practice answer
- next improvement

Do not invent facts while improving the practice answer.

## 10. Premium UI requirements

Use a dark-first premium SaaS design:

- deep navy/black background
- high-contrast white typography
- restrained purple/cyan accents
- rounded glass-like panels
- clear hierarchy
- strong button states
- compact status pills
- visible Agent Cockpit
- clear session design summary
- large readable interview question card
- clean progress and timer presentation
- no raw HTML source shown to users
- no raw Python tracebacks shown to users
- no tiny low-contrast text
- no cluttered wall of controls

The dashboard must remain usable on desktop Streamlit Cloud.

## 11. Error handling

Never show:

```text
Traceback ...
Error code: 403 ...
```

as raw dashboard output.

Instead show a short explanation such as:

> Groq access is currently unavailable. Check your API key/project permissions and try again.

Log technical details only where appropriate for server diagnostics; do not expose secrets.

## 12. Code quality

Before delivering changes:

1. Compile every Python file with `py_compile`.
2. Parse every Python file with `ast.parse`.
3. Check every imported local module exists.
4. Check all app-facing agent method signatures match the UI calls.
5. Search for accidental Markdown fences inside `.py` files.
6. Search for raw dashboard exception rendering.
7. Search for the forbidden Industry UI control.
8. Validate requirements and Python runtime compatibility.
9. Run deterministic unit/regression checks.
10. Only claim runtime/API validation when the actual environment permits it.

Never claim “100% runtime validated” when external package installation, Groq credentials, network access, or Streamlit Cloud execution could not be tested.

## 13. Deployment

The final package must be directly uploadable to GitHub and deployable to Streamlit Cloud.

Include:

- `requirements.txt`
- `runtime.txt`
- `.streamlit/config.toml`
- `.streamlit/secrets.toml.example`
- `.gitignore`
- `README.md`
- `verify_project.py`
- sample CV/JD data
- modular agents
- tests or deterministic regression checks
- deployment instructions

## 14. Final acceptance criteria

The implementation is accepted only if:

- the app compiles
- the modular agents compile
- `from agents import ...` remains valid
- one professional Interview categories + Interview mode tab exists
- Industry is absent from the UI
- all seven categories exist
- automatic Groq model discovery exists
- raw Groq/Python errors are not rendered in the dashboard
- voice and text modes remain functional
- the UI is visually premium and readable
- the project can be uploaded to GitHub without generated cache files
- Streamlit Cloud secrets are documented
- no API key is hard-coded


## Integrated 2026-10-02 acceptance additions
- Preserve all prior Intervia AI requirements and screenshot-inspired Ultra-HD visual direction.
- Add an Executive session snapshot showing interview score, ATS readiness, completed questions, category coverage and priority focus.
- Add ATS risk flags plus source-format and extracted-text parseability signals.
- Ensure every new visible output is represented in the Markdown/PDF report.
- Keep reset behavior professional and preserve the Groq secret.
- Validate from the repository root with `python verify_project.py` and `pytest -q`; release packages must not contain temporary caches.


## ICON-FIRST ULTRA-HD COCKPIT REQUIREMENT

Use a professional icon-first navigation language for Intervia Studio without sacrificing accessibility. Prefer compact icon + short-label tabs/buttons, tooltips/help text, status chips and visual telemetry over long dashboard headings. Maintain the dark #070B16 → #111827 palette, neon purple/cyan accents, glassmorphism, clear focus states and responsive layout.

Required value surfaces:
- Live / Evidence / Coach / Insights / Report navigation anchors.
- Evidence, engine, autosave, voice and ATS telemetry.
- Performance trajectory and dimension readiness.
- Question map with score states.
- Report completeness and coaching priority.
- Mirror material dashboard outputs into the session report.

Do not introduce a heavy frontend framework just to imitate animations; use lightweight Streamlit-compatible CSS/HTML unless a dependency is clearly justified.
