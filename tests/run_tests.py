#!/usr/bin/env python3
"""
Test runner script for the autonomia project.
Provides convenient commands for running different types of tests.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    if result.returncode != 0:
        print(f"\n❌ {description} failed with return code {result.returncode}")
        return False
    else:
        print(f"\n✅ {description} completed successfully")
        return True


def main():
    parser = argparse.ArgumentParser(description="Test runner for autonomia project")
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "all", "coverage", "lint"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow tests"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ["python", "-m", "pytest"]
    
    if args.verbose:
        base_cmd.append("-v")
    
    if args.fast:
        base_cmd.extend(["-m", "not slow"])
    
    success = True
    
    if args.type == "unit":
        success = run_command(
            base_cmd + ["-m", "unit"],
            "Unit tests"
        )
    
    elif args.type == "integration":
        success = run_command(
            base_cmd + ["-m", "integration"],
            "Integration tests"
        )
    
    elif args.type == "coverage":
        success = run_command(
            base_cmd + [
                "--cov=.",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--cov-fail-under=80"
            ],
            "Tests with coverage report"
        )
    
    elif args.type == "lint":
        success = run_command(
            ["ruff", "check", "."],
            "Linting with ruff"
        )
    
    elif args.type == "all":
        # Run linting first
        if not run_command(["ruff", "check", "."], "Linting with ruff"):
            success = False
        
        # Run tests with coverage
        if not run_command(
            base_cmd + [
                "--cov=.",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--cov-fail-under=70"
            ],
            "All tests with coverage"
        ):
            success = False
    
    if success:
        print("\n🎉 All checks passed!")
        sys.exit(0)
    else:
        print("\n💥 Some checks failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 