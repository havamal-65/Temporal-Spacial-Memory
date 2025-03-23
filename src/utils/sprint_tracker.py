import os
import re
from datetime import datetime

class SprintTracker:
    """Utility class to automatically update sprint tracker documents."""
    
    def __init__(self, sprint_number, planning_dir="Documents/planning"):
        """
        Initialize the sprint tracker.
        
        Args:
            sprint_number (int): The sprint number to track
            planning_dir (str): Directory containing planning documents
        """
        self.sprint_number = sprint_number
        self.planning_dir = planning_dir
        self.tasks_file = os.path.join(planning_dir, f"sprint{sprint_number}_tasks.md")
        self.tracker_file = os.path.join(planning_dir, f"sprint{sprint_number}_tracker.md")
        
        # Verify files exist
        if not os.path.exists(self.tasks_file):
            raise FileNotFoundError(f"Tasks file not found: {self.tasks_file}")
        if not os.path.exists(self.tracker_file):
            raise FileNotFoundError(f"Tracker file not found: {self.tracker_file}")
    
    def read_file(self, filepath):
        """Read file content."""
        with open(filepath, 'r') as f:
            return f.read()
    
    def write_file(self, filepath, content):
        """Write content to file."""
        with open(filepath, 'w') as f:
            f.write(content)
    
    def update_task_status(self, task_id, status, completion_percentage, notes=None, assigned_to=None):
        """
        Update the status of a specific task in the tracker.
        
        Args:
            task_id (str): Task ID (e.g., "1.1", "2.3")
            status (str): Status of the task (e.g., "In Progress", "Completed")
            completion_percentage (int): Percentage of completion (0-100)
            notes (str, optional): Additional notes about the task
            assigned_to (str, optional): Person assigned to the task
        """
        tracker_content = self.read_file(self.tracker_file)
        
        # Find the task row in the table
        task_pattern = re.compile(r'\|\s*' + re.escape(task_id) + r'\s*\|(.*?)\|\s*([^|]*)\s*\|\s*\d+\s*\|\s*[^|]*\s*\|\s*\d+%\s*\|\s*[^|]*\s*\|', re.DOTALL)
        
        def replace_task(match):
            desc = match.group(1)
            person = assigned_to if assigned_to is not None else match.group(2).strip()
            hours = re.search(r'\|\s*\d+\s*\|', match.group(0)).group(0)
            notes_text = notes if notes is not None else re.search(r'\|\s*[^|]*\s*\|$', match.group(0)).group(0)
            
            return f"| {task_id} |{desc}| {person} |{hours} {status} | {completion_percentage}% |{notes_text}"
        
        updated_content = task_pattern.sub(replace_task, tracker_content)
        
        # Write the updated content back to the file
        if updated_content != tracker_content:
            self.write_file(self.tracker_file, updated_content)
            print(f"Updated task {task_id} status to {status} ({completion_percentage}%)")
        else:
            print(f"No changes made to task {task_id}")
    
    def update_metrics(self, completed_tasks=None, actual_hours=None, bugs_found=None, 
                      bugs_fixed=None, test_coverage=None, performance_metrics=None):
        """
        Update the metrics section of the tracker.
        
        Args:
            completed_tasks (int, optional): Number of completed tasks
            actual_hours (int, optional): Actual hours spent
            bugs_found (int, optional): Number of bugs found
            bugs_fixed (int, optional): Number of bugs fixed
            test_coverage (float, optional): Test coverage percentage
            performance_metrics (dict, optional): Performance metrics
        """
        tracker_content = self.read_file(self.tracker_file)
        
        # Calculate total tasks if not provided
        if completed_tasks is None:
            # Count tasks with 100% completion
            completed_count = len(re.findall(r'\|\s*\d+\.\d+\s*\|.*?\|\s*.*?\s*\|\s*\d+\s*\|\s*Completed\s*\|\s*100%\s*\|', tracker_content))
            total_count = len(re.findall(r'\|\s*\d+\.\d+\s*\|', tracker_content))
            completed_tasks = f"{completed_count}/{total_count}"
        
        # Update metrics section
        metrics_section = "## Metrics\n"
        
        # Planned vs. Completed Tasks
        if completed_tasks:
            tracker_content = re.sub(
                r'- \*\*Planned vs\. Completed Tasks\*\*: \[.*?\]', 
                f'- **Planned vs. Completed Tasks**: [{completed_tasks}]', 
                tracker_content
            )
        
        # Estimated vs. Actual Hours
        if actual_hours:
            # Extract total estimated hours
            estimated_hours = sum([int(h) for h in re.findall(r'\|\s*\d+\.\d+\s*\|.*?\|\s*.*?\s*\|\s*(\d+)\s*\|', tracker_content)])
            tracker_content = re.sub(
                r'- \*\*Estimated vs\. Actual Hours\*\*: \[.*?\]', 
                f'- **Estimated vs. Actual Hours**: [{actual_hours}/{estimated_hours}]', 
                tracker_content
            )
        
        # Bugs Found/Fixed
        if bugs_found or bugs_fixed:
            bugs_str = f"{bugs_found if bugs_found else 0}/{bugs_fixed if bugs_fixed else 0}"
            tracker_content = re.sub(
                r'- \*\*Bugs Found/Fixed\*\*: \[.*?\]', 
                f'- **Bugs Found/Fixed**: [{bugs_str}]', 
                tracker_content
            )
        
        # Test Coverage
        if test_coverage:
            tracker_content = re.sub(
                r'- \*\*Test Coverage\*\*: \[.*?\]', 
                f'- **Test Coverage**: [{test_coverage}%]', 
                tracker_content
            )
        
        # Performance Metrics
        if performance_metrics:
            perf_section = re.search(r'- \*\*Performance Metrics\*\*:\s*(.*?)(?=^##|\Z)', tracker_content, re.DOTALL | re.MULTILINE)
            if perf_section:
                perf_content = perf_section.group(1)
                updated_perf = "- **Performance Metrics**: \n"
                for key, value in performance_metrics.items():
                    # Check if metric already exists
                    if re.search(rf"  - {key}:", perf_content):
                        # Update existing metric
                        perf_content = re.sub(rf"  - {key}: .*", f"  - {key}: {value}", perf_content)
                    else:
                        # Add new metric
                        perf_content += f"  - {key}: {value}\n"
                
                tracker_content = re.sub(
                    r'- \*\*Performance Metrics\*\*:.*?(?=^##|\Z)', 
                    f"- **Performance Metrics**: \n{perf_content}", 
                    tracker_content, 
                    flags=re.DOTALL | re.MULTILINE
                )
        
        self.write_file(self.tracker_file, tracker_content)
        print("Updated metrics in the tracker.")
    
    def add_standup_entry(self, date=None, entries=None):
        """
        Add a new standup entry for the given date.
        
        Args:
            date (str, optional): Date string (defaults to today)
            entries (dict, optional): Dictionary of person -> notes entries
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        if entries is None or not entries:
            print("No entries provided for standup.")
            return
        
        tracker_content = self.read_file(self.tracker_file)
        
        # Check if entry for this date already exists
        day_pattern = re.compile(rf'### Day \d+ \({date}\)')
        if day_pattern.search(tracker_content):
            # Update existing entry
            day_section = re.search(rf'### Day \d+ \({date}\)(.*?)(?=^###|\Z)', tracker_content, re.DOTALL | re.MULTILINE)
            if day_section:
                day_content = day_section.group(1)
                updated_content = f"\n"
                for person, notes in entries.items():
                    # Check if person already has an entry
                    if re.search(rf"- \[{re.escape(person)}\]:", day_content):
                        # Update existing person entry
                        day_content = re.sub(
                            rf"- \[{re.escape(person)}\]:.*", 
                            f"- [{person}]: {notes}", 
                            day_content
                        )
                    else:
                        # Add new person entry
                        updated_content += f"- [{person}]: {notes}\n"
                
                updated_day = day_content + updated_content if not re.search(rf"- \[.*?\]:", day_content) else day_content
                
                tracker_content = re.sub(
                    rf'### Day \d+ \({date}\).*?(?=^###|\Z)', 
                    f"### Day X ({date}){updated_day}", 
                    tracker_content, 
                    flags=re.DOTALL | re.MULTILINE
                )
            
        else:
            # Find the last day entry
            day_entries = re.findall(r'### Day (\d+)', tracker_content)
            next_day_number = 1
            if day_entries:
                next_day_number = max([int(d) for d in day_entries]) + 1
            
            # Create new day entry
            standup_section = "## Daily Stand-up Notes\n"
            new_day_entry = f"\n### Day {next_day_number} ({date})\n"
            for person, notes in entries.items():
                new_day_entry += f"- [{person}]: {notes}\n"
            
            # Insert after the standup section
            if "## Daily Stand-up Notes" in tracker_content:
                pattern = r'## Daily Stand-up Notes\s*\n(.*?)(?=^##|\Z)'
                match = re.search(pattern, tracker_content, re.DOTALL | re.MULTILINE)
                if match:
                    existing_content = match.group(1)
                    tracker_content = re.sub(
                        pattern,
                        f"## Daily Stand-up Notes\n{existing_content}{new_day_entry}\n",
                        tracker_content,
                        flags=re.DOTALL | re.MULTILINE
                    )
            
        self.write_file(self.tracker_file, tracker_content)
        print(f"Added standup entry for {date}.")
    
    def add_accomplishment(self, accomplishment):
        """
        Add an accomplishment to the tracker.
        
        Args:
            accomplishment (str): The accomplishment to add
        """
        tracker_content = self.read_file(self.tracker_file)
        
        # Find the accomplishments section
        accomplishments_section = re.search(r'## Accomplishments\s*\n(.*?)(?=^##|\Z)', tracker_content, re.DOTALL | re.MULTILINE)
        if accomplishments_section:
            existing_content = accomplishments_section.group(1)
            # Add the new accomplishment
            updated_content = existing_content
            if not accomplishment.startswith('-'):
                accomplishment = f"- {accomplishment}"
            
            # Check if accomplishment already exists
            if accomplishment.strip() not in existing_content:
                updated_content += f"{accomplishment}\n"
            
            tracker_content = re.sub(
                r'## Accomplishments\s*\n.*?(?=^##|\Z)',
                f"## Accomplishments\n{updated_content}",
                tracker_content,
                flags=re.DOTALL | re.MULTILINE
            )
            
            self.write_file(self.tracker_file, tracker_content)
            print(f"Added accomplishment: {accomplishment}")
        else:
            print("Accomplishments section not found in the tracker.")
    
    def set_sprint_dates(self, start_date=None, end_date=None):
        """
        Set the sprint start and end dates.
        
        Args:
            start_date (str, optional): Start date (defaults to today)
            end_date (str, optional): End date
        """
        if start_date is None:
            start_date = datetime.now().strftime("%Y-%m-%d")
        
        tracker_content = self.read_file(self.tracker_file)
        
        # Update start date
        if start_date:
            tracker_content = re.sub(
                r'\*\*Start Date:\*\* .*',
                f"**Start Date:** {start_date}",
                tracker_content
            )
        
        # Update end date
        if end_date:
            tracker_content = re.sub(
                r'\*\*End Date:\*\* .*',
                f"**End Date:** {end_date}",
                tracker_content
            )
        
        self.write_file(self.tracker_file, tracker_content)
        print(f"Set sprint dates: Start={start_date}, End={end_date if end_date else 'TBD'}")
    
    def update_retrospective(self, went_well=None, not_well=None, action_items=None):
        """
        Update the sprint retrospective section.
        
        Args:
            went_well (list, optional): List of things that went well
            not_well (list, optional): List of things that didn't go well
            action_items (list, optional): List of action items for next sprint
        """
        tracker_content = self.read_file(self.tracker_file)
        
        # Update "What Went Well" section
        if went_well:
            well_pattern = r'### What Went Well\s*\n(.*?)(?=^###|\Z)'
            match = re.search(well_pattern, tracker_content, re.DOTALL | re.MULTILINE)
            if match:
                new_content = "### What Went Well\n"
                for item in went_well:
                    new_content += f"- {item}\n"
                
                tracker_content = re.sub(
                    well_pattern,
                    new_content + "\n",
                    tracker_content,
                    flags=re.DOTALL | re.MULTILINE
                )
        
        # Update "What Didn't Go Well" section
        if not_well:
            not_well_pattern = r'### What Didn\'t Go Well\s*\n(.*?)(?=^###|\Z)'
            match = re.search(not_well_pattern, tracker_content, re.DOTALL | re.MULTILINE)
            if match:
                new_content = "### What Didn't Go Well\n"
                for item in not_well:
                    new_content += f"- {item}\n"
                
                tracker_content = re.sub(
                    not_well_pattern,
                    new_content + "\n",
                    tracker_content,
                    flags=re.DOTALL | re.MULTILINE
                )
        
        # Update "Action Items for Next Sprint" section
        if action_items:
            action_pattern = r'### Action Items for Next Sprint\s*\n(.*?)(?=^##|\Z)'
            match = re.search(action_pattern, tracker_content, re.DOTALL | re.MULTILINE)
            if match:
                new_content = "### Action Items for Next Sprint\n"
                for item in action_items:
                    new_content += f"- {item}\n"
                
                tracker_content = re.sub(
                    action_pattern,
                    new_content + "\n",
                    tracker_content,
                    flags=re.DOTALL | re.MULTILINE
                )
        
        self.write_file(self.tracker_file, tracker_content)
        print("Updated retrospective sections.")


# Example usage
if __name__ == "__main__":
    # Create a tracker for sprint 2
    tracker = SprintTracker(2)
    
    # Set sprint dates
    tracker.set_sprint_dates("2023-05-01", "2023-05-14")
    
    # Update a task status
    tracker.update_task_status("1.1", "In Progress", 30, "Working on QueryEngine implementation", "Alice")
    
    # Add a standup entry
    tracker.add_standup_entry("2023-05-02", {
        "Alice": "Completed the query plan generation, working on execution strategies today. No blockers.",
        "Bob": "Working on index selection logic. Need clarification on cost model.",
        "Charlie": "Starting implementation of result pagination. No blockers."
    })
    
    # Add an accomplishment
    tracker.add_accomplishment("Implemented initial version of QueryEngine with basic execution capabilities")
    
    # Update metrics
    tracker.update_metrics(
        completed_tasks="1/9",
        actual_hours=12,
        bugs_found=3,
        bugs_fixed=2,
        test_coverage=68,
        performance_metrics={
            "Query execution time": "150ms average",
            "Index lookup performance": "12ms per lookup",
            "Memory usage": "45MB peak"
        }
    )
    
    print("Sprint tracker updated successfully!") 