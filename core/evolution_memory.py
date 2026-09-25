"""
Evolutionary Memory Vault for AizenOS.
Persists lessons, failure post-mortems, architectural blueprints, and self-learning milestones.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

MEMORY_FILE = Path.home() / ".aizen_evolution_memory.json"

DEFAULT_INITIAL_RULES = [
    "Rule 2 & 3 Guardrails: Never allow destructive filesystem, git force, or database wipe operations.",
    "AST Safety: Inspect ast.Call argument nodes specifically rather than naive substring matching.",
    "Isolated Pytest: Test runners must invoke specific target functions during self-test to avoid recursive subprocess loops.",
    "Hardware Acceleration: On Apple Silicon M4, use vector CPU AMX fallback if whisper Metal shaders deadlock.",
    "Binary Deployment: Deployments to ~/.local/bin/ai must maintain project root fallback resolution."
]

DEFAULT_PATTERNS = [
    "Atomic Hot-Deploy: Pre-verify code via AST, run full pytest suite, copy to system binary, chmod 0755, rollback on failure.",
    "Dynamic Port Allocator: Use dual-socket probe to bind next available port without collisions.",
    "Bidirectional ReAct: Wrap local model chat in tool execution loop for hardware and terminal commands."
]

class EvolutionMemory:
    def __init__(self, memory_path: Optional[Path] = None):
        self.memory_path = memory_path or MEMORY_FILE
        self._ensure_initialized()

    def _ensure_initialized(self):
        if not self.memory_path.exists():
            data = {
                "version": 1,
                "created_at": time.time(),
                "lessons": list(DEFAULT_INITIAL_RULES),
                "patterns": list(DEFAULT_PATTERNS),
                "milestones": []
            }
            self._save(data)

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.memory_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {
                "version": 1,
                "created_at": time.time(),
                "lessons": list(DEFAULT_INITIAL_RULES),
                "patterns": list(DEFAULT_PATTERNS),
                "milestones": []
            }

    def _save(self, data: Dict[str, Any]) -> bool:
        try:
            self.memory_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = self.memory_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self.memory_path)
            return True
        except Exception:
            return False

    def get_lessons(self) -> List[str]:
        data = self._load()
        return data.get("lessons", [])

    def add_lesson(self, lesson: str) -> bool:
        data = self._load()
        lessons = data.get("lessons", [])
        clean = lesson.strip()
        if clean and clean not in lessons:
            lessons.append(clean)
            data["lessons"] = lessons
            return self._save(data)
        return False

    def get_patterns(self) -> List[str]:
        data = self._load()
        return data.get("patterns", [])

    def add_pattern(self, pattern: str) -> bool:
        data = self._load()
        patterns = data.get("patterns", [])
        clean = pattern.strip()
        if clean and clean not in patterns:
            patterns.append(clean)
            data["patterns"] = patterns
            return self._save(data)
        return False

    def record_interaction(
        self,
        intent_type: str,
        query: str,
        action: str,
        result: str,
        success: bool = True
    ) -> None:
        """
        Records sensory interactions from ai chat and ai talk.
        Tracks successful action recipes and query patterns to formulate into native OS capabilities.
        """
        data = self._load()
        interactions = data.setdefault("interactions", [])
        entry = {
            "timestamp": time.time(),
            "intent_type": intent_type,
            "query": query[:200],
            "action": action[:200],
            "result": result[:200],
            "success": success
        }
        interactions.append(entry)
        if len(interactions) > 200:
            data["interactions"] = interactions[-200:]

        if success:
            patterns_freq = data.setdefault("action_frequencies", {})
            action_key = f"{intent_type}:{action.strip()}"
            patterns_freq[action_key] = patterns_freq.get(action_key, 0) + 1

        self._save(data)

    def get_interactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the most recent interactions logged from ai chat and ai talk."""
        data = self._load()
        return data.get("interactions", [])[-limit:]

    def get_formulation_candidates(self) -> List[Dict[str, Any]]:
        """
        Identifies repeated successful chat/voice actions that qualify for
        formulation into permanent, hardcoded native OS commands.
        """
        data = self._load()
        freq = data.get("action_frequencies", {})
        candidates = []
        for action_key, count in sorted(freq.items(), key=lambda x: x[1], reverse=True):
            parts = action_key.split(":", 1)
            intent = parts[0]
            act = parts[1] if len(parts) > 1 else ""
            candidates.append({
                "intent": intent,
                "action": act,
                "occurrences": count,
                "status": "Ready for OS Formulation" if count >= 2 else "Collecting Telemetry"
            })
        return candidates

    def record_milestone(
        self,
        goal: str,
        architect: str,
        synthesizer: str,
        status: str,
        details: str = "",
        new_lesson: Optional[str] = None
    ) -> Dict[str, Any]:
        """Records an evolution milestone and captures any new lesson learned."""
        data = self._load()
        milestone = {
            "id": f"evo_{int(time.time())}",
            "timestamp": time.time(),
            "goal": goal,
            "architect": architect,
            "synthesizer": synthesizer,
            "status": status,
            "details": details[:500]
        }
        data.setdefault("milestones", []).append(milestone)
        if new_lesson and new_lesson.strip():
            lessons = data.setdefault("lessons", [])
            if new_lesson.strip() not in lessons:
                lessons.append(new_lesson.strip())
        self._save(data)
        return milestone

    def get_milestones(self) -> List[Dict[str, Any]]:
        data = self._load()
        return data.get("milestones", [])

    def get_evolution_context(self, task_description: str = "") -> str:
        """
        Synthesizes historical lessons and architectural patterns into a high-density
        prompt prefix for the Multi-Model Council.
        """
        data = self._load()
        lessons = data.get("lessons", [])
        patterns = data.get("patterns", [])
        milestones = data.get("milestones", [])

        lines = [
            "### AIZIN-OS EVOLUTIONARY MEMORY & SELF-LEARNED PRINCIPLES",
            "The following principles were learned through previous autonomous build and test cycles:"
        ]
        for idx, l in enumerate(lessons[-8:], 1):
            lines.append(f"{idx}. {l}")

        if patterns:
            lines.append("\n### PROVEN ARCHITECTURAL PATTERNS:")
            for p in patterns[-4:]:
                lines.append(f"• {p}")

        recent_successes = [m for m in milestones if m.get("status") == "SUCCESS"]
        if recent_successes:
            lines.append("\n### RECENT EVOLUTIONARY MILESTONES:")
            for m in recent_successes[-3:]:
                lines.append(f"• [{m.get('synthesizer')}] {m.get('goal')}")

        return "\n".join(lines)

EVOLUTION_MEMORY = EvolutionMemory()
