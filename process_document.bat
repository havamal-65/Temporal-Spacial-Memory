@echo off
echo Starting GraphRAG Document Processor...
python document_processor.py
if errorlevel 1 (
  echo An error occurred. Please check if Python and required packages are installed.
  echo Required packages: tkinter, yaml, subprocess, webbrowser
  pause
) 