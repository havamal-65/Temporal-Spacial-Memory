import os
import sys
import shutil
import hashlib
import datetime
import yaml
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import webbrowser

class DocumentProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GraphRAG Document Processor")
        self.root.geometry("900x600")
        self.setup_ui()
        
        # Check for required directories
        self.input_dir = "Input"
        self.output_dir = "Output"
        self.processed_docs_file = "processed_documents.yaml"
        self.processed_docs = self.load_processed_docs()
        
        if not os.path.exists(self.input_dir):
            os.makedirs(self.input_dir)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
    def load_processed_docs(self):
        """Load the list of processed documents and their output folders"""
        if os.path.exists(self.processed_docs_file):
            with open(self.processed_docs_file, 'r') as f:
                try:
                    return yaml.safe_load(f) or {}
                except yaml.YAMLError:
                    return {}
        return {}
    
    def save_processed_docs(self):
        """Save the list of processed documents"""
        with open(self.processed_docs_file, 'w') as f:
            yaml.dump(self.processed_docs, f)
    
    def setup_ui(self):
        """Set up the user interface"""
        # Create a frame for document selection
        input_frame = ttk.LabelFrame(self.root, text="Document Input")
        input_frame.pack(fill="x", padx=10, pady=10)
        
        # File selection
        ttk.Label(input_frame, text="Select Document:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.file_entry = ttk.Entry(input_frame, width=50)
        self.file_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=5, pady=5)
        
        # Document name
        ttk.Label(input_frame, text="Document Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.name_entry = ttk.Entry(input_frame, width=50)
        self.name_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Process button
        ttk.Button(input_frame, text="Process Document", command=self.process_document).grid(row=2, column=1, padx=5, pady=10)
        
        # Create a frame for the file browsers
        browser_frame = ttk.Frame(self.root)
        browser_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Input browser
        input_browser_frame = ttk.LabelFrame(browser_frame, text="Input Files")
        input_browser_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        self.input_tree = ttk.Treeview(input_browser_frame)
        self.input_tree["columns"] = ("Size", "Date")
        self.input_tree.column("#0", width=200, minwidth=200)
        self.input_tree.column("Size", width=100, minwidth=100)
        self.input_tree.column("Date", width=130, minwidth=130)
        self.input_tree.heading("#0", text="Name")
        self.input_tree.heading("Size", text="Size")
        self.input_tree.heading("Date", text="Date Modified")
        self.input_tree.pack(fill="both", expand=True)
        
        ttk.Button(input_browser_frame, text="Refresh", command=self.refresh_input_files).pack(pady=5)
        
        # Output browser
        output_browser_frame = ttk.LabelFrame(browser_frame, text="Output Files")
        output_browser_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        self.output_tree = ttk.Treeview(output_browser_frame)
        self.output_tree["columns"] = ("Type", "Date")
        self.output_tree.column("#0", width=200, minwidth=200)
        self.output_tree.column("Type", width=100, minwidth=100)
        self.output_tree.column("Date", width=130, minwidth=130)
        self.output_tree.heading("#0", text="Name")
        self.output_tree.heading("Type", text="Type")
        self.output_tree.heading("Date", text="Date Created")
        self.output_tree.pack(fill="both", expand=True)
        
        ttk.Button(output_browser_frame, text="Refresh", command=self.refresh_output_files).pack(pady=5)
        ttk.Button(output_browser_frame, text="Open Selected", command=self.open_selected_output).pack(pady=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")
        
        # Initialize the file browsers
        self.refresh_input_files()
        self.refresh_output_files()
        
    def browse_file(self):
        """Open file dialog to select a document"""
        file_path = filedialog.askopenfilename(
            title="Select Document",
            filetypes=[("Text Files", "*.txt"), ("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if file_path:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file_path)
            # Auto-fill the document name based on the filename
            base_name = os.path.basename(file_path)
            name, _ = os.path.splitext(base_name)
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, name)
    
    def refresh_input_files(self):
        """Refresh the input files treeview"""
        # Clear existing items
        for item in self.input_tree.get_children():
            self.input_tree.delete(item)
        
        # Add input files
        if os.path.exists(self.input_dir):
            for item in os.listdir(self.input_dir):
                item_path = os.path.join(self.input_dir, item)
                if os.path.isfile(item_path):
                    size_kb = os.path.getsize(item_path) / 1024
                    modified = datetime.datetime.fromtimestamp(os.path.getmtime(item_path)).strftime('%Y-%m-%d %H:%M:%S')
                    self.input_tree.insert("", "end", text=item, values=(f"{size_kb:.1f} KB", modified))
    
    def refresh_output_files(self):
        """Refresh the output files treeview"""
        # Clear existing items
        for item in self.output_tree.get_children():
            self.output_tree.delete(item)
        
        # Add output folders
        if os.path.exists(self.output_dir):
            for item in os.listdir(self.output_dir):
                item_path = os.path.join(self.output_dir, item)
                if os.path.isdir(item_path):
                    # Check for HTML files to determine type
                    has_visualization = False
                    for file in os.listdir(item_path):
                        if file.endswith(".html") and "visualization" in file:
                            has_visualization = True
                            break
                    
                    item_type = "Graph+Viz" if has_visualization else "Folder"
                    modified = datetime.datetime.fromtimestamp(os.path.getctime(item_path)).strftime('%Y-%m-%d %H:%M:%S')
                    self.output_tree.insert("", "end", text=item, values=(item_type, modified))
                elif item.endswith(".html"):
                    modified = datetime.datetime.fromtimestamp(os.path.getctime(item_path)).strftime('%Y-%m-%d %H:%M:%S')
                    self.output_tree.insert("", "end", text=item, values=("HTML", modified))
    
    def open_selected_output(self):
        """Open the selected output file or folder"""
        selected = self.output_tree.selection()
        if not selected:
            messagebox.showinfo("Information", "Please select an output item to open.")
            return
        
        item_id = selected[0]
        item_name = self.output_tree.item(item_id, "text")
        item_type = self.output_tree.item(item_id, "values")[0]
        
        item_path = os.path.join(self.output_dir, item_name)
        
        # If it's an HTML file, open in the browser
        if item_type == "HTML" or item_name.endswith(".html"):
            webbrowser.open(f"file://{os.path.abspath(item_path)}")
        elif os.path.isdir(item_path):
            # Look for visualization HTML files
            visualization_files = [
                f for f in os.listdir(item_path) 
                if f.endswith(".html") and ("visualization" in f or "dashboard" in f)
            ]
            
            if visualization_files:
                # Open the first visualization file
                viz_path = os.path.join(item_path, visualization_files[0])
                webbrowser.open(f"file://{os.path.abspath(viz_path)}")
            else:
                # Open the folder
                os.startfile(item_path) if sys.platform == 'win32' else subprocess.call(['open', item_path])
    
    def process_document(self):
        """Process the selected document"""
        file_path = self.file_entry.get().strip()
        doc_name = self.name_entry.get().strip()
        
        if not file_path:
            messagebox.showerror("Error", "Please select a document file.")
            return
        
        if not doc_name:
            messagebox.showerror("Error", "Please enter a document name.")
            return
        
        if not os.path.exists(file_path):
            messagebox.showerror("Error", "Selected file does not exist.")
            return
        
        # Create a document hash to check for duplicates
        with open(file_path, 'rb') as f:
            doc_hash = hashlib.md5(f.read()).hexdigest()
        
        # Check if we've processed this exact file before
        if doc_hash in self.processed_docs:
            existing_output = self.processed_docs[doc_hash]['output_dir']
            msg = f"This document has been processed before (output: {existing_output}).\nDo you want to process it again?"
            if messagebox.askyesno("Document Already Processed", msg):
                # User wants to process again - ask if they want to overwrite
                if messagebox.askyesno("Overwrite", "Do you want to overwrite the existing output?"):
                    output_folder = existing_output
                else:
                    # Create a new output folder with timestamp
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_folder = f"{doc_name}_{timestamp}"
                    self.processed_docs[doc_hash] = {
                        'name': doc_name,
                        'output_dir': output_folder,
                        'date': datetime.datetime.now().isoformat()
                    }
                    self.save_processed_docs()
            else:
                # User doesn't want to process again, just show the existing output
                messagebox.showinfo("Information", f"Using existing output in {existing_output}.")
                return
        else:
            # First time processing this document
            output_folder = doc_name
            
            # Check if folder already exists (different file with same name)
            if os.path.exists(os.path.join(self.output_dir, output_folder)):
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                output_folder = f"{doc_name}_{timestamp}"
            
            # Record this document
            self.processed_docs[doc_hash] = {
                'name': doc_name,
                'output_dir': output_folder,
                'date': datetime.datetime.now().isoformat()
            }
            self.save_processed_docs()
        
        # Create output directory
        full_output_path = os.path.join(self.output_dir, output_folder)
        if not os.path.exists(full_output_path):
            os.makedirs(full_output_path)
        
        # Copy the file to input directory if it's not already there
        input_file_path = os.path.join(self.input_dir, os.path.basename(file_path))
        if os.path.abspath(file_path) != os.path.abspath(input_file_path):
            shutil.copy2(file_path, input_file_path)
        
        # Update the settings.yaml file to use the new output folder
        self.update_settings_yaml(output_folder)
        
        # Run the GraphRAG indexing process
        self.status_var.set(f"Processing document: {doc_name}...")
        self.root.update()
        
        try:
            result = subprocess.run(
                ["python", "-m", "graphrag", "index", "--config", "settings.yaml", "--verbose"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                error_msg = f"Error processing document:\n{result.stderr}"
                messagebox.showerror("Processing Error", error_msg)
                self.status_var.set("Error processing document")
            else:
                self.status_var.set(f"Document processed successfully: {doc_name}")
                messagebox.showinfo("Success", f"Document processed successfully.\nOutput saved to: {output_folder}")
                
                # Refresh the file browsers
                self.refresh_input_files()
                self.refresh_output_files()
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
            self.status_var.set("Error processing document")
    
    def update_settings_yaml(self, output_folder):
        """Update the settings.yaml file to use the specified output folder"""
        if os.path.exists("settings.yaml"):
            with open("settings.yaml", 'r') as f:
                settings = yaml.safe_load(f)
            
            # Update output folder
            settings['output']['base_dir'] = os.path.join(self.output_dir, output_folder)
            
            # Update vector store path
            settings['vector_store']['default_vector_store']['db_uri'] = os.path.join(
                self.output_dir, output_folder, "lancedb"
            )
            
            with open("settings.yaml", 'w') as f:
                yaml.dump(settings, f)

def main():
    root = tk.Tk()
    app = DocumentProcessorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 