# /// script
# dependencies = [
#     "questionary==2.1.0",
# ]
# ///

import os
import socket
import subprocess
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path

import questionary
from questionary import Style


# ANSI color codes for minimal, elegant styling
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    GRAY = '\033[90m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


# Custom style for questionary to match our theme
custom_style = Style([
    ('qmark', 'fg:#f59e0b'),        # question mark - yellowish
    ('question', ''),               # question text
    ('answer', 'fg:#f59e0b bold'),  # submitted answer - yellowish
    ('pointer', 'fg:#f59e0b bold'), # pointer in select - yellowish
    ('highlighted', 'fg:#fbbf24'),  # highlighted choice - lighter yellow
    ('selected', 'fg:#f59e0b'),     # selected item - yellowish
    ('separator', 'fg:#6c6c6c'),    # separator
    ('instruction', 'fg:#858585'),  # instructions
    ('text', ''),                   # plain text
    ('disabled', 'fg:#858585'),     # disabled choices
])


@dataclass
class Scenario:
    id: str
    name: str
    description: str
    
    def run(self, base_dir: Path, port: int = 3000) -> None:
        """Execute this scenario."""
        raise NotImplementedError
    
    def _ask_show_logs(self) -> bool:
        """Ask user if they want to see full Docker logs."""
        return questionary.confirm("Show full Docker logs?", default=True, style=custom_style).ask()
    
    def _show_ready_message(self, port: int) -> None:
        """Display the setup complete message."""
        print(f"\n{Colors.GREEN}✓{Colors.RESET} Grafana is ready")
        print(f"\n  {Colors.CYAN}http://localhost:{port}{Colors.RESET}")
        print(f"  {Colors.GRAY}admin / admin{Colors.RESET}")
        print(f"\n{Colors.GRAY}Press Ctrl+C to stop{Colors.RESET}")
    
    def _ask_open_browser(self, port: int) -> bool:
        """Ask user if they want to open browser."""
        return questionary.confirm("Open in browser?", default=True, style=custom_style).ask()


class StandaloneGrafana(Scenario):
    def __init__(self):
        super().__init__(
            id="01_standalone_grafana", 
            name="Standalone Grafana", 
            description="Vanilla Grafana instance"
        )
    
    def run(self, base_dir: Path, port: int = 3000) -> None:
        cmd_str = f"docker run -i -t --rm -p {port}:3000 grafana/grafana:12.0.2"
        print(f"\n{Colors.GRAY}→ Starting {self.name}...{Colors.RESET}")
        print(f"  {Colors.GRAY}{cmd_str}{Colors.RESET}")
        
        print()
        show_logs = self._ask_show_logs()
        self._show_ready_message(port)
        
        if self._ask_open_browser(port):
            webbrowser.open(f"http://localhost:{port}")
            print()
        
        subprocess.run([
            "docker", "run", "-i", "-t", "--rm", "-p", f"{port}:3000",
            "grafana/grafana:12.0.2"
        ], check=True, capture_output=not show_logs, text=True)


class ComposeBased(Scenario):
    """Base class for docker-compose based scenarios."""
    
    def run(self, base_dir: Path, port: int = 3000) -> None:
        scenario_dir = base_dir / self.id
        if not scenario_dir.exists():
            print(f"{Colors.YELLOW}Directory '{self.id}' not found{Colors.RESET}")
            sys.exit(1)
        
        cmd_str = f"cd {self.id} && docker-compose up"
        print(f"\n{Colors.GRAY}→ Starting {self.name}...{Colors.RESET}")
        print(f"  {Colors.GRAY}{cmd_str}{Colors.RESET}")
        
        if port != 3000:
            print(f"\n  {Colors.YELLOW}Using port {Colors.CYAN}{port}{Colors.YELLOW} instead of default 3000{Colors.RESET}")
        
        print()
        show_logs = self._ask_show_logs()
        self._show_ready_message(port)
        
        if self._ask_open_browser(port):
            webbrowser.open(f"http://localhost:{port}")
            print()
        
        if port != 3000:
            # Create a temporary docker-compose override
            override_content = f"""services:
  grafana:
    ports:
      - "{port}:3000"
"""
            override_file = scenario_dir / "docker-compose.override.yml"
            try:
                with open(override_file, 'w') as f:
                    f.write(override_content)
                
                subprocess.run(["docker-compose", "up"], cwd=scenario_dir, 
                             check=True, capture_output=not show_logs, text=True)
            finally:
                # Clean up override file
                if override_file.exists():
                    override_file.unlink()
        else:
            subprocess.run(["docker-compose", "up"], cwd=scenario_dir, 
                         check=True, capture_output=not show_logs, text=True)


class PrometheusSetup(ComposeBased):
    def __init__(self):
        super().__init__(
            id="02_metrics_with_prometheus", 
            name="Grafana + Prometheus", 
            description="Basic metrics collection"
        )


class LokiSetup(ComposeBased):
    def __init__(self):
        super().__init__(
            id="03_logs_with_loki", 
            name="Grafana + Loki", 
            description="Log aggregation and exploration"
        )


class TempoSetup(ComposeBased):
    def __init__(self):
        super().__init__(
            id="04_traces_with_tempo", 
            name="Grafana + Tempo", 
            description="Distributed tracing"
        )


class PyroscopeSetup(ComposeBased):
    def __init__(self):
        super().__init__(
            id="05_profiling_with_pyroscope", 
            name="Grafana + Pyroscope", 
            description="Continuous profiling"
        )


def is_port_available(port: int) -> bool:
    """Check if a port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            return result != 0
    except socket.error:
        return False


def check_docker_containers() -> list[str]:
    """Check for existing Docker containers that might conflict."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def handle_container_conflicts(existing_containers: list[str]) -> bool:
    """Handle Docker container conflicts."""
    conflicting = [name for name in ['grafana', 'prometheus', 'loki', 'tempo'] 
                   if name in existing_containers]
    
    if not conflicting:
        return True
    
    print(f"\n{Colors.YELLOW}Found existing containers:{Colors.RESET} {', '.join(conflicting)}")
    
    choice = questionary.select(
        "These containers may conflict. How would you like to proceed?",
        choices=[
            "Remove conflicting containers (recommended)",
            "Stop conflicting containers", 
            "Continue anyway (may fail)",
            "Exit to handle manually"
        ],
        style=custom_style
    ).ask()
    
    if not choice or "Exit" in choice:
        return False
    elif "Remove" in choice:
        for container in conflicting:
            try:
                subprocess.run(["docker", "rm", "-f", container], 
                             capture_output=True, check=True)
                print(f"  {Colors.GREEN}✓{Colors.RESET} Removed container: {Colors.GRAY}{container}{Colors.RESET}")
            except subprocess.CalledProcessError:
                print(f"  {Colors.YELLOW}!{Colors.RESET} Could not remove container: {Colors.GRAY}{container}{Colors.RESET}")
    elif "Stop" in choice:
        for container in conflicting:
            try:
                subprocess.run(["docker", "stop", container], 
                             capture_output=True, check=True)
                print(f"  {Colors.GREEN}✓{Colors.RESET} Stopped container: {Colors.GRAY}{container}{Colors.RESET}")
            except subprocess.CalledProcessError:
                print(f"  {Colors.YELLOW}!{Colors.RESET} Could not stop container: {Colors.GRAY}{container}{Colors.RESET}")
    
    return True


def find_next_available_port(start_port: int = 3000) -> int:
    """Find the next available port starting from start_port."""
    port = start_port
    while port < 65535:
        if is_port_available(port):
            return port
        port += 1
    raise RuntimeError("No available ports found")


def handle_port_conflict(port: int = 3000) -> int:
    """Handle port conflicts with user-friendly options."""
    next_port = find_next_available_port(port + 1)
    
    print(f"\n{Colors.YELLOW}Port {Colors.CYAN}{port}{Colors.YELLOW} is already in use{Colors.RESET}")
    
    choice = questionary.select(
        "How would you like to proceed?",
        choices=[
            f"Use port {next_port} (recommended)",
            "Choose custom port",
            "Exit to handle manually"
        ],
        style=custom_style
    ).ask()
    
    if not choice or "Exit" in choice:
        sys.exit(0)
    elif "custom port" in choice:
        while True:
            print()
            custom_port = questionary.text("Enter port number:", style=custom_style).ask()
            if not custom_port:
                sys.exit(0)
            try:
                port_num = int(custom_port)
                if 1024 <= port_num <= 65535:
                    if is_port_available(port_num):
                        return port_num
                    else:
                        print(f"  {Colors.YELLOW}Port {Colors.CYAN}{port_num}{Colors.YELLOW} is also in use. Please try another.{Colors.RESET}")
                else:
                    print(f"  {Colors.YELLOW}Port must be between 1024 and 65535.{Colors.RESET}")
            except ValueError:
                print(f"  {Colors.YELLOW}Please enter a valid port number.{Colors.RESET}")
    else:
        return next_port


def check_docker() -> tuple[bool, str | None]:
    """Check if Docker is installed and return version info."""
    try:
        result = subprocess.run(
            ["docker", "--version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return True, result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, None


def handle_missing_docker() -> None:
    """Handle case when Docker is not installed."""
    choice = questionary.select(
        "Docker is required. What would you like to do?",
        choices=[
            "Open installation page",
            "Exit"
        ],
        style=custom_style
    ).ask()
    
    if choice == "Open installation page":
        webbrowser.open("https://docs.docker.com/get-docker/")
    
    sys.exit(0)


def get_scenarios() -> list[Scenario]:
    """Return list of available scenarios."""
    return [
        StandaloneGrafana(),
        PrometheusSetup(),
        LokiSetup(),
        TempoSetup(),
        PyroscopeSetup()
    ]


def select_scenario() -> Scenario | None:
    """Display scenario selection menu and return choice."""
    scenarios = get_scenarios()
    
    print()
    
    choices = [f"{s.id.split('_')[0]} · {s.name} – {s.description}" for s in scenarios]
    
    selected = questionary.select("Select scenario:", choices=choices, style=custom_style).ask()
    print()
    
    if not selected:
        return None
    
    scenario_num = selected[:2]
    return next(s for s in scenarios if s.id.startswith(scenario_num))


def run_scenario(scenario: Scenario, port: int) -> None:
    """Execute the selected scenario with proper error handling."""
    base_dir = Path(__file__).parent
    
    try:
        scenario.run(base_dir, port)
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.YELLOW}Error:{Colors.RESET} {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{Colors.GRAY}→ Stopping {scenario.name}...{Colors.RESET}")
        
        if scenario.id != "01_standalone_grafana":
            scenario_dir = base_dir / scenario.id
            try:
                subprocess.run(["docker-compose", "down"], cwd=scenario_dir)
                print(f"{Colors.GREEN}✓{Colors.RESET} Services stopped")
                
                # Clean up any override file
                override_file = scenario_dir / "docker-compose.override.yml"
                if override_file.exists():
                    override_file.unlink()
                    
            except subprocess.CalledProcessError:
                print(f"{Colors.YELLOW}!{Colors.RESET} Some services may still be running")
        
        sys.exit(0)


def main() -> None:
    """Main function."""
    print(f"\n{Colors.BOLD}Grafana Setup Wizard{Colors.RESET}")
    print(f"{Colors.GRAY}Interactive setup for Grafana scenarios{Colors.RESET}\n")
    
    docker_available, docker_version = check_docker()
    
    if not docker_available:
        handle_missing_docker()
        return
    
    version_parts = docker_version.split(' ')
    if len(version_parts) >= 3:
        print(f"{Colors.GREEN}✓{Colors.RESET} Docker {Colors.CYAN}{version_parts[2].rstrip(',')}{Colors.RESET}")
    else:
        print(f"{Colors.GREEN}✓{Colors.RESET} {docker_version}")
    
    # Check for container conflicts
    existing_containers = check_docker_containers()
    if not handle_container_conflicts(existing_containers):
        print(f"\n{Colors.GRAY}Exiting...{Colors.RESET}")
        return
    
    # Check port availability
    port = 3000
    if not is_port_available(port):
        port = handle_port_conflict(port)
    else:
        print(f"{Colors.GREEN}✓{Colors.RESET} Port {Colors.CYAN}{port}{Colors.RESET} available")
    
    scenario = select_scenario()
    if scenario:
        run_scenario(scenario, port)
    else:
        print(f"\n{Colors.GRAY}No scenario selected{Colors.RESET}")


if __name__ == "__main__":
    main()