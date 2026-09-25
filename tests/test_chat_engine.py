"""
Unit tests for ai-chat AGY-grade Agent Engine.
Verifies:
- Multi-model switching and status detection
- Complexity auto-routing (Qwen vs Llama)
- ReAct tool execution safety boundaries
- Proactive deterministic macOS interception
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.agent_engine import AgentEngine

def test_model_switching():
    engine = AgentEngine()
    assert engine.active_model == "auto"

    ok, msg = engine.set_model("qwen")
    assert ok is True
    assert engine.active_model == "qwen"

    ok, msg = engine.set_model("agy")
    assert ok is True
    assert engine.active_model == "agy"

    ok, msg = engine.set_model("claude")
    assert ok is True
    assert engine.active_model == "claude"

    ok, msg = engine.set_model("nonexistent_model")
    assert ok is False
    assert engine.active_model == "claude"

def test_model_status():
    engine = AgentEngine()
    status = engine.get_model_status()
    assert "llama3.2" in status
    assert "qwen" in status
    assert "agy" in status
    assert "claude" in status
    assert "codex" in status
    assert "auto" in status
    assert status["llama3.2"]["ready"] is True

def test_auto_routing_complexity():
    engine = AgentEngine(default_model="auto")
    # Simple greeting should use fast edge model
    assert engine.determine_effective_model("hello how are you?") == "llama3.2"
    # Complex programming task should escalate to local coding powerhouse
    assert engine.determine_effective_model("refactor this FastAPI auth route") == "qwen"
    assert engine.determine_effective_model("build a docker container and fix bug") == "qwen"

def test_tool_execution_safety_boundary():
    engine = AgentEngine()
    # Safe command
    ok, out = engine.execute_tool("bash", "echo 'antigravity'")
    assert ok is True
    assert "antigravity" in out

    # Dangerous command blocked under Rule 2
    ok_bad, out_bad = engine.execute_tool("bash", "rm -rf /")
    assert ok_bad is False
    assert "Safety Block" in out_bad

def test_proactive_mac_interception():
    engine = AgentEngine()
    messages = []
    resp, updated_messages = engine.run_agentic_turn(
        user_prompt="what time is it in Kathmandu, Nepal?",
        messages=messages
    )
    assert "Kathmandu" in resp
    assert "Nepal" in resp
    assert len(updated_messages) == 2
    assert updated_messages[1]["role"] == "assistant"

def test_natural_language_agent_routing():
    engine = AgentEngine()
    assert engine.determine_effective_model("ask agy to refactor this module") == "agy"
    assert engine.determine_effective_model("ask codex to optimize concurrency") == "codex"
    assert engine.determine_effective_model("ask claude to design the interface") == "claude"
    assert engine.determine_effective_model("write a python test for my database") == "qwen"
    assert engine.determine_effective_model("how are you today") == "llama3.2"
