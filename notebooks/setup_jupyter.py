#!/usr/bin/env python3
"""
Setup script for Jupyter notebook environment
"""

import subprocess
import sys
from pathlib import Path


def install_packages():
    """Install required packages for Jupyter notebooks"""
    packages = [
        "jupyter",
        "notebook",
        "ipykernel",
        "pandas",
        "matplotlib",
        "seaborn",
        "plotly",
        "numpy",
        "scipy",
    ]

    print("Installing Jupyter packages...")
    for package in packages:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package]
            )
            print(f"✓ Installed {package}")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {package}")


def setup_kernel():
    """Setup Jupyter kernel for the project"""
    try:
        # Install the current environment as a Jupyter kernel
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "ipykernel",
                "install",
                "--user",
                "--name=superchromia",
                "--display-name=Superchromia",
            ]
        )
        print("✓ Jupyter kernel 'superchromia' installed successfully")
    except subprocess.CalledProcessError:
        print("✗ Failed to install Jupyter kernel")


def main():
    print("Setting up Jupyter notebook environment for Superchromia...")

    # Install packages
    install_packages()

    # Setup kernel
    setup_kernel()

    print("\nSetup complete! You can now:")
    print("1. Run 'jupyter notebook' to start the notebook server")
    print("2. Open 'database_connection.ipynb' to connect to your database")
    print("3. Select the 'superchromia' kernel when prompted")


if __name__ == "__main__":
    main()
