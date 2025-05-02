import os
import sys
import subprocess
import venv
import platform

VENV_DIR = "venv"

def run_command(command, cwd=None, check=True):
    """Runs a command using subprocess and handles errors."""
    print(f"--- Running command: {' '.join(command)}")
    process = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if process.stdout:
        print(process.stdout)
    if process.stderr:
        print(process.stderr, file=sys.stderr)
    if check and process.returncode != 0:
        print(f"--- Command failed: {' '.join(command)}", file=sys.stderr)
        sys.exit(process.returncode)
    print(f"--- Command finished: {' '.join(command)}")
    return process

def get_venv_executable(executable_name):
    """Gets the path to an executable within the virtual environment."""
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", f"{executable_name}.exe")
    else: # Linux/macOS
        return os.path.join(VENV_DIR, "bin", executable_name)

def main():
    print("--- Starting project setup ---")

    # 1. Create virtual environment if it doesn't exist
    if not os.path.exists(VENV_DIR):
        print(f"--- Creating virtual environment in '{VENV_DIR}'... ---")
        venv.create(VENV_DIR, with_pip=True)
        print(f"--- Virtual environment created. ---")
    else:
        print(f"--- Virtual environment '{VENV_DIR}' already exists. ---")

    # 2. Install requirements using the venv pip
    print("--- Installing requirements from requirements.txt... ---")
    pip_executable = get_venv_executable("pip")
    run_command([pip_executable, "install", "-r", "requirements.txt"])

    # 3. Download spaCy model using the venv python
    print("--- Downloading spaCy model 'en_core_web_sm'... ---")
    python_executable = get_venv_executable("python")
    run_command([python_executable, "-m", "spacy", "download", "en_core_web_sm"])

    print("\n--- Setup Complete! ---")
    print("\nPlease activate the virtual environment:")
    if platform.system() == "Windows":
        print(f"  On Windows (Command Prompt/PowerShell): .\\{VENV_DIR}\\Scripts\\activate")
    else:
        print(f"  On Linux/macOS (bash/zsh): source {VENV_DIR}/bin/activate")
    
    # 4. Remind about .env file
    env_example_file = ".env copy.txt"
    env_file = ".env"
    if os.path.exists(env_example_file) and not os.path.exists(env_file):
        print(f"\nIMPORTANT: Please copy '{env_example_file}' to '{env_file}' and fill in your API key.")
        print(f"  Example (Windows): copy '{env_example_file}' '{env_file}'")
        print(f"  Example (Linux/macOS): cp '{env_example_file}' '{env_file}'")
    elif not os.path.exists(env_file):
         print(f"\nIMPORTANT: Create a '{env_file}' file and add your OPENAI_API_KEY and any other necessary environment variables.")

    print("\nNow you should be ready to run the application.")

if __name__ == "__main__":
    main() 