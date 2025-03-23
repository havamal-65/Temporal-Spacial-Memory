# Sprint Tracker Utilities

These utilities help automate the process of updating sprint tracker documents in the `Documents/planning` directory.

## Overview

- `sprint_tracker.py`: Core class for managing sprint tracker documents
- `update_tracker.py`: Command-line interface for easy tracker updates
- `update_sprint.ps1`: PowerShell script for Windows users
- `update_sprint.sh`: Bash script for Unix/Linux/Mac users

## Installation

No special installation is needed. Just ensure Python 3.6+ is available on your system.

### Shell Script Setup

#### Windows
Make sure PowerShell execution policy allows running scripts:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Unix/Linux/Mac
Make the bash script executable:
```bash
chmod +x update_sprint.sh
```

## Usage

### Quick Start with Shell Scripts

#### Windows (PowerShell)
```powershell
# Mark task as completed
.\update_sprint.ps1 2 done 1.1 "Implemented with tests"

# Record your daily standup
.\update_sprint.ps1 2 standup "Completed task 1.1, working on task 1.2 today. No blockers."

# Update task progress
.\update_sprint.ps1 2 progress 1.2 50 "Halfway through implementation"
```

#### Unix/Linux/Mac (Bash)
```bash
# Mark task as completed
./update_sprint.sh 2 done 1.1 "Implemented with tests"

# Record your daily standup
./update_sprint.sh 2 standup "Completed task 1.1, working on task 1.2 today. No blockers."

# Update task progress
./update_sprint.sh 2 progress 1.2 50 "Halfway through implementation"
```

### Shell Script Commands

Both PowerShell and Bash scripts support the same commands:

1. **Start a task**: `start TASK_ID [ASSIGNEE]`
   ```
   # Windows
   .\update_sprint.ps1 2 start 1.1 "Alice"
   
   # Unix/Linux/Mac
   ./update_sprint.sh 2 start 1.1 "Alice"
   ```

2. **Mark a task as completed**: `done TASK_ID [NOTES]`
   ```
   # Windows
   .\update_sprint.ps1 2 done 1.2 "Feature implemented with tests"
   
   # Unix/Linux/Mac
   ./update_sprint.sh 2 done 1.2 "Feature implemented with tests"
   ```

3. **Update task progress**: `progress TASK_ID PERCENTAGE [NOTES]`
   ```
   # Windows
   .\update_sprint.ps1 2 progress 1.3 75 "Almost done"
   
   # Unix/Linux/Mac
   ./update_sprint.sh 2 progress 1.3 75 "Almost done"
   ```

4. **Add standup notes**: `standup NOTES`
   ```
   # Windows
   .\update_sprint.ps1 2 standup "Completed feature X, working on Y"
   
   # Unix/Linux/Mac
   ./update_sprint.sh 2 standup "Completed feature X, working on Y"
   ```

5. **Update metrics interactively**: `metrics`
   ```
   # Windows
   .\update_sprint.ps1 2 metrics
   
   # Unix/Linux/Mac
   ./update_sprint.sh 2 metrics
   ```

6. **Show help**: `help`
   ```
   # Windows
   .\update_sprint.ps1 2 help
   
   # Unix/Linux/Mac
   ./update_sprint.sh 2 help
   ```

### Command-line Interface (Python)

The `update_tracker.py` script provides a more detailed command-line interface for updating sprint trackers.

Basic usage:

```bash
python update_tracker.py SPRINT_NUMBER COMMAND [ARGS]
```

Where:
- `SPRINT_NUMBER` is the sprint number to update (e.g., 1, 2, 3)
- `COMMAND` is one of the available commands (see below)
- `ARGS` are command-specific arguments

### Available Commands

#### Update Task Status

```bash
python update_tracker.py 2 task 1.1 "In Progress" 25 --notes "Working on implementation" --assigned "Alice"
```

Updates task 1.1 in sprint 2 to "In Progress" with 25% completion, adds notes, and assigns it to Alice.

#### Add Standup Entry

```bash
python update_tracker.py 2 standup --person "Bob" --notes "Completed task 2.1, working on 2.2 today. No blockers."
```

Adds a standup entry for Bob in sprint 2 with the specified notes for today's date.

To specify a different date:

```bash
python update_tracker.py 2 standup --date "2023-05-10" --person "Charlie" --notes "Working on tests."
```

#### Add Accomplishment

```bash
python update_tracker.py 2 accomplishment "Implemented QueryEngine with optimization capabilities"
```

Adds an accomplishment to the sprint 2 tracker.

#### Update Metrics

```bash
python update_tracker.py 2 metrics --completed "3/9" --hours 20 --bugs-found 5 --bugs-fixed 4 --coverage 78.5 --perf "Query time" "120ms average" --perf "Memory usage" "40MB"
```

Updates the metrics section in the sprint 2 tracker with completed tasks, hours spent, bugs found/fixed, test coverage, and performance metrics.

#### Set Sprint Dates

```bash
python update_tracker.py 2 dates --start "2023-05-01" --end "2023-05-14"
```

Sets the start and end dates for sprint 2.

#### Update Retrospective

```bash
python update_tracker.py 2 retro --well "Completed all tasks on time" --well "Good test coverage" --not-well "Performance issues in complex queries" --action "Optimize query execution for next sprint"
```

Updates the retrospective sections in the sprint 2 tracker.

### Using the Python API

You can also use the `SprintTracker` class directly in your Python code:

```python
from sprint_tracker import SprintTracker

# Create a tracker for sprint 2
tracker = SprintTracker(2)

# Update a task
tracker.update_task_status("1.1", "In Progress", 30, "Working on implementation", "Alice")

# Add accomplishment
tracker.add_accomplishment("Implemented core functionality")

# Update metrics
tracker.update_metrics(
    completed_tasks="2/9",
    actual_hours=15,
    test_coverage=70,
    performance_metrics={
        "Query time": "150ms average",
        "Memory usage": "35MB peak"
    }
)
```

## Examples

### Updating Multiple Tasks

```bash
python update_tracker.py 2 task 1.1 "Completed" 100 --notes "Finished implementation" --assigned "Alice"
python update_tracker.py 2 task 1.2 "In Progress" 50 --notes "Working on optimization" --assigned "Bob"
python update_tracker.py 2 task 1.3 "Not Started" 0 --assigned "Charlie"
```

### Daily Standup Updates

```bash
python update_tracker.py 2 standup --person "Alice" --notes "Completed task 1.1, starting 2.1."
python update_tracker.py 2 standup --person "Bob" --notes "Working on task 1.2, 50% complete."
python update_tracker.py 2 standup --person "Charlie" --notes "Will start task 1.3 today."
```

## Automation Ideas

- Set up Git hooks to update task completion percentages when commits are made
- Integrate with CI/CD to update test coverage metrics automatically
- Schedule daily reminders to update standup notes
- Create a simple desktop application that shows pending tasks and allows quick status updates
- Configure IDE extensions to update tasks directly from your editor 