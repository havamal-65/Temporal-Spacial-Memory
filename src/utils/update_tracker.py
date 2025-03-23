#!/usr/bin/env python3
"""
Command-line utility for updating sprint tracker documents.
"""

import argparse
import sys
import os
from datetime import datetime
from sprint_tracker import SprintTracker

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Update sprint tracker documents")
    
    # Sprint number argument
    parser.add_argument(
        "sprint", 
        type=int, 
        help="Sprint number to update"
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Task update command
    task_parser = subparsers.add_parser("task", help="Update task status")
    task_parser.add_argument("task_id", help="Task ID (e.g., 1.1, 2.3)")
    task_parser.add_argument("status", help="Task status (e.g., 'In Progress', 'Completed')")
    task_parser.add_argument("completion", type=int, help="Completion percentage (0-100)")
    task_parser.add_argument("--notes", help="Additional notes about the task")
    task_parser.add_argument("--assigned", help="Person assigned to the task")
    
    # Standup command
    standup_parser = subparsers.add_parser("standup", help="Add standup entry")
    standup_parser.add_argument("--date", help="Date for standup (YYYY-MM-DD), defaults to today")
    standup_parser.add_argument("--person", required=True, help="Person name")
    standup_parser.add_argument("--notes", required=True, help="Standup notes for the person")
    
    # Accomplishment command
    accomplishment_parser = subparsers.add_parser("accomplishment", help="Add accomplishment")
    accomplishment_parser.add_argument("text", help="Accomplishment text")
    
    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="Update metrics")
    metrics_parser.add_argument("--completed", help="Completed tasks (e.g., '3/9')")
    metrics_parser.add_argument("--hours", type=int, help="Actual hours spent")
    metrics_parser.add_argument("--bugs-found", type=int, help="Number of bugs found")
    metrics_parser.add_argument("--bugs-fixed", type=int, help="Number of bugs fixed")
    metrics_parser.add_argument("--coverage", type=float, help="Test coverage percentage")
    metrics_parser.add_argument("--perf", action="append", nargs=2, 
                               metavar=("KEY", "VALUE"),
                               help="Performance metric (can be used multiple times)")
    
    # Sprint dates command
    dates_parser = subparsers.add_parser("dates", help="Set sprint dates")
    dates_parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    dates_parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    
    # Retrospective command
    retro_parser = subparsers.add_parser("retro", help="Update retrospective")
    retro_parser.add_argument("--well", action="append", help="What went well (can be used multiple times)")
    retro_parser.add_argument("--not-well", action="append", help="What didn't go well (can be used multiple times)")
    retro_parser.add_argument("--action", action="append", help="Action item for next sprint (can be used multiple times)")
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        tracker = SprintTracker(args.sprint)
        
        if args.command == "task":
            tracker.update_task_status(
                args.task_id,
                args.status,
                args.completion,
                args.notes,
                args.assigned
            )
        
        elif args.command == "standup":
            date = args.date or datetime.now().strftime("%Y-%m-%d")
            tracker.add_standup_entry(date, {args.person: args.notes})
        
        elif args.command == "accomplishment":
            tracker.add_accomplishment(args.text)
        
        elif args.command == "metrics":
            perf_metrics = {}
            if args.perf:
                for key, value in args.perf:
                    perf_metrics[key] = value
                    
            tracker.update_metrics(
                completed_tasks=args.completed,
                actual_hours=args.hours,
                bugs_found=args.bugs_found,
                bugs_fixed=args.bugs_fixed,
                test_coverage=args.coverage,
                performance_metrics=perf_metrics if perf_metrics else None
            )
        
        elif args.command == "dates":
            tracker.set_sprint_dates(args.start, args.end)
        
        elif args.command == "retro":
            tracker.update_retrospective(
                went_well=args.well,
                not_well=args.not_well,
                action_items=args.action
            )
        
        else:
            print("No command specified. Use -h for help.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 