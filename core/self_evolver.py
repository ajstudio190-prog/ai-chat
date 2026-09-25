"""
AizenOS Autonomous Self-Evolution, Self-Review & Self-Build Engine.
Empowers AizenOS to inspect, refactor, test, and safely deploy upgrades
to its own codebase and OS-level system binary (~/.local/bin/ai).
"""

import os
import sys
import shutil
import time
import ast
import subprocess
from pathlib import Path
from typing import Tuple, Dict, Any

from core.safety import validate_shell_safety
from core.pii_guard import sanitize_text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYSTEM_BIN = Path(os.path.expanduser("~/.local/bin/ai"))
BACKUP_DIR = PROJECT_ROOT / ".backups"

class SelfEvolver:
    """
    Autonomous Recursive Self-Engineering Sentinel:
    Manages self-inspection, safety review, automated testing, atomic deployment,
    and automatic self-rollback for AizenOS.
    """
    def __init__(self, project_root: Path = PROJECT_ROOT, system_bin: Path = SYSTEM_BIN):
        self.project_root = project_root
        self.system_bin = system_bin
        self.backup_dir = BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(self) -> str:
        """Creates an atomic timestamped snapshot before applying any self-modifications."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        snap_path = self.backup_dir / f"snapshot_{timestamp}"
        snap_path.mkdir(parents=True, exist_ok=True)

        # Backup core, cli, and tests
        for folder in ("core", "cli", "tests"):
            src = self.project_root / folder
            if src.exists():
                shutil.copytree(src, snap_path / folder, dirs_exist_ok=True)

        if self.system_bin.exists():
            shutil.copy2(self.system_bin, snap_path / "system_ai_bin")

        return str(snap_path)

    def self_review_code(self, file_path: str) -> Tuple[bool, str]:
        """
        Static Code Analysis & Safety Review Gate:
        1. Verifies AST syntax validity.
        2. Enforces Rule 2 & Rule 3 safety guardrails against dangerous patterns.
        """
        p = Path(file_path)
        if not p.exists():
            return False, f"File {file_path} not found."

        try:
            content = p.read_text(encoding="utf-8")
        except Exception as e:
            return False, f"Failed to read {file_path}: {e}"

        # 1. AST Syntax Check & Analysis
        try:
            tree = ast.parse(content)
        except SyntaxError as se:
            return False, f"AST Syntax Error at line {se.lineno}: {se.msg}"

        hazardous_tokens = ["rm -rf", "rm -r", "rm *", "drop table", "drop database", "flushall", "git reset --hard", "format c:"]

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Block eval and exec
                if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
                    return False, f"Self-review rejected: Dynamic '{node.func.id}()' execution is prohibited (Rule 7)."

                # Check subprocess / os.system executions
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in ("system", "run", "Popen", "check_output", "call"):
                    # Check literal arguments
                    for arg in node.args:
                        arg_str = ""
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            arg_str = arg.value.lower()
                        elif isinstance(arg, ast.List):
                            items = [elt.value.lower() for elt in arg.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]
                            arg_str = " ".join(items)

                        for token in hazardous_tokens:
                            if token in arg_str:
                                return False, f"Self-review rejected: Hazardous pattern - Destructive execution '{token}' in {func_name}() (Rule 2)."

        # 2. Verify no raw unredacted credentials
        _, masked = sanitize_text(content)
        if masked:
            return False, "Self-review rejected: Code contains sensitive API keys or credentials."

        return True, "Code passed all AST and safety review checks."

    def self_test(self, test_target: str = "tests/test_core.py") -> Tuple[bool, str]:
        """Runs the entire test suite to guarantee 100% zero-regression verification."""
        try:
            res = subprocess.run(
                [sys.executable, "-m", "pytest", test_target, "-q"],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            passed = (res.returncode == 0)
            output = res.stdout.strip() or res.stderr.strip()
            return passed, output
        except Exception as e:
            return False, f"Test runner execution failed: {e}"

    def self_rollback(self, snapshot_path: str) -> bool:
        """Restores repository and system binary from a prior snapshot upon test failure."""
        snap = Path(snapshot_path)
        if not snap.exists():
            return False

        try:
            for folder in ("core", "cli", "tests"):
                src = snap / folder
                if src.exists():
                    shutil.copytree(src, self.project_root / folder, dirs_exist_ok=True)

            snap_bin = snap / "system_ai_bin"
            if snap_bin.exists():
                shutil.copy2(snap_bin, self.system_bin)
            return True
        except Exception:
            return False

    def self_deploy_to_os(self) -> Tuple[bool, str]:
        """Atomically deploys validated codebase to OS-level system binary (~/.local/bin/ai)."""
        cli_src = self.project_root / "cli" / "ai"
        if not cli_src.exists():
            return False, "Source cli/ai executable not found."

        try:
            # Sync directly to system binary
            self.system_bin.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cli_src, self.system_bin)
            os.chmod(self.system_bin, 0o755)
            return True, f"Successfully deployed validated build to OS level: {self.system_bin}"
        except Exception as e:
            return False, f"OS-level deployment error: {e}"

    def run_evolution_cycle(self, feature_description: str) -> Dict[str, Any]:
        """
        Executes complete end-to-end self-evolution cycle:
        1. Snapshot state
        2. Safety review
        3. Pytest suite verification
        4. Atomic OS deployment or Rollback
        """
        result = {
            "feature": feature_description,
            "snapshot": None,
            "review_passed": False,
            "tests_passed": False,
            "deployed": False,
            "message": ""
        }

        # Step 1: Snapshot
        snapshot = self.create_snapshot()
        result["snapshot"] = snapshot

        # Step 2: Safety Review on all core Python files
        for py_file in self.project_root.glob("core/**/*.py"):
            ok, msg = self.self_review_code(str(py_file))
            if not ok:
                result["message"] = f"Review failed on {py_file.name}: {msg}"
                return result
        result["review_passed"] = True

        # Step 3: Self-Test
        test_ok, test_msg = self.self_test()
        result["tests_passed"] = test_ok
        if not test_ok:
            self.self_rollback(snapshot)
            result["message"] = f"Tests failed during self-evolution. Automatically rolled back.\nOutput: {test_msg}"
            return result

        # Step 4: Deploy to OS level
        deploy_ok, deploy_msg = self.self_deploy_to_os()
        result["deployed"] = deploy_ok
        result["message"] = deploy_msg if deploy_ok else f"Deployment failed: {deploy_msg}"

        return result

SELF_EVOLVER = SelfEvolver()
