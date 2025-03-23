#!/bin/bash
# Bash script for quick sprint tracker updates
# This script provides shortcuts for common sprint tracker operations

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Show usage information
show_usage() {
    echo "Sprint Tracker Update Tool"
    echo "=========================="
    echo ""
    echo "Usage: ./update_sprint.sh SPRINT_NUMBER ACTION [ARGS]"
    echo ""
    echo "Actions:"
    echo "  task ID STATUS COMPLETION [NOTES] [ASSIGNEE]   - Update task status"
    echo "    Example: ./update_sprint.sh 2 task 1.1 'In Progress' 30 'Working on it' 'Alice'"
    echo ""
    echo "  done ID [NOTES]                                - Mark task as completed (100%)"
    echo "    Example: ./update_sprint.sh 2 done 1.1 'Feature completed with tests'"
    echo ""
    echo "  start ID [ASSIGNEE]                            - Start work on a task (set to 'In Progress', 10%)"
    echo "    Example: ./update_sprint.sh 2 start 2.3 'Bob'"
    echo ""
    echo "  progress ID PERCENTAGE [NOTES]                 - Update task progress"
    echo "    Example: ./update_sprint.sh 2 progress 1.2 50 'Halfway through implementation'"
    echo ""
    echo "  standup [NOTES]                                - Add your standup notes for today"
    echo "    Example: ./update_sprint.sh 2 standup 'Completed task 1.1, starting 2.1 today. No blockers.'"
    echo ""
    echo "  metrics                                        - Update metrics interactively"
    echo "    Example: ./update_sprint.sh 2 metrics"
    echo ""
    echo "  help                                           - Show this help message"
    echo "    Example: ./update_sprint.sh 2 help"
}

# Process task updates
process_task() {
    local task_id="$1"
    local status="$2"
    local completion="$3"
    local notes="$4"
    local assignee="$5"
    
    cmd="python ${SCRIPT_DIR}/update_tracker.py ${SPRINT_NUMBER} task ${task_id} \"${status}\" ${completion}"
    
    if [ ! -z "$notes" ]; then
        cmd="${cmd} --notes \"${notes}\""
    fi
    
    if [ ! -z "$assignee" ]; then
        cmd="${cmd} --assigned \"${assignee}\""
    fi
    
    echo "Updating task ${task_id} to ${status} (${completion}%)"
    eval "$cmd"
}

# Process standup entries
process_standup() {
    local notes="$1"
    
    # Get current user
    local current_user=$(whoami)
    
    cmd="python ${SCRIPT_DIR}/update_tracker.py ${SPRINT_NUMBER} standup --person \"${current_user}\" --notes \"${notes}\""
    
    echo "Adding standup entry for ${current_user}"
    eval "$cmd"
}

# Interactive metrics update
interactive_metrics() {
    # Get metrics from user interactively
    echo "Updating Sprint ${SPRINT_NUMBER} Metrics"
    echo "=================================="
    
    echo -n "Completed tasks (e.g., '3/9', press Enter to skip): "
    read completed
    
    echo -n "Actual hours spent (press Enter to skip): "
    read hours
    
    echo -n "Bugs found (press Enter to skip): "
    read bugs_found
    
    echo -n "Bugs fixed (press Enter to skip): "
    read bugs_fixed
    
    echo -n "Test coverage percentage (press Enter to skip): "
    read coverage
    
    # Build command
    cmd="python ${SCRIPT_DIR}/update_tracker.py ${SPRINT_NUMBER} metrics"
    
    if [ ! -z "$completed" ]; then
        cmd="${cmd} --completed \"${completed}\""
    fi
    
    if [ ! -z "$hours" ]; then
        cmd="${cmd} --hours ${hours}"
    fi
    
    if [ ! -z "$bugs_found" ]; then
        cmd="${cmd} --bugs-found ${bugs_found}"
    fi
    
    if [ ! -z "$bugs_fixed" ]; then
        cmd="${cmd} --bugs-fixed ${bugs_fixed}"
    fi
    
    if [ ! -z "$coverage" ]; then
        cmd="${cmd} --coverage ${coverage}"
    fi
    
    # Ask for performance metrics
    add_metrics=true
    while $add_metrics; do
        echo -n "Performance metric name (press Enter to stop adding metrics): "
        read metric_name
        
        if [ -z "$metric_name" ]; then
            add_metrics=false
        else
            echo -n "Value for ${metric_name}: "
            read metric_value
            cmd="${cmd} --perf \"${metric_name}\" \"${metric_value}\""
        fi
    done
    
    echo "Updating metrics..."
    eval "$cmd"
}

# Check if enough arguments were provided
if [ $# -lt 2 ]; then
    echo "Error: Not enough arguments."
    show_usage
    exit 1
fi

SPRINT_NUMBER="$1"
ACTION="$2"
shift 2  # Remove first two arguments, remaining args will be in $@

# Process the action
case "${ACTION}" in
    task)
        if [ $# -lt 3 ]; then
            echo "Error: Not enough arguments for task update."
            show_usage
            exit 1
        fi
        
        task_id="$1"
        status="$2"
        completion="$3"
        notes="${4:-}"
        assignee="${5:-}"
        
        process_task "$task_id" "$status" "$completion" "$notes" "$assignee"
        ;;
    
    done)
        if [ $# -lt 1 ]; then
            echo "Error: Task ID required."
            show_usage
            exit 1
        fi
        
        task_id="$1"
        notes="${2:-Task completed}"
        
        process_task "$task_id" "Completed" "100" "$notes"
        ;;
    
    start)
        if [ $# -lt 1 ]; then
            echo "Error: Task ID required."
            show_usage
            exit 1
        fi
        
        task_id="$1"
        assignee="${2:-$(whoami)}"
        
        process_task "$task_id" "In Progress" "10" "Started work" "$assignee"
        ;;
    
    progress)
        if [ $# -lt 2 ]; then
            echo "Error: Task ID and percentage required."
            show_usage
            exit 1
        fi
        
        task_id="$1"
        completion="$2"
        notes="${3:-Updated progress}"
        
        process_task "$task_id" "In Progress" "$completion" "$notes"
        ;;
    
    standup)
        if [ $# -lt 1 ]; then
            echo "Error: Standup notes required."
            show_usage
            exit 1
        fi
        
        notes="$*"
        process_standup "$notes"
        ;;
    
    metrics)
        interactive_metrics
        ;;
    
    help)
        show_usage
        ;;
    
    *)
        echo "Error: Unknown action '${ACTION}'"
        show_usage
        exit 1
        ;;
esac 