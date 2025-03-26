#!/usr/bin/env python3
"""
Installation script for the Temporal-Spatial Memory Database.

This script installs the package in development mode and ensures that all
dependencies are properly installed.
"""

import os
import sys
import subprocess
import platform

def main():
    """Run the installation process."""
    print("Installing Temporal-Spatial Memory Database...")
    
    # Install dependencies based on platform
    install_dependencies()
    
    # Install the package in development mode
    print("Installing package in development mode...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
        print("Package installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing package: {e}")
        return False
    
    print("\nInstallation complete!")
    print("You can now run the database with: python run_database.py")
    
    return True

def install_dependencies():
    """Install all dependencies, with special handling for Windows."""
    print("Installing dependencies...")
    
    # Install standard dependencies
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Standard dependencies installed.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False
    
    # Special handling for RTree on Windows
    if platform.system() == "Windows":
        try:
            print("Detected Windows OS - Installing RTree with wheels...")
            
            # First uninstall rtree if already installed
            subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "rtree"])
            # Install wheel support first
            subprocess.check_call([sys.executable, "-m", "pip", "install", "wheel"])
            # Install rtree with wheel support to ensure binaries are included
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir", "rtree"])
            print("RTree installation completed.")
        except Exception as e:
            print(f"Warning: Failed to install RTree: {e}")
            print("Please ensure you have Microsoft Visual C++ Redistributable installed.")
            print("You can download it from the Microsoft website.")
            return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 