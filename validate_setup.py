#!/usr/bin/env python3
"""
Setup Validation Script for Temporal-Spatial Memory System

This script validates that the environment is properly configured
and all dependencies are available.
"""

import sys
import os
import importlib
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.8+")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'langchain',
        'langchain_community', 
        'langchain_openai',
        'faiss',
        'numpy',
        'sentence_transformers',
        'torch',
        'transformers',
        'python_dotenv',
        'pytest',
        'spacy',
        'requests',
        'pypdf',
        'tiktoken',
        'sklearn',
        'fastapi',
        'uvicorn'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            # Handle special cases
            if package == 'faiss':
                try:
                    importlib.import_module('faiss')
                except ImportError:
                    importlib.import_module('faiss-cpu')
            elif package == 'python_dotenv':
                importlib.import_module('dotenv')
            elif package == 'sklearn':
                importlib.import_module('sklearn')
            else:
                importlib.import_module(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - Missing")
            missing_packages.append(package)
    
    return len(missing_packages) == 0, missing_packages

def check_project_structure():
    """Check if project structure is correct."""
    print("\n📁 Checking project structure...")
    
    required_paths = [
        'src/',
        'src/models/',
        'src/utils/',
        'src/services/',
        'src/visualization/',
        'tests/',
        'input/',
        'output/',
        'cache/',
        'requirements.txt',
        'README.md'
    ]
    
    missing_paths = []
    
    for path in required_paths:
        if os.path.exists(path):
            print(f"   ✅ {path}")
        else:
            print(f"   ❌ {path} - Missing")
            missing_paths.append(path)
    
    return len(missing_paths) == 0, missing_paths

def check_environment_config():
    """Check environment configuration."""
    print("\n⚙️  Checking environment configuration...")
    
    # Check for .env file
    if os.path.exists('.env'):
        print("   ✅ .env file found")
        env_exists = True
    else:
        print("   ⚠️  .env file not found (copy config.env.example to .env)")
        env_exists = False
    
    # Check for config template
    if os.path.exists('config.env.example'):
        print("   ✅ config.env.example template found")
    else:
        print("   ❌ config.env.example template missing")
    
    return env_exists

def check_core_imports():
    """Check if core project modules can be imported."""
    print("\n🔧 Checking core imports...")
    
    # Add src to path
    sys.path.insert(0, 'src')
    
    core_modules = [
        'models.narrative_atlas',
        'utils.embedding_service',
        'coordinates',
        'nl_parser',
        'data_models'
    ]
    
    import_errors = []
    
    for module in core_modules:
        try:
            importlib.import_module(module)
            print(f"   ✅ {module}")
        except ImportError as e:
            print(f"   ❌ {module} - {str(e)}")
            import_errors.append((module, str(e)))
    
    return len(import_errors) == 0, import_errors

def check_test_functionality():
    """Check if tests can be imported."""
    print("\n🧪 Checking test functionality...")
    
    try:
        from utils.embedding_service import MockEmbeddingService
        print("   ✅ MockEmbeddingService import")
        
        # Test basic functionality
        mock_service = MockEmbeddingService(dimension=384)
        embedding = mock_service.embed_query("test")
        if len(embedding) == 384:
            print("   ✅ MockEmbeddingService functionality")
            return True
        else:
            print("   ❌ MockEmbeddingService returns wrong dimension")
            return False
            
    except ImportError as e:
        print(f"   ❌ MockEmbeddingService import failed: {e}")
        return False

def main():
    """Run all validation checks."""
    print("🔍 Temporal-Spatial Memory System - Setup Validation")
    print("=" * 60)
    
    checks = []
    
    # Run all checks
    checks.append(("Python Version", check_python_version()))
    
    deps_ok, missing_deps = check_dependencies()
    checks.append(("Dependencies", deps_ok))
    
    structure_ok, missing_paths = check_project_structure()
    checks.append(("Project Structure", structure_ok))
    
    checks.append(("Environment Config", check_environment_config()))
    
    imports_ok, import_errors = check_core_imports()
    checks.append(("Core Imports", imports_ok))
    
    checks.append(("Test Functionality", check_test_functionality()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 VALIDATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name:20} {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 ALL CHECKS PASSED! System is ready to use.")
        print("\nNext steps:")
        print("1. Copy config.env.example to .env and add your API keys")
        print("2. Run: python run_project.py")
        print("3. Or start the server: python server.py")
    else:
        print("⚠️  SOME CHECKS FAILED. Please address the issues above.")
        
        if not deps_ok:
            print(f"\nMissing packages: {', '.join(missing_deps)}")
            print("Install with: pip install -r requirements.txt")
        
        if not structure_ok:
            print(f"\nMissing paths: {', '.join(missing_paths)}")
            print("Ensure you're running from the project root directory")
        
        if not imports_ok:
            print("\nImport errors found. Check dependencies and file structure.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 