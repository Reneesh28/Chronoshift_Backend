#!/usr/bin/env python
"""
ChronoShift Modular Monolith — Backend Services Operations Gateway
Orchestrates Daphne ASGI (8000), FastAPI Simulator (8002), and Flask AI (8003)
side-by-side with color-coded live logs, port clearing, and robust graceful teardown.
"""

import os
import sys
import time
import subprocess
import threading
import signal
import re
import socket
from pathlib import Path

# Color presets using standard ANSI escape codes
RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
YELLOW = "\033[33m"
RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"

TAG_DJANGO = f"{BOLD}{CYAN}[Daphne Core]{RESET} "
TAG_FASTAPI = f"{BOLD}{MAGENTA}[Simulator]  {RESET} "
TAG_FLASK = f"{BOLD}{YELLOW}[AI Engine]  {RESET} "
TAG_SYSTEM = f"{BOLD}{GREEN}[SYSTEM]     {RESET} "

# Port numbers for the services
PORTS = {
    "django": 8000,
    "fastapi": 8002,
    "flask": 8003
}

# Subprocesses container
active_processes = {}
is_shutting_down = False

def render_banner():
    """Renders premium Aetherion terminal header."""
    print(f"\n{BOLD}{CYAN}" + "="*85 + f"{RESET}")
    print(f"""{BOLD}{CYAN}
   ______ _                                _____ _     _  __ _
  / ____/| |                             / ____| |   (_)/ _| |
 | |     | |__  _ __ ___  _ __   ___    | (___ | |__  _| |_| |_
 | |     | '_ \| '__/ _ \| '_ \ / _ \    \___ \| '_ \| |  _| __|
 | |____ | | | | | | (_) | | | | (_) |   ____) | | | | | | | | |
  \_____/|_| |_|_|  \___/|_| |_|\___/   |_____/|_| |_|_|_|  \__|

                  COFLOW DIGITAL TWIN BACKEND SERVICES
{RESET}""")
    print(f"{BOLD}{CYAN}" + "="*85 + f"{RESET}\n")

def check_port_free(port):
    """Returns True if the port is unoccupied, False otherwise."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except socket.error:
            return False

def force_terminate_port_owners():
    """Finds and terminates any processes listening on the target ports on Windows or POSIX."""
    print(f"{TAG_SYSTEM}Performing port collision checks on ports: {list(PORTS.values())}")
    for name, port in PORTS.items():
        if check_port_free(port):
            continue
        
        print(f"{TAG_SYSTEM}Port {port} ({name}) is occupied. Clearing process collision...")
        if sys.platform == "win32":
            try:
                # Query netstat to find PID of active listener
                output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True, text=True)
                for line in output.strip().split('\n'):
                    if "LISTENING" in line:
                        parts = re.split(r'\s+', line.strip())
                        if len(parts) >= 5:
                            pid = parts[-1]
                            print(f"{TAG_SYSTEM}  |-- Forcefully terminating Windows PID {pid} occupying port {port}...")
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                print(f"{TAG_SYSTEM}{RED}Error terminating port {port} owner: {e}{RESET}")
        else:
            # POSIX systems
            try:
                subprocess.run(f"fuser -k -n tcp {port}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"{TAG_SYSTEM}  |-- Forcefully terminated POSIX process occupying port {port}...")
            except Exception as e:
                print(f"{TAG_SYSTEM}{RED}Error terminating port {port} owner: {e}{RESET}")

def stream_log(stream, prefix):
    """Reads logs line-by-line from a subprocess and displays them with color-coded prefix."""
    try:
        for line in iter(stream.readline, ''):
            if is_shutting_down:
                break
            if line:
                # Print directly, ensuring no duplicate newlines
                print(f"{prefix}{line.strip()}")
    except Exception:
        pass
    finally:
        try:
            stream.close()
        except Exception:
            pass

def clean_shutdown_handler(signum=None, frame=None):
    """Gracefully terminates all child microservices on exit."""
    global is_shutting_down
    if is_shutting_down:
        return
    is_shutting_down = True
    
    print(f"\n\n{TAG_SYSTEM}{BOLD}{RED}CRITICAL: Keyboard Interrupt Detected. Terminating cluster...{RESET}")
    
    for name, proc in active_processes.items():
        if proc.poll() is None:
            print(f"{TAG_SYSTEM}Sending shutdown signal to {name} (PID {proc.pid})...")
            if sys.platform == "win32":
                subprocess.run(f'taskkill /F /T /PID {proc.pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except Exception:
                    proc.terminate()
                    
    print(f"{TAG_SYSTEM}System cooldown complete. Operations safely offline.\n")
    sys.exit(0)

def main():
    # 1. Relaunch using virtual environment python if available
    root_dir = Path(__file__).resolve().parent
    if sys.platform == "win32":
        venv_python = root_dir / "venv" / "Scripts" / "python.exe"
    else:
        venv_python = root_dir / "venv" / "bin" / "python"

    if venv_python.exists() and os.path.abspath(sys.executable) != os.path.abspath(str(venv_python)):
        print(f"[BOOT] Activating Virtual Environment: {venv_python.parent.parent.name}")
        # Relaunch current script with the virtual environment's Python interpreter
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)

    # Register exit signal interceptors
    signal.signal(signal.SIGINT, clean_shutdown_handler)
    signal.signal(signal.SIGTERM, clean_shutdown_handler)

    # 2. Render ASCII Banner
    render_banner()

    # 3. Clean environment port collisions
    force_terminate_port_owners()
    print(f"{TAG_SYSTEM}{GREEN}Ports verified and clean.{RESET}")

    # 4. Read Environment File
    env_path = root_dir / ".env"
    if not env_path.exists():
        print(f"{TAG_SYSTEM}{RED}Error: Shared .env configuration missing at: {env_path}{RESET}")
        sys.exit(1)

    print(f"{TAG_SYSTEM}Loading configuration credentials...")
    from dotenv import load_dotenv
    load_dotenv(env_path)

    # 5. Spawn Modular Monolith Services
    python_exe = sys.executable

    # Setup process kwargs for Unix-based systems to handle child signal isolation
    popen_kwargs = {}
    if sys.platform != "win32":
        popen_kwargs["preexec_fn"] = os.setsid

    # A. Daphne ASGI Server (Port 8000)
    django_dir = root_dir / "django_core"
    print(f"{TAG_SYSTEM}Deploying Daphne ASGI Server on Port {PORTS['django']}...")
    active_processes["django"] = subprocess.Popen(
        [python_exe, "-m", "daphne", "-p", str(PORTS["django"]), "core.asgi:application"],
        cwd=str(django_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        **popen_kwargs
    )

    # B. FastAPI Simulator (Port 8002)
    fastapi_dir = root_dir / "fastapi_simulator"
    print(f"{TAG_SYSTEM}Deploying FastAPI Simulator on Port {PORTS['fastapi']}...")
    active_processes["fastapi"] = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "main:app", "--port", str(PORTS["fastapi"]), "--host", "127.0.0.1"],
        cwd=str(fastapi_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        **popen_kwargs
    )

    # C. Flask AI Engine (Port 8003)
    flask_dir = root_dir / "flask_ai_engine"
    print(f"{TAG_SYSTEM}Deploying Flask AI Engine on Port {PORTS['flask']}...")
    env_copy = os.environ.copy()
    env_copy["AI_PORT"] = str(PORTS["flask"])
    active_processes["flask"] = subprocess.Popen(
        [python_exe, "main.py"],
        cwd=str(flask_dir),
        env=env_copy,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        **popen_kwargs
    )

    # 6. Stream Logs via Concurrent Reader Threads
    threads = []
    for name, proc in active_processes.items():
        if name == "django":
            prefix = TAG_DJANGO
        elif name == "fastapi":
            prefix = TAG_FASTAPI
        else:
            prefix = TAG_FLASK

        t_out = threading.Thread(target=stream_log, args=(proc.stdout, prefix), daemon=True)
        t_err = threading.Thread(target=stream_log, args=(proc.stderr, prefix), daemon=True)
        threads.extend([t_out, t_err])
        t_out.start()
        t_err.start()

    print(f"\n{TAG_SYSTEM}{BOLD}{GREEN}ALL SERVICES INITIALIZED AND AGGREGATING LOGS. PRESS CTRL+C TO SHUT DOWN.{RESET}\n")

    # Maintain main process heartbeat and monitor child states
    while True:
        time.sleep(1)
        for name, proc in active_processes.items():
            return_code = proc.poll()
            if return_code is not None:
                print(f"{TAG_SYSTEM}{BOLD}{RED}CRITICAL WARNING: Service {name} has terminated with code {return_code}!{RESET}")
                clean_shutdown_handler()

if __name__ == "__main__":
    main()
