# PowerShell script for quick sprint tracker updates
# This script provides shortcuts for common sprint tracker operations

param (
    [Parameter(Mandatory=$true)]
    [int]$SprintNumber,
    
    [Parameter(Mandatory=$true)]
    [string]$Action,
    
    [Parameter(ValueFromRemainingArguments=$true)]
    $RemainingArgs
)

# Get the directory of this script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Show-Usage {
    Write-Host "Sprint Tracker Update Tool"
    Write-Host "=========================="
    Write-Host ""
    Write-Host "Usage: ./update_sprint.ps1 SPRINT_NUMBER ACTION [ARGS]"
    Write-Host ""
    Write-Host "Actions:"
    Write-Host "  task ID STATUS COMPLETION [NOTES] [ASSIGNEE]   - Update task status"
    Write-Host "    Example: ./update_sprint.ps1 2 task 1.1 'In Progress' 30 'Working on it' 'Alice'"
    Write-Host ""
    Write-Host "  done ID [NOTES]                                - Mark task as completed (100%)"
    Write-Host "    Example: ./update_sprint.ps1 2 done 1.1 'Feature completed with tests'"
    Write-Host ""
    Write-Host "  start ID [ASSIGNEE]                            - Start work on a task (set to 'In Progress', 10%)"
    Write-Host "    Example: ./update_sprint.ps1 2 start 2.3 'Bob'"
    Write-Host ""
    Write-Host "  progress ID PERCENTAGE [NOTES]                 - Update task progress"
    Write-Host "    Example: ./update_sprint.ps1 2 progress 1.2 50 'Halfway through implementation'"
    Write-Host ""
    Write-Host "  standup [NOTES]                                - Add your standup notes for today"
    Write-Host "    Example: ./update_sprint.ps1 2 standup 'Completed task 1.1, starting 2.1 today. No blockers.'"
    Write-Host ""
    Write-Host "  metrics                                        - Update metrics interactively"
    Write-Host "    Example: ./update_sprint.ps1 2 metrics"
    Write-Host ""
    Write-Host "  help                                           - Show this help message"
    Write-Host "    Example: ./update_sprint.ps1 2 help"
}

function Process-Task {
    param (
        [string]$TaskId,
        [string]$Status,
        [int]$Completion,
        [string]$Notes,
        [string]$Assignee
    )
    
    $cmd = "python $ScriptDir/update_tracker.py $SprintNumber task $TaskId `"$Status`" $Completion"
    
    if ($Notes) {
        $cmd += " --notes `"$Notes`""
    }
    
    if ($Assignee) {
        $cmd += " --assigned `"$Assignee`""
    }
    
    Write-Host "Updating task $TaskId to $Status ($Completion%)"
    Invoke-Expression $cmd
}

function Process-Standup {
    param (
        [string]$Notes
    )
    
    # Get current user
    $currentUser = $env:USERNAME
    
    $cmd = "python $ScriptDir/update_tracker.py $SprintNumber standup --person `"$currentUser`" --notes `"$Notes`""
    
    Write-Host "Adding standup entry for $currentUser"
    Invoke-Expression $cmd
}

function Interactive-Metrics {
    # Get metrics from user interactively
    Write-Host "Updating Sprint $SprintNumber Metrics"
    Write-Host "=================================="
    
    $completed = Read-Host "Completed tasks (e.g., '3/9', press Enter to skip)"
    $hours = Read-Host "Actual hours spent (press Enter to skip)"
    $bugsFound = Read-Host "Bugs found (press Enter to skip)"
    $bugsFixed = Read-Host "Bugs fixed (press Enter to skip)"
    $coverage = Read-Host "Test coverage percentage (press Enter to skip)"
    
    # Build command
    $cmd = "python $ScriptDir/update_tracker.py $SprintNumber metrics"
    
    if ($completed) {
        $cmd += " --completed `"$completed`""
    }
    
    if ($hours) {
        $cmd += " --hours $hours"
    }
    
    if ($bugsFound) {
        $cmd += " --bugs-found $bugsFound"
    }
    
    if ($bugsFixed) {
        $cmd += " --bugs-fixed $bugsFixed"
    }
    
    if ($coverage) {
        $cmd += " --coverage $coverage"
    }
    
    # Ask for performance metrics
    $addMetrics = $true
    while ($addMetrics) {
        $metricName = Read-Host "Performance metric name (press Enter to stop adding metrics)"
        
        if (-not $metricName) {
            $addMetrics = $false
        } else {
            $metricValue = Read-Host "Value for $metricName"
            $cmd += " --perf `"$metricName`" `"$metricValue`""
        }
    }
    
    Write-Host "Updating metrics..."
    Invoke-Expression $cmd
}

# Process the action
switch ($Action.ToLower()) {
    "task" {
        if ($RemainingArgs.Count -lt 3) {
            Write-Host "Error: Not enough arguments for task update."
            Show-Usage
            exit 1
        }
        
        $taskId = $RemainingArgs[0]
        $status = $RemainingArgs[1]
        $completion = $RemainingArgs[2]
        $notes = if ($RemainingArgs.Count -gt 3) { $RemainingArgs[3] } else { $null }
        $assignee = if ($RemainingArgs.Count -gt 4) { $RemainingArgs[4] } else { $null }
        
        Process-Task -TaskId $taskId -Status $status -Completion $completion -Notes $notes -Assignee $assignee
    }
    
    "done" {
        if ($RemainingArgs.Count -lt 1) {
            Write-Host "Error: Task ID required."
            Show-Usage
            exit 1
        }
        
        $taskId = $RemainingArgs[0]
        $notes = if ($RemainingArgs.Count -gt 1) { $RemainingArgs[1] } else { "Task completed" }
        
        Process-Task -TaskId $taskId -Status "Completed" -Completion 100 -Notes $notes
    }
    
    "start" {
        if ($RemainingArgs.Count -lt 1) {
            Write-Host "Error: Task ID required."
            Show-Usage
            exit 1
        }
        
        $taskId = $RemainingArgs[0]
        $assignee = if ($RemainingArgs.Count -gt 1) { $RemainingArgs[1] } else { $env:USERNAME }
        
        Process-Task -TaskId $taskId -Status "In Progress" -Completion 10 -Notes "Started work" -Assignee $assignee
    }
    
    "progress" {
        if ($RemainingArgs.Count -lt 2) {
            Write-Host "Error: Task ID and percentage required."
            Show-Usage
            exit 1
        }
        
        $taskId = $RemainingArgs[0]
        $completion = $RemainingArgs[1]
        $notes = if ($RemainingArgs.Count -gt 2) { $RemainingArgs[2] } else { "Updated progress" }
        
        Process-Task -TaskId $taskId -Status "In Progress" -Completion $completion -Notes $notes
    }
    
    "standup" {
        if ($RemainingArgs.Count -lt 1) {
            Write-Host "Error: Standup notes required."
            Show-Usage
            exit 1
        }
        
        $notes = $RemainingArgs -join " "
        Process-Standup -Notes $notes
    }
    
    "metrics" {
        Interactive-Metrics
    }
    
    "help" {
        Show-Usage
    }
    
    default {
        Write-Host "Error: Unknown action '$Action'"
        Show-Usage
        exit 1
    }
} 