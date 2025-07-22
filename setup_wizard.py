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


@dataclass
class Scenario:
    id: str
    name: str
    description: str
    
    def run(self, base_dir: Path, port: int = 3000) -> None:
        """Execute this scenario."""
        raise NotImplementedError


class StandaloneGrafana(Scenario):
    def __init__(self):
        super().__init__(
            id="01", 
            name="Standalone Grafana", 
            description="Vanilla Grafana instance"
        )
    
    def run(self, base_dir: Path, port: int = 3000) -> None:
        print(f"\n→ Starting {self.name}...")
        print(f"Access at: http://localhost:{port} (admin/admin)")
        
        subprocess.run([
            "docker", "run", "-i", "-t", "--rm", "-p", f"{port}:3000",
            "grafana/grafana:12.0.2"
        ], check=True)


class ComposeBased(Scenario):
    """Base class for docker-compose based scenarios."""
    
    def run(self, base_dir: Path, port: int = 3000) -> None:
        scenario_dir = base_dir / self.id
        if not scenario_dir.exists():
            print(f"Directory '{self.id}' not found")
            sys.exit(1)
        
        print(f"\n→ Starting {self.name}...")
        print(f"Access at: http://localhost:{port} (admin/admin)")
        
        if port != 3000:
            print(f"Note: Using port {port} instead of default 3000")
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
                
                subprocess.run(["docker-compose", "up"], cwd=scenario_dir, check=True)
            finally:
                # Clean up override file
                if override_file.exists():
                    override_file.unlink()
        else:
            subprocess.run(["docker-compose", "up"], cwd=scenario_dir, check=True)


class PrometheusSetup(ComposeBased):
    def __init__(self):
        super().__init__(
            id="02", 
            name="Grafana + Prometheus", 
            description="Basic metrics collection"
        )


class LokiSetup(ComposeBased):
    def __init__(self):
        super().__init__(
            id="03", 
            name="Grafana + Loki", 
            description="Log aggregation and exploration"
        )


class TempoSetup(ComposeBased):
    def __init__(self):
        super().__init__(
            id="04", 
            name="Grafana + Tempo", 
            description="Distributed tracing"
        )


class PyroscopeSetup(ComposeBased):
    def __init__(self):
        super().__init__(
            id="05", 
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
    
    print(f"Port {port} is already in use.")
    
    choice = questionary.select(
        "How would you like to proceed?",
        choices=[
            f"Use port {next_port} (recommended)",
            "Choose custom port",
            "Exit to handle manually"
        ]
    ).ask()
    
    if not choice or "Exit" in choice:
        sys.exit(0)
    elif "custom port" in choice:
        while True:
            custom_port = questionary.text("Enter port number:").ask()
            if not custom_port:
                sys.exit(0)
            try:
                port_num = int(custom_port)
                if 1024 <= port_num <= 65535:
                    if is_port_available(port_num):
                        return port_num
                    else:
                        print(f"Port {port_num} is also in use. Please try another.")
                else:
                    print("Port must be between 1024 and 65535.")
            except ValueError:
                print("Please enter a valid port number.")
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
        ]
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
    
    print("\nGrafana Setup Wizard")
    print("Choose a scenario:")
    
    choices = [f"{s.id} · {s.name} – {s.description}" for s in scenarios]
    
    selected = questionary.select("Select scenario:", choices=choices).ask()
    
    if not selected:
        return None
    
    scenario_id = selected[:2]
    return next(s for s in scenarios if s.id == scenario_id)


def run_scenario(scenario: Scenario, port: int) -> None:
    """Execute the selected scenario with proper error handling."""
    base_dir = Path(__file__).parent
    
    try:
        scenario.run(base_dir, port)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n→ Stopping {scenario.name}...")
        
        if scenario.id != "01":
            scenario_dir = base_dir / scenario.id
            try:
                subprocess.run(["docker-compose", "down"], cwd=scenario_dir)
                print("Services stopped")
                
                # Clean up any override file
                override_file = scenario_dir / "docker-compose.override.yml"
                if override_file.exists():
                    override_file.unlink()
                    
            except subprocess.CalledProcessError:
                print("Some services may still be running")
        
        sys.exit(0)


def main() -> None:
    """Main function."""
    docker_available, docker_version = check_docker()
    
    if not docker_available:
        handle_missing_docker()
        return
    
    print(f"✓ {docker_version}")
    
    # Check port availability
    port = 3000
    if not is_port_available(port):
        port = handle_port_conflict(port)
    else:
        print(f"✓ Port {port} available")
    
    scenario = select_scenario()
    if scenario:
        run_scenario(scenario, port)
    else:
        print("No scenario selected")


if __name__ == "__main__":
    main()