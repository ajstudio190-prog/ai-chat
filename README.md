# ⚡ AI-CHAT: AGY-Grade Sovereign Autonomous Terminal Agent

> **Sovereign multi-model terminal agent paired with autonomous ReAct execution, deterministic macOS automation, and zero-leakage privacy firewall.**

---

## 💡 1. Plain-English Guide (For Non-Technical Users)

### What Is This? (ELI5)
Think of `ai-chat` like having a brilliant software engineer sitting directly inside your Mac terminal. Instead of just answering questions like a passive chatbot (like standard ChatGPT), `ai-chat` has real hands: it can write code, run tests, open terminal windows, close apps when asked, and if something fails, read the error message and fix it by itself.

### Who Is This For?
- Anyone who wants an AI partner that doesn't just talk, but actually **does things** on their Mac.
- Developers who want instant access to multiple AI brains (Llama 3.2, Qwen 2.5 Coder, Antigravity, Claude Code, and Codex) through one unified prompt.

### Plain-English File Directory
| Folder / File | What It Does (In Plain English) |
| :--- | :--- |
| `cli/main.py` | The chat interface. Type messages and watch the AI think and act. |
| `core/agent_engine.py` | The main brain. Coordinates multi-turn reasoning and tool execution. |
| `core/mac_controller.py` | The macOS hands. Quits apps cleanly, opens new Terminal windows, and provides exact world times. |
| `core/safety.py` | The safety shield. Blocks dangerous commands from ever harming your files. |
| `core/grounding.py` | Sensory grounding. Reads live location, weather, and battery with zero hallucination. |
| `core/pii_guard.py` | The privacy firewall. Scrubs API keys and passwords before data leaves your Mac. |
| `dashboard.html` | Visual command center to inspect models, vitals, and tests. |
| `dev.sh` | 1-click launcher for the visual command center. |

---

## 🏢 2. Executive Overview

- **The Problem**: Small edge models like Llama 3.2 (3B) lack the parameter depth to reliably handle complex OS scripting and zero-shot multi-step actions on their own. Meanwhile, cloud-only agents risk leaking credentials and incur high API latency.
- **The Solution**: `ai-chat` bridges the gap using an **AGY-grade ReAct loop** with **dynamic model escalation**:
  - Run ultra-fast (<100ms) on local Apple Silicon Metal GPU with `llama3.2`.
  - Escalate on the fly to `qwen2.5-coder:7b`, Google DeepMind's `agy` (Antigravity), Anthropic's `claude`, or OpenAI's `codex` via `/model <name>` or `/model auto`.
  - Self-healing multi-turn observation: if a shell or AppleScript command errors, the agent observes the stderr and repairs the syntax in the next step.

---

## 🤖 3. Genesis & Autonomous Creation Story

1. **The Investigation**: Why was `ai` previously struggling with actions that Antigravity (AGY) executes effortlessly?
   - **Parameter Scale**: Llama 3.2 3B has 3 billion parameters compared to hundreds of billions in frontier models. It frequently hallucinated mental-math timezones and macOS bundle paths (`/Applications/Utilities/Settings.app` instead of `System Settings`).
   - **Missing Feedback Loop**: Previously, interactive chat executed tools in a one-shot fire-and-forget manner. If an error occurred, it simply dumped it to the console rather than letting the model observe and correct it.
   - **Model Lock-In**: The interactive CLI was hardcoded strictly to `llama3.2:latest`, locking out local 7B coding models and cloud agent engines already installed on the Mac.
2. **The Architecture Upgrade**:
   - Built [`core/agent_engine.py`](file:///Users/ajayashrestha/Desktop/ai-chat/core/agent_engine.py) implementing a 5-step ReAct loop (Thought $\rightarrow$ Action $\rightarrow$ Observation $\rightarrow$ Reflection $\rightarrow$ Self-Correction).
   - Added instant model switching via `/model` supporting `llama3.2`, `qwen`, `agy`, `claude`, `codex`, and `auto`.
   - Wired [`core/mac_controller.py`](file:///Users/ajayashrestha/Desktop/ai-chat/core/mac_controller.py) for 0ms deterministic execution of native macOS window, application, and timezone actions.

---

## 🏗️ 4. Architecture & Directory Tree

```
ai-chat/
├── cli/
│   └── main.py                # Interactive Terminal Chat Shell (/model, /vitals, /clear)
├── core/
│   ├── agent_engine.py        # AGY-Grade ReAct Loop & Multi-Model Coordinator
│   ├── mac_controller.py      # Deterministic macOS Controller & ZoneInfo World Clock
│   ├── safety.py              # Rule 2 & 3 Destructive Command Sentinel
│   ├── grounding.py           # Sensory Grounding & Action Engine
│   ├── telemetry.py           # Hardware Vitals Monitor (RAM, Battery, Wi-Fi)
│   ├── browser.py             # Private Web Search Controller
│   ├── pii_guard.py           # Pre-Flight PII Redaction Firewall
│   └── evolution_memory.py    # Evolutionary Memory Vault & Telemetry Tracker
├── tests/
│   └── test_chat_engine.py    # Unit Test Suite (5/5 Green Verification)
├── dev.sh                     # Dynamic Dev Server & Port Allocator
├── dashboard.html             # Interactive ADHD Visual Command Center
└── README.md                  # Production Technical Manual
```

---

## 🧪 5. Deep QA Matrix

| Test Name | Module | Assertion / Target | Execution Time | Status |
| :--- | :--- | :--- | :--- | :--- |
| `test_model_switching` | `core/agent_engine.py` | Dynamic model switching (llama, qwen, agy, claude) | `0.01s` | ✅ PASS |
| `test_model_status` | `core/agent_engine.py` | Inspects readiness and active flags of models | `0.01s` | ✅ PASS |
| `test_auto_routing_complexity` | `core/agent_engine.py` | Auto-routes complex code to Qwen and simple chat to Llama | `0.01s` | ✅ PASS |
| `test_tool_execution_safety_boundary`| `core/agent_engine.py` | Blocks destructive `rm -rf` while allowing safe bash tools | `0.01s` | ✅ PASS |
| `test_proactive_mac_interception` | `core/agent_engine.py` | Deterministic 0ms world clock and macOS window interception | `0.01s` | ✅ PASS |

---

## 🚀 6. Developer Extension Guide: How to Add Features

1. **Step 1: Add a Tool**: Register a new tool tag (e.g. `<tool:git>`) in `execute_tool()` inside [`core/agent_engine.py`](file:///Users/ajayashrestha/Desktop/ai-chat/core/agent_engine.py).
2. **Step 2: Add Safety Gate**: Ensure any arguments pass through [`core/safety.py`](file:///Users/ajayashrestha/Desktop/ai-chat/core/safety.py) before execution.
3. **Step 3: Add Unit Test**: Append a test case in [`tests/test_chat_engine.py`](file:///Users/ajayashrestha/Desktop/ai-chat/tests/test_chat_engine.py) and verify with `pytest`.
