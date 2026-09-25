"""
Unit tests for AizenOS core modules:
Safety, PII guard, Telemetry, Voice, Polyglot Shell, and Container Subsystems.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.safety import validate_shell_safety
from core.pii_guard import sanitize_text
from core.telemetry import get_system_vitals, get_battery_info
from core.shell_translator import translate_command
from core.container_bridge import detect_linux_runtime

def test_destructive_rm_blocked():
    is_safe, reason = validate_shell_safety("rm -rf /tmp/test")
    assert not is_safe
    assert "Rule 2" in reason

def test_git_reset_hard_blocked():
    is_safe, reason = validate_shell_safety("git reset --hard HEAD~1")
    assert not is_safe
    assert "Rule 2" in reason

def test_drop_database_blocked():
    is_safe, reason = validate_shell_safety("psql -c 'DROP TABLE users;'")
    assert not is_safe
    assert "Rule 2" in reason

def test_env_wipe_blocked():
    is_safe, reason = validate_shell_safety("rm .env")
    assert not is_safe
    assert "sensitive security target" in reason

def test_safe_commands_allowed():
    assert validate_shell_safety("pmset -g batt")[0] is True
    assert validate_shell_safety("git status")[0] is True
    assert validate_shell_safety("ls -la")[0] is True

def test_pii_guard_redaction():
    text = "Deploy token sk-proj-1234567890abcdef1234567890 to server user@example.com"
    clean, masked = sanitize_text(text)
    assert "sk-proj" not in clean
    assert "[API_KEY_1]" in clean
    assert "[EMAIL_1]" in clean
    assert len(masked) == 2

def test_telemetry_vitals():
    vitals = get_system_vitals()
    assert "os" in vitals
    assert "free_disk_gb" in vitals
    assert "free_ram_gb" in vitals
    assert "battery" in vitals

def test_route_task_local_priority():
    from core.orchestrator import route_task
    # Casual chit-chat and questions stay 100% local
    agent, _ = route_task("Hey friend what's up?")
    assert agent == "local"

    # Battery and Mac system queries stay local
    agent, _ = route_task("What is my battery percentage right now?")
    assert agent == "local"

    # Quick scripts and functions stay local
    agent, _ = route_task("Write a python function to parse a JSON string")
    assert agent == "local_code"

def test_route_task_cloud_escalation():
    from core.orchestrator import route_task
    # Massive multi-file fullstack architecture escalates
    agent, _ = route_task("Build a fullstack SaaS application with Stripe billing and PostgreSQL")
    assert agent == "claude"

    # Explicit requests route to requested agent
    agent, _ = route_task("Ask Claude to redesign the button component")
    assert agent == "claude"

    agent, _ = route_task("Have Antigravity audit the entire repo")
    assert agent == "agy"

def test_extract_sentences_streaming():
    from core.voice import extract_sentences_for_speech
    stream_chunk = "Hey there! Your battery is at 95%. You are good to go."
    sents, remaining = extract_sentences_for_speech(stream_chunk)
    assert len(sents) == 3
    assert sents[0] == "Hey there!"
    assert sents[1] == "Your battery is at 95%."
    assert sents[2] == "You are good to go."
    assert remaining == ""

def test_background_job_manager():
    from core.orchestrator import BackgroundJobManager, MAX_BACKGROUND_JOBS
    mgr = BackgroundJobManager()
    assert mgr.get_active_count() == 0

    # Start 3 jobs
    ok1, msg1 = mgr.start_job("sleep 10")
    ok2, msg2 = mgr.start_job("sleep 10")
    ok3, msg3 = mgr.start_job("sleep 10")
    assert ok1 and ok2 and ok3
    assert mgr.get_active_count() == 3

    # Attempt 4th job (should be blocked by Mac Resource Safeguard)
    ok4, msg4 = mgr.start_job("sleep 10")
    assert not ok4
    assert "Safeguard" in msg4

    # Kill jobs cleanly
    mgr.kill_job(1)
    mgr.kill_job(2)
    mgr.kill_job(3)
    assert mgr.get_active_count() == 0

def test_shell_translator_windows_to_posix():
    assert translate_command("cls", target_os="Darwin") == "clear"
    assert translate_command("dir", target_os="Darwin") == "ls -la"
    assert translate_command("dir /Users", target_os="Darwin") == "ls -la /Users"
    assert translate_command("type file.txt", target_os="Darwin") == "cat file.txt"
    assert translate_command("tasklist", target_os="Linux") == "ps aux"
    assert translate_command("Get-Process", target_os="Darwin") == "ps aux"
    assert translate_command("findstr foo file.txt", target_os="Darwin") == "grep foo file.txt"
    assert translate_command("del temp.txt", target_os="Darwin") == "rm temp.txt"
    assert translate_command("copy src.txt dst.txt", target_os="Darwin") == "cp src.txt dst.txt"
    assert translate_command("move src.txt dst.txt", target_os="Darwin") == "mv src.txt dst.txt"

def test_shell_translator_posix_to_windows():
    assert translate_command("clear", target_os="Windows") == "cls"
    assert translate_command("ls -la", target_os="Windows") == "dir"
    assert translate_command("cat config.json", target_os="Windows") == "type config.json"
    assert translate_command("ps aux", target_os="Windows") == "tasklist"
    assert translate_command("grep error app.log", target_os="Windows") == "findstr error app.log"
    assert translate_command("cp a b", target_os="Windows") == "copy a b"
    assert translate_command("mv a b", target_os="Windows") == "move a b"

def test_translated_destructive_command_blocked():
    # If a Windows user types 'del sensitive.env' on macOS, translation produces 'rm sensitive.env'
    posix_cmd = translate_command("del sensitive.env", target_os="Darwin")
    assert posix_cmd == "rm sensitive.env"
    is_safe, reason = validate_shell_safety(posix_cmd)
    assert not is_safe
    assert "sensitive security target" in reason

def test_linux_container_runtime_detection():
    rt = detect_linux_runtime()
    assert isinstance(rt, dict)
    assert "available" in rt
    assert "engine" in rt
    assert "name" in rt
    assert "active" in rt

def test_multios_orchestrator_discovery():
    from core.multi_os_orchestrator import MultiOSOrchestrator
    orchestrator = MultiOSOrchestrator()
    assert len(orchestrator.nodes) >= 1
    assert "macos-host" in orchestrator.nodes or "linux-host" in orchestrator.nodes

def test_multios_node_execution():
    from core.multi_os_orchestrator import MultiOSOrchestrator
    orchestrator = MultiOSOrchestrator()
    host_node_id = "macos-host" if "macos-host" in orchestrator.nodes else "linux-host"
    node = orchestrator.nodes[host_node_id]
    ok, out = node.execute("echo 'aizen-cluster-test'")
    assert ok is True
    assert "aizen-cluster-test" in out

def test_multios_shard_task():
    from core.multi_os_orchestrator import MultiOSOrchestrator
    orchestrator = MultiOSOrchestrator()
    host_node_id = "macos-host" if "macos-host" in orchestrator.nodes else "linux-host"
    res = orchestrator.shard_task({host_node_id: "echo 'shard-success'"})
    assert host_node_id in res
    assert "shard-success" in res[host_node_id]

def test_self_evolver_review_valid_code(tmp_path):
    from core.self_evolver import SelfEvolver
    evolver = SelfEvolver(project_root=tmp_path)
    clean_file = tmp_path / "valid_module.py"
    clean_file.write_text("def add(a, b):\n    return a + b\n")
    ok, msg = evolver.self_review_code(str(clean_file))
    assert ok is True
    assert "passed" in msg.lower()

def test_self_evolver_review_blocks_hazardous_code(tmp_path):
    from core.self_evolver import SelfEvolver
    evolver = SelfEvolver(project_root=tmp_path)
    bad_file = tmp_path / "bad_module.py"
    bad_file.write_text("import os\nos.system('rm -rf /')\n")
    ok, msg = evolver.self_review_code(str(bad_file))
    assert ok is False
    assert "Hazardous pattern" in msg

def test_self_evolver_self_test():
    from core.self_evolver import SELF_EVOLVER
    passed, out = SELF_EVOLVER.self_test(test_target="tests/test_core.py::test_safe_commands_allowed")
    assert passed is True
    assert "passed" in out.lower()

def test_evolution_memory_add_and_retrieve(tmp_path):
    from core.evolution_memory import EvolutionMemory
    mem_file = tmp_path / "test_memory.json"
    mem = EvolutionMemory(memory_path=mem_file)
    assert len(mem.get_lessons()) >= 5
    ok = mem.add_lesson("Always verify test targets")
    assert ok is True
    assert "Always verify test targets" in mem.get_lessons()
    ctx = mem.get_evolution_context("test task")
    assert "Always verify test targets" in ctx

def test_evolution_memory_milestone_recording(tmp_path):
    from core.evolution_memory import EvolutionMemory
    mem_file = tmp_path / "test_memory.json"
    mem = EvolutionMemory(memory_path=mem_file)
    ms = mem.record_milestone(
        goal="build widget",
        architect="planner",
        synthesizer="qwen2.5-coder",
        status="SUCCESS",
        details="All green",
        new_lesson="Widgets must be responsive"
    )
    assert ms["status"] == "SUCCESS"
    assert "Widgets must be responsive" in mem.get_lessons()
    assert len(mem.get_milestones()) == 1

def test_evolution_council_status_detection():
    from core.evolution_council import EVOLUTION_COUNCIL
    status = EVOLUTION_COUNCIL.get_council_status()
    assert "llama3.2" in status
    assert "qwen2.5-coder" in status
    assert "claude" in status
    assert "agy" in status
    assert "codex" in status
    assert status["claude"]["type"] == "cloud"
    assert status["llama3.2"]["type"] == "local"

def test_evolution_council_synthesizer_selection():
    from core.evolution_council import EVOLUTION_COUNCIL
    sel_ui = EVOLUTION_COUNCIL.select_synthesizer_for_goal("build a react frontend dashboard")
    sel_repo = EVOLUTION_COUNCIL.select_synthesizer_for_goal("whole repo refactor architecture")
    sel_conc = EVOLUTION_COUNCIL.select_synthesizer_for_goal("optimize concurrency and low level networking")
    sel_code = EVOLUTION_COUNCIL.select_synthesizer_for_goal("write a python helper function")
    assert sel_ui == "claude"
    assert sel_repo == "agy"
    assert sel_conc == "codex"
    assert sel_code in ("qwen2.5-coder", "llama3.2")

def test_grounding_location():
    from core.grounding import get_real_location
    loc = get_real_location()
    assert "city" in loc
    assert "region" in loc
    assert "timezone" in loc

def test_grounding_weather():
    from core.grounding import get_real_weather
    w = get_real_weather()
    assert isinstance(w, str)
    assert len(w) > 5

def test_grounding_system_settings():
    from core.grounding import get_mac_system_settings
    settings = get_mac_system_settings()
    assert "appearance" in settings
    assert "hostname" in settings
    assert "volume" in settings

def test_grounding_proactive_actions():
    from core.grounding import handle_proactive_actions
    handled, res = handle_proactive_actions("what is weather like?", [])
    assert handled is True
    assert "Right now in your location" in res
    handled_loc, res_loc = handle_proactive_actions("what is my location?", [])
    assert handled_loc is True
    assert "Your location is" in res_loc

def test_vision_desktop_awareness():
    from core.vision import get_frontmost_app, get_running_desktop_apps, get_desktop_visual_summary
    front = get_frontmost_app()
    assert isinstance(front, str)
    assert len(front) > 0
    apps = get_running_desktop_apps()
    assert isinstance(apps, list)
    summary = get_desktop_visual_summary()
    assert "Active Front App" in summary

def test_media_studio_render(tmp_path):
    from core.media_studio import render_hardware_video_clip
    out = tmp_path / "test_clip.mp4"
    ok, msg = render_hardware_video_clip("Test Video", output_path=out, duration_secs=1)
    assert ok is True
    assert out.exists()
    assert out.stat().st_size > 1000

def test_media_studio_kling_blueprint():
    from core.media_studio import generate_video_diffusion_blueprint
    bp = generate_video_diffusion_blueprint("sunset over mountains", provider="kling")
    assert bp["provider"] == "kling"
    assert "sunset over mountains" in bp["enhanced_prompt"]
    assert "camera_motion" in bp
    assert bp["status"] == "BLUEPRINT_READY"

def test_mac_controller_world_time():
    from core.mac_controller import get_accurate_world_time
    ok, msg = get_accurate_world_time("what time is it in Kathmandu, Nepal?")
    assert ok is True
    assert "Kathmandu" in msg
    assert "Nepal" in msg
    assert "2026" in msg

def test_mac_controller_resolve_app():
    from core.mac_controller import resolve_mac_app_name
    assert resolve_mac_app_name("settings") == "System Settings"
    assert resolve_mac_app_name("terminal") == "Terminal"
    assert resolve_mac_app_name("chrome") == "Google Chrome"

def test_mac_controller_execute_action():
    from core.mac_controller import execute_mac_action
    ok, res = execute_mac_action("what time is it in tokyo?")
    assert ok is True
    assert "Tokyo" in res

def test_evolution_memory_interaction_formulation(tmp_path):
    from core.evolution_memory import EvolutionMemory
    mem_file = tmp_path / "evo_formulation_test.json"
    mem = EvolutionMemory(memory_path=mem_file)
    
    # Record chat/voice interactions
    mem.record_interaction("mac_action", "close settings app", "close_mac_app('System Settings')", "Closed System Settings", True)
    mem.record_interaction("mac_action", "close settings", "close_mac_app('System Settings')", "Closed System Settings", True)
    mem.record_interaction("mac_action", "open new terminal", "open_mac_app('Terminal', new_window=True)", "Opened new Terminal", True)

    interactions = mem.get_interactions()
    assert len(interactions) == 3

    candidates = mem.get_formulation_candidates()
    assert len(candidates) >= 1
    # System Settings should have 2 occurrences and be ready for OS formulation
    ready = [c for c in candidates if c["status"] == "Ready for OS Formulation"]
    assert len(ready) == 1
    assert "System Settings" in ready[0]["action"]
    assert ready[0]["occurrences"] == 2

def test_agent_engine_integration():
    from core.agent_engine import AgentEngine
    engine = AgentEngine()
    assert engine.active_model == "llama3.2"
    ok, msg = engine.set_model("qwen")
    assert ok is True
    assert engine.active_model == "qwen"
    status = engine.get_model_status()
    assert "llama3.2" in status
    assert "qwen" in status
    assert "agy" in status




