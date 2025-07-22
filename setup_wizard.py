# /// script
# dependencies = [
#     "questionary==2.1.0",
# ]
# ///

import os
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
    
    def run(self, base_dir: Path) -> None:
        """Execute this scenario."""
        raise NotImplementedError


class StandaloneGrafana(Scenario):
    def __init__(self):
        super().__init__(
            id="01", 
            name="Standalone Grafana", 
            description="Vanilla Grafana instance"
        )
    
    def run(self, base_dir: Path) -> None:
        print(f"\n→ Starting {self.name}...")
        print("Access at: http://localhost:3000 (admin/admin)")
        
        subprocess.run([
            "docker", "run", "-i", "-t", "--rm", "-p", "3000:3000",
            "grafana/grafana:12.0.2"
        ], check=True)


class ComposeBased(Scenario):
    """Base class for docker-compose based scenarios."""
    
    def run(self, base_dir: Path) -> None:
        scenario_dir = base_dir / self.id
        if not scenario_dir.exists():
            print(f"Directory '{self.id}' not found")
            sys.exit(1)
        
        print(f"\n→ Starting {self.name}...")
        print("Access at: http://localhost:3000 (admin/admin)")
        
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


def run_scenario(scenario: Scenario) -> None:
    """Execute the selected scenario with proper error handling."""
    base_dir = Path(__file__).parent
    
    try:
        scenario.run(base_dir)
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
    
    scenario = select_scenario()
    if scenario:
        run_scenario(scenario)
    else:
        print("No scenario selected")


if __name__ == "__main__":
    main()