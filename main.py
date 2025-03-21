import tkinter as tk
from tkinter import Menu, filedialog, messagebox
from PIL import Image, ImageTk
import os
import yaml
import subprocess
import threading
import sys
from tkinter import ttk
import webbrowser

# Load YAML configuration
def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

config = load_yaml('0_config.yaml')  # Load config

def open_help_link():
    url = "https://docs.google.com/presentation/d/1GKsw4e6UGEFhFP3W1ZAoSSxLRf7SaCxO06ve7mZ2mEY"  # Replace with your actual URL
    webbrowser.open_new_tab(url)


# Redirect console output to a text widget
class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.insert(tk.END, string + "\n")  # Add newline for readability
        self.text_widget.see(tk.END)  # Auto-scroll to the bottom
        self.text_widget.update_idletasks()  # Ensure UI updates immediately

    def flush(self):
        pass  # Not needed

def redirect_stdout_to_widget(text_widget):
    """Redirects stdout and stderr to the given text widget."""
    sys.stdout = RedirectText(text_widget)
    sys.stderr = RedirectText(text_widget)  # Also capture stderr for errors

class BasePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.text_output = None  # Placeholder for text widget

    def setup_output_widget(self, text_widget):
        """Set up output redirection for the text widget."""
        self.text_output = text_widget
        
        sys.stderr = RedirectText(self.text_output)  # Also capture errors

    def launch_script(self, script_path):
        """Launches an external script and redirects its output to the text widget."""
        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"Script file not found: {script_path}")
            return

        def run():
            try:
                pythonw_path = config.get('pythonw', sys.executable)  # Use default Python if not specified
                process = subprocess.Popen(
                    [pythonw_path, '-u', script_path], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True, 
                    bufsize=1
                )

                # Redirect both stdout and stderr to the text widget
                def read_stream(stream, tag):
                    for line in iter(stream.readline, ''):
                        self.text_output.insert(tk.END, line, tag)  # Insert into text widget
                        self.text_output.see(tk.END)  # Auto-scroll to latest output
                        stream.flush()

                stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, "stdout"))
                stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, "stderr"))

                stdout_thread.start()
                stderr_thread.start()

                stdout_thread.join()
                stderr_thread.join()

                process.stdout.close()
                process.stderr.close()
                process.wait()

                messagebox.showinfo("Success", "Script finished successfully!")

            except Exception as e:
                error_msg = f"Error: {e}\n"
                self.text_output.insert(tk.END, error_msg, "stderr")  # Show error in text widget
                messagebox.showerror("Error", f"Failed to launch script:\n{e}")

        # Start the script in a separate thread to avoid blocking the UI
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        # Add color tags for stdout and stderr
        self.text_output.tag_config("stdout", foreground="black")
        self.text_output.tag_config("stderr", foreground="red")  # Errors in red

    def launch_script_mod(self, script_path, myEntry, myCombobox):
        """Launches an external script and redirects its output to the text widget."""
        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"Script file not found: {script_path}")
            return

        def run():
            try:
                pythonw_path = config.get('pythonw', sys.executable)  # Use default Python if not specified
                
                entry_value  = myEntry.get()
                combo_value  = myCombobox.get()

                if not entry_value or not combo_value:
                    print("Please enter all fields before launching the script.")
                    return
                
                process = subprocess.Popen(
                    [pythonw_path, '-u', script_path, entry_value, combo_value], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True, 
                    bufsize=1
                )

                # Redirect both stdout and stderr to the text widget
                def read_stream(stream, tag):
                    for line in iter(stream.readline, ''):
                        self.text_output.insert(tk.END, line, tag)  # Insert into text widget
                        self.text_output.see(tk.END)  # Auto-scroll to latest output
                        stream.flush()

                stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, "stdout"))
                stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, "stderr"))

                stdout_thread.start()
                stderr_thread.start()

                stdout_thread.join()
                stderr_thread.join()

                process.stdout.close()
                process.stderr.close()
                process.wait()

                messagebox.showinfo("Success", "Script finished successfully!")

            except Exception as e:
                error_msg = f"Error: {e}\n"
                self.text_output.insert(tk.END, error_msg, "stderr")  # Show error in text widget
                messagebox.showerror("Error", f"Failed to launch script:\n{e}")

        # Start the script in a separate thread to avoid blocking the UI
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        # Add color tags for stdout and stderr
        self.text_output.tag_config("stdout", foreground="black")
        self.text_output.tag_config("stderr", foreground="red")  # Errors in red
        

# ====================== MAIN APPLICATION CLASS ======================
class MyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ATO Impact Tool")
        height = 600
        width = 550
        self.root.geometry(f"{width}x{height}")
        
        # set the gui style
        style = ttk.Style()
        style.theme_use("clam")  # Change this to "alt", "default", etc.

        # Create menu bar
        menu_bar = Menu(root)
        root.config(menu=menu_bar)

        # File menu
        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=root.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)
        

        # Settings menu
        setup_menu = Menu(menu_bar, tearoff=0)
        setup_menu.add_command(label="Edit configurations", command=self.open_config_file)
        menu_bar.add_cascade(label="Settings", menu=setup_menu)

        info_menu = Menu(menu_bar, tearoff=0)
        info_menu.add_command(label="Help", command=open_help_link)
        info_menu.add_command(label="About", command=None)
        menu_bar.add_cascade(label="Info", menu=info_menu)

        # ===================== PAGE CONTAINER =====================
        self.container = tk.Frame(root)
        self.container.pack(fill="both", expand=True)

        # Dictionary to store pages
        self.pages = {}

        # Create pages
        for Page in (MainMenu, NetworkSetupPage, TazSetupPage, ModProjectsPage, ModDrivePage, ModBikePage, ScoreModsPage):
            page_instance = Page(self.container, self)
            self.pages[Page] = page_instance
            page_instance.grid(row=0, column=0, sticky="nsew")

        self.show_page(MainMenu)  # Show the main menu first

    def show_page(self, page):
        """Raises the selected page to the front and updates stdout redirection."""
        self.pages[page].tkraise()

        # Redirect stdout dynamically to the selected page's text_output
        if hasattr(self.pages[page], 'text_output'):
            sys.stdout = RedirectText(self.pages[page].text_output)

    def open_file(self):
        file_path = filedialog.askopenfilename(title="Open File")
        if file_path:
            self.pages[MainMenu].load_image(file_path)

    def open_config_file(self):
        """Opens the configuration file."""
        filepath = '0_config.yaml'
        try:
            if os.name == 'nt':  # Windows
                os.startfile(filepath)
        except Exception as e:
            print(f"Error opening file: {e}")

# ====================== MAIN MENU PAGE CLASS ======================

class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        header_text = 'Main Menu'

        style = ttk.Style()
        style.configure("Custom.TLabelframe.Label", font=("Calibri", 12, "bold"), foreground="black")
        
        # Create LabelFrame with reduced width settings
        frame = ttk.LabelFrame(self, text=header_text, style="Custom.TLabelframe", padding=(10, 10))
        frame.pack(padx=10, pady=10, fill="x")  # Prevent full expansion
        frame.config(width=550)  
        
        # Left frame with buttons
        left_frame = ttk.Frame(frame)
        left_frame.grid(row=0, column=0, sticky="n", padx=10, pady=10)

        # Create buttons
        btn1 = ttk.Button(left_frame, text="1) Network Setup", width=20,  padding=(35, 15),
                         command=lambda: controller.show_page(NetworkSetupPage))
        btn1.grid(row=0, column=0, pady=5)

        btn2 = ttk.Button(left_frame, text="2) TAZ Setup", width=20,  padding=(35, 15),
                         command=lambda: controller.show_page(TazSetupPage))
        btn2.grid(row=1, column=0, pady=5)

        btn3 = ttk.Button(left_frame, text="3) Mod Projects", width=20, padding=(35, 15),
                         command=lambda: controller.show_page(ModProjectsPage))
        btn3.grid(row=2, column=0, pady=5)

        btn4 = ttk.Button(left_frame, text="4) Score Projects", width=20,padding=(35, 15), 
                          command=lambda: controller.show_page(ScoreModsPage))
        btn4.grid(row=3, column=0, pady=5)

        # Right frame for image
        self.right_frame = ttk.Frame(frame)
        self.right_frame.grid(row=0, column=1, padx=20)

        # Load image
        self.load_image("ato_graphic.png")  # Change to actual image path


    def load_image(self, image_path):
        """Loads an image into the right frame."""
        try:
            image = Image.open(image_path)
            image = image.resize((150, 300))  # Resize image
            self.img = ImageTk.PhotoImage(image)

            # Clear previous image
            for widget in self.right_frame.winfo_children():
                widget.destroy()

            label = tk.Label(self.right_frame, image=self.img, bd=2, relief="solid")
            label.pack()
        except Exception as e:
            print(f"Error loading image: {e}")

# ====================== NETWORK SETUP PAGE CLASS ======================

class NetworkSetupPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        header_text = '1) Network Setup'
        description_text = "This script prepares the Network Dataset datasets used for all ATO calculations."
        script_name = 'network_setup'

        style = ttk.Style()
        style.configure("Custom.TLabelframe.Label", font=("Arial", 12, "bold"), foreground="black")

        # Create LabelFrame with reduced width settings
        frame = ttk.LabelFrame(self, text=header_text, style="Custom.TLabelframe", padding=(10, 10))
        frame.pack(padx=10, pady=10, fill="x")  # Prevent full expansion
        frame.config(width=550)  

        # Description label with wrapping to avoid excessive width
        desc_label = ttk.Label(frame, text=description_text, wraplength=525)  # Prevents it from stretching too wide
        desc_label.grid(row=0, column=0, columnspan=2, pady=5, sticky="w")

        # Navigation buttons with fixed width to prevent excessive stretching
        back_button = ttk.Button(frame, text="🠜 Go Back", command=lambda: controller.show_page(MainMenu))
        run_button = ttk.Button(frame, text="Run Script 🠞", command=lambda: self.launch_script(config[script_name]))
        
        back_button.grid(row=3, column=0, padx=5, pady=5, sticky="w")  # No "sticky" to prevent full row stretch
        run_button.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        back_button.config(width=15)  # Set a fixed width
        run_button.config(width=20)  # Set a fixed width

        # Output text box inside a small frame
        self.text_frame = tk.Frame(frame)
        self.text_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=10)  # Prevent full stretch

        self.text_output = tk.Text(self.text_frame, wrap="word", height=10, width=40)  # Reduce width from 50 to 30
        self.text_output.pack(side=tk.LEFT, fill=tk.Y)  # No full horizontal expansion

        self.scrollbar = ttk.Scrollbar(self.text_frame, command=self.text_output.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_output.config(yscrollcommand=self.scrollbar.set)

        # Prevent frame columns from stretching too much
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=0)
        frame.rowconfigure(2, weight=0)  # Prevent text widget from taking too much space

        # Redirect stdout to this page's text widget
        self.setup_output_widget(self.text_output)

# ====================== TAZ SETUP PAGE CLASS ======================
class TazSetupPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        header_text = '2) TAZ Setup'
        description_text = "This script prepares the TAZ dataset used for all ATO calculations."
        script_name = 'taz_setup'
        
        style = ttk.Style()
        style.configure("Custom.TLabelframe.Label", font=("Arial", 12, "bold"), foreground="black")
        
        # Create LabelFrame with reduced width settings
        frame = ttk.LabelFrame(self, text=header_text, style="Custom.TLabelframe", padding=(10, 10))
        frame.pack(padx=10, pady=10, fill="x")  # Prevent full expansion
        frame.config(width=550)  

        # Description label with wrapping to avoid excessive width
        desc_label = ttk.Label(frame, text=description_text, wraplength=525)  # Prevents it from stretching too wide
        desc_label.grid(row=0, column=0, columnspan=2, pady=5, sticky="w")

        # Navigation buttons with fixed width to prevent excessive stretching
        back_button = ttk.Button(frame, text="🠜 Go Back", command=lambda: controller.show_page(MainMenu))
        run_button = ttk.Button(frame, text="Run Script 🠞", command=lambda: self.launch_script(config[script_name]))
        
        back_button.grid(row=3, column=0, padx=5, pady=5, sticky="w")  # No "sticky" to prevent full row stretch
        run_button.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        back_button.config(width=15)  # Set a fixed width
        run_button.config(width=20)  # Set a fixed width

        # Output text box inside a small frame
        self.text_frame = tk.Frame(frame)
        self.text_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=10)  # Prevent full stretch

        self.text_output = tk.Text(self.text_frame, wrap="word", height=10, width=40)  # Reduce width from 50 to 30
        self.text_output.pack(side=tk.LEFT, fill=tk.Y)  # No full horizontal expansion

        self.scrollbar = ttk.Scrollbar(self.text_frame, command=self.text_output.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_output.config(yscrollcommand=self.scrollbar.set)

        # Prevent frame columns from stretching too much
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=0)
        frame.rowconfigure(2, weight=0)  # Prevent text widget from taking too much space

        # Redirect stdout to this page's text widget
        self.setup_output_widget(self.text_output)

    

# ====================== SCORE MODS PAGE CLASS ======================
class ScoreModsPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)

        header_text = '4) Score Mods'
        description_text = '''This script scores the configured scenarios.\n\nAny unscored scenarios will be scored.\n\nTo re-score a scenario, open its corresponding file \ngeodatabaseand delete its "scores" and "scores_summary" table. '''
        script_name = 'score'
        
        style = ttk.Style()
        style.configure("Custom.TLabelframe.Label", font=("Arial", 12, "bold"), foreground="black")
        
        # Create LabelFrame with reduced width settings
        frame = ttk.LabelFrame(self, text=header_text, style="Custom.TLabelframe", padding=(10, 10))
        frame.pack(padx=10, pady=10, fill="x")  # Prevent full expansion
        frame.config(width=550)  

        # Description label with wrapping to avoid excessive width
        desc_label = ttk.Label(frame, text=description_text, wraplength=525)  # Prevents it from stretching too wide
        desc_label.grid(row=0, column=0, columnspan=2, pady=5, sticky="w")

        # Navigation buttons with fixed width to prevent excessive stretching
        back_button = ttk.Button(frame, text="🠜 Go Back", command=lambda: controller.show_page(MainMenu))
        back_button.config(width=15)  # Set a fixed width
        back_button.grid(row=3, column=0, padx=5, pady=5, sticky="w")  # No "sticky" to prevent full row stretch
        
        # run button
        run_button = ttk.Button(frame, text="Run Script 🠞", command=lambda: self.launch_script(config[script_name]))
        run_button.config(width=20)  # Set a fixed width
        run_button.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        
        # Output text box inside a small frame
        self.text_frame = tk.Frame(frame)
        self.text_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=10)  # Prevent full stretch

        self.text_output = tk.Text(self.text_frame, wrap="word", height=10, width=40)  # Reduce width from 50 to 30
        self.text_output.pack(side=tk.LEFT, fill=tk.Y)  # No full horizontal expansion

        self.scrollbar = ttk.Scrollbar(self.text_frame, command=self.text_output.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_output.config(yscrollcommand=self.scrollbar.set)

        # Prevent frame columns from stretching too much
        frame.columnconfigure(0, weight=0)
        frame.columnconfigure(1, weight=0)
        frame.rowconfigure(2, weight=0)  # Prevent text widget from taking too much space

        # Redirect stdout to this page's text widget
        self.setup_output_widget(self.text_output)
        
        
#======================== MOD PROJECTS PAGE ==========================

class ModProjectsPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        header_text = '3) Mod Projects'
        description_text = '''Select which type of modification to add (Drive, Transit, Bike, Land Use).\n\nOnce all of the desired mods are created, use the fourth script in the Main Menu to score them all at once.'''

        style = ttk.Style()
        style.configure("Custom.TLabelframe.Label", font=("Calibri", 12, "bold"), foreground="black")
        
        # Create LabelFrame with reduced width settings
        frame = ttk.LabelFrame(self, text=header_text, style="Custom.TLabelframe", padding=(10, 10))
        frame.pack(padx=10, pady=10, fill="x")  # Prevent full expansion
        frame.config(width=550)  
    
        desc_label = ttk.Label(frame, text=description_text, wraplength=500)
        desc_label.grid(row=0, column=0, columnspan=2, pady=10, sticky="w")

        button_frame = ttk.LabelFrame(frame, text='Select a Mod Type:',  padding=(15, 15))
        button_frame.grid(row=1, column=0, pady=5, sticky="w")
        button_frame.config(width=550)  

        # Create buttons
        btn1 = ttk.Button(button_frame, text="A) Mod Drive", width=20,  padding=(35, 15),
                         command=lambda: controller.show_page(ModDrivePage))
        btn1.grid(row=1, column=0, padx=5, pady=5, sticky='w')

        btn2 = ttk.Button(button_frame, text="B) Mod Transit", width=20,  padding=(35, 15),
                         command=lambda: controller.show_page(TazSetupPage))
        btn2.grid(row=2, column=0, padx=5, pady=5, sticky='w')

        btn3 = ttk.Button(button_frame, text="C) Mod Bike", width=20, padding=(35, 15),
                         command=lambda: controller.show_page(ModBikePage)) 
        btn3.grid(row=3, column=0, padx=5, pady=5, sticky='w')

        btn4 = ttk.Button(button_frame, text="D) Mod Land Use", width=20,padding=(35, 15), 
                          command=lambda: controller.show_page(ScoreModsPage))
        btn4.grid(row=4, column=0, padx=5, pady=5, sticky='w')

        back_button = ttk.Button(frame, text="🠜 Go Back", width=10,padding=(5, 5), command=lambda: controller.show_page(MainMenu))
        back_button.config(width=15)  
        back_button.grid(row=5, column=0,  padx=5, pady=5, sticky="w")


# ====================== MOD DRIVE PAGE CLASS ======================
class ModDrivePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        
        header_text = '3A) Mod Drive'
        description_text = '''Modify a copy of the baseline NetworkDataset with the candidate for improvement for road projects.\n\n1. Set the scenario name in the cell below before running the script.\n\n2. Run the script, ArcGIS Pro will launch.\n\n3. IMPORTANT: When you are done making your edits, leave the edited feature selected.\n\n4. Remember to save your edits and the project when you are finished'''
        script_name = 'mod_drive'

        style = ttk.Style()
        style.configure("Custom.TLabelframe.Label", font=("Calibri", 12, "bold"), foreground="black")
        
        frame = ttk.LabelFrame(self, text=header_text, style="Custom.TLabelframe",  padding=(10, 10))
        frame.pack(padx=10, pady=10, fill="x")
        frame.config(width=550) 
        
        desc_label = ttk.Label(frame, text=description_text, wraplength=525)
        desc_label.grid(row=0, column=0, columnspan=2, pady=5, sticky='w')

        # User input frame
        input_frame = ttk.LabelFrame(frame, padding=(5, 5))
        input_frame.grid(row=1, column=0, pady=5, sticky='w')

        # Scenario Name Label
        entry_label = ttk.Label(input_frame, text="Scenario Name:")
        entry_label.grid(row=0, column=0, pady=5, sticky='w')

        # Scenario Name Entry Widget
        user_input = ttk.Entry(input_frame, width=30)
        user_input.grid(row=0, column=1, pady=5, sticky='w')

        # Mod Type
        dropdown_label = ttk.Label(input_frame, text="Modification Type:")
        dropdown_label.grid(row=1, column=0, pady=5, sticky='w')

        # Options for the dropdown
        options = ["New Construction", "Widening | Restripe", "Operational", "New Interchange", "Grade-separated Crossing"]

        # Create the dropdown menu
        dropdown = ttk.Combobox(input_frame, values=options, width=30)
        dropdown.grid(row=1, column=1, pady=5, sticky='w')

        # run button
        run_button = ttk.Button(input_frame, text="Run Script 🠞", command=lambda: self.launch_script_mod(config['mod_drive'], user_input, dropdown))
        run_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        run_button.config(width=20)  # Set a fixed width
        
        # Output text box
        self.text_frame = tk.Frame(frame)
        self.text_frame.grid(row=3, column=0, columnspan=2,  sticky="nsew", padx=10, pady=10)

        self.text_output = tk.Text(self.text_frame, wrap="word", height=10, width=50)
        self.text_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self.text_frame, command=self.text_output.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_output.config(yscrollcommand=self.scrollbar.set)

        # Make sure rows resize properly
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)  # Allow text widget to expand

        # Redirect stdout to Text widget
        back_button = ttk.Button(frame, text="🠜 Go Back", command=lambda: controller.show_page(ModProjectsPage))
        back_button.config(width=15)  # Set a fixed width
        back_button.grid(row=4, column=0, padx=5, pady=5, sticky="w")





# ====================== MOD BIKE PAGE CLASS ======================
class ModBikePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        
        header_text = '3C) Mod Bike'
        description_text = '''Modify a copy of the baseline NetworkDataset with the candidate for improvement for bicycle projects.\n\n1. Set the scenario name and improvement type in the cell below before running the script.\n\n2. Run the script, ArcGIS Pro will launch.\n\n3. IMPORTANT: When you are done making your edits, leave the edited feature selected.\n\n4. Remember to save your edits and the project when you are finished'''
        script_name = 'mod_bike'
        
        style = ttk.Style()
        style.configure("Custom.TLabelframe.Label", font=("Calibri", 12, "bold"), foreground="black")
        
        frame = ttk.LabelFrame(self, text=header_text, style="Custom.TLabelframe",  padding=(10, 10))
        frame.pack(padx=10, pady=10, fill="x")
        frame.config(width=550) 
        
        desc_label = ttk.Label(frame, text=description_text, wraplength=525)
        desc_label.grid(row=0, column=0, columnspan=2, pady=5, sticky='w')

        # User input frame
        input_frame = ttk.LabelFrame(frame, padding=(5, 5))
        input_frame.grid(row=1, column=0, pady=5, sticky='w')

        # Scenario Name Label
        entry_label = ttk.Label(input_frame, text="Scenario Name:")
        entry_label.grid(row=0, column=0, pady=5, sticky='w')

        # Scenario Name Entry Widget
        user_input = ttk.Entry(input_frame, width=30)
        user_input.grid(row=0, column=1, pady=5, sticky='w')

        # Facility Type
        dropdown_label = ttk.Label(input_frame, text="Bike Facility Type:")
        dropdown_label.grid(row=1, column=0, pady=5, sticky='w')


        # Options for the dropdown
        options = ["shared_lane", "shoulder_bikeway", "bike_lane", "buffered_bike_lane", "protected_bike_lane", "bike_blvd", "shared_use_path"]

    
        # Create the dropdown menu
        dropdown = ttk.Combobox(input_frame, values=options, width=30)
        dropdown.grid(row=1, column=1, pady=5, sticky='w')

        # run button
        run_button = ttk.Button(input_frame, text="Run Script 🠞", command=lambda: self.launch_script_mod(config[script_name], user_input, dropdown))
        run_button.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        run_button.config(width=20)
        
        # Output text box
        self.text_frame = tk.Frame(frame)
        self.text_frame.grid(row=3, column=0, columnspan=2,  sticky="nsew", padx=10, pady=10)

        self.text_output = tk.Text(self.text_frame, wrap="word", height=10, width=50)
        self.text_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self.text_frame, command=self.text_output.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_output.config(yscrollcommand=self.scrollbar.set)

        # Make sure rows resize properly
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)  # Allow text widget to expand

        # Redirect stdout to Text widget
        back_button = ttk.Button(frame, text="🠜 Go Back", command=lambda: controller.show_page(ModProjectsPage))
        back_button.config(width=15)  # Set a fixed width
        back_button.grid(row=4, column=0, padx=5, pady=5, sticky="w")
        



# ====================== MAIN APPLICATION START ======================
if __name__ == "__main__":
    root = tk.Tk()
    app = MyApp(root)
    root.mainloop()
