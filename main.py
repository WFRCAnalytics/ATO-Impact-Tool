import tkinter as tk
from tkinter import Menu, filedialog, messagebox
from PIL import Image, ImageTk
import os
import yaml
import subprocess
import threading
import sys
from tkinter import ttk

# Load YAML configuration
def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

config = load_yaml('0_config.yaml')  # Load config

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

                # Read output line-by-line and update the text widget
                for line in iter(process.stdout.readline, ''):
                    sys.stdout.write(line)  # Write directly to redirected stdout
                    sys.stdout.flush()  # Force immediate UI update

                for err in iter(process.stderr.readline, ''):
                    sys.stderr.write(err)  # Write directly to stderr

                process.stdout.close()
                process.stderr.close()
                process.wait()

                messagebox.showinfo("Success", "Script finished successfully!")

            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")
                messagebox.showerror("Error", f"Failed to launch script:\n{e}")

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

# ====================== MAIN APPLICATION CLASS ======================
class MyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ATO Impact Tool")
        self.root.geometry("480x500")
        
        # set the gui style
        style = ttk.Style()
        style.theme_use("clam")  # Change this to "alt", "default", etc.

        # Create menu bar
        menu_bar = Menu(root)
        root.config(menu=menu_bar)

        # File menu
        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Exit", command=root.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        # Settings menu
        setup_menu = Menu(menu_bar, tearoff=0)
        setup_menu.add_command(label="Edit config file", command=self.open_config_file)
        menu_bar.add_cascade(label="Settings", menu=setup_menu)

        # ===================== PAGE CONTAINER =====================
        self.container = tk.Frame(root)
        self.container.pack(fill="both", expand=True)

        # Dictionary to store pages
        self.pages = {}

        # Create pages
        for Page in (MainMenu, NetworkSetupPage, TazSetupPage, ModProjectsPage, ModBikePage, ScoreModsPage):
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
            elif os.name == 'posix':  # macOS & Linux
                subprocess.run(["xdg-open", filepath], check=True)
        except Exception as e:
            print(f"Error opening file: {e}")

# ====================== MAIN MENU CLASS ======================
class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        # Left frame with buttons
        left_frame = tk.Frame(self)
        left_frame.grid(row=0, column=0, sticky="n", padx=10, pady=10)

        # Create buttons
        btn1 = ttk.Button(left_frame, text="1 Network Setup", width=15,  padding=(35, 15),
                         command=lambda: controller.show_page(NetworkSetupPage))
        btn1.grid(row=0, column=0, pady=5)

        btn2 = ttk.Button(left_frame, text="2 TAZ Setup", width=15,  padding=(35, 15),
                         command=lambda: controller.show_page(TazSetupPage))
        btn2.grid(row=1, column=0, pady=5)

        btn3 = ttk.Button(left_frame, text="3 Mod Projects", width=15, padding=(35, 15),
                         command=lambda: controller.show_page(ModProjectsPage))
        btn3.grid(row=2, column=0, pady=5)

        btn4 = ttk.Button(left_frame, text="4 Score Projects", width=15,padding=(35, 15), 
                          command=lambda: controller.show_page(ScoreModsPage))
        btn4.grid(row=3, column=0, pady=5)

        # Right frame for image
        self.right_frame = tk.Frame(self)
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
        
        frame = ttk.LabelFrame(self, text='1 Network Setup', padding=(10, 10))
        frame.pack(padx=10, pady=10, fill="both", expand="yes")

        desc_label = ttk.Label(frame, text="This script prepares the Network Dataset datasets used for all ATO calculations.")
        desc_label.grid(row=0, column=0, columnspan=2, pady=5)

        back_button = ttk.Button(frame, text="🠜 Go Back", command=lambda: controller.show_page(MainMenu))
        run_button = ttk.Button(frame, text="Run Script!", command=lambda: self.launch_script(config['network_setup']))

        back_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        run_button.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Output text box
        self.text_frame = tk.Frame(frame)
        self.text_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)

        self.text_output = tk.Text(self.text_frame, wrap="word", height=10, width=50)
        self.text_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = ttk.Scrollbar(self.text_frame, command=self.text_output.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_output.config(yscrollcommand=self.scrollbar.set)

        # Make sure rows resize properly
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)  # Allow text widget to expand

        # Redirect stdout to this page's text widget
        self.setup_output_widget(self.text_output)

# ====================== TAZ SETUP PAGE CLASS ======================
class TazSetupPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        frame = ttk.LabelFrame(self, text='2 TAZ Setup',  padding=(10, 10))
        frame.pack(padx=10, pady=10, fill="both", expand="yes")

        desc_label = ttk.Label(frame, text="This script prepares the TAZ dataset used for all ATO calculations.")
        desc_label.grid(row=0, column=0, columnspan=2, pady=5)

        back_button = ttk.Button(frame, text="🠜 Go Back", command=lambda: controller.show_page(MainMenu))
        run_button = ttk.Button(frame, text="Run Script 🠞", command=lambda: self.launch_script(config['taz_setup']))

        back_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        run_button.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # Output text box
        self.text_frame = tk.Frame(frame)
        self.text_frame.grid(row=2, column=0, columnspan=2,  sticky="nsew", padx=10, pady=10)

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
        
        
        
        # back_button.pack()
        # continue_button.pack()
        # self.text_frame.pack()

    

# ====================== SCORE MODS PAGE CLASS ======================
class ScoreModsPage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        frame = ttk.LabelFrame(self, text='4 Score Mods',  padding=(10, 10))
        frame.pack(padx=10, pady=10, fill="both", expand="yes")

        score_desc = '''This script scores the configured scenarios.\n\nAny unscored scenarios will be scored.\n\nTo re-score a scenario, open its corresponding file \ngeodatabaseand delete its "scores" and "scores_summary" table. '''
        desc_label = ttk.Label(frame, text=score_desc)
        desc_label.grid(row=0, column=0, columnspan=2, pady=5)

        back_button = ttk.Button(frame, text="🠜 Go Back", command=lambda: controller.show_page(MainMenu))
        run_button = ttk.Button(frame, text="Run Script 🠞", command=lambda: self.launch_script(config['taz_setup']))

        back_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        run_button.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # Output text box
        self.text_frame = tk.Frame(frame)
        self.text_frame.grid(row=2, column=0, columnspan=2,  sticky="nsew", padx=10, pady=10)

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
        
        
#======================== MOD PROJECTS PAGE ==========================

class ModProjectsPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        frame = ttk.LabelFrame(self, text='3 Mod Projects',  padding=(10, 10))
        frame.pack(padx=10, pady=10, fill="both", expand="yes")

        mod_desc = '''Select which type of modification you wish to add (Drive, Transit, Bike, Land Use)\n\nAll modifications will be scored at once in the final script'''
        desc_label = ttk.Label(frame, text=mod_desc)
        desc_label.grid(row=0, column=0, columnspan=2, pady=5)

        # # frame with buttons
        # frame = tk.Frame(self)
        # frame.grid(row=0, column=0, sticky="n", padx=10, pady=10)

        # Create buttons
        btn1 = ttk.Button(frame, text="Mod Drive", width=15,  padding=(35, 15),
                         command=lambda: controller.show_page(NetworkSetupPage))
        btn1.grid(row=1, column=0, pady=5)

        btn2 = ttk.Button(frame, text="Mod Transit", width=15,  padding=(35, 15),
                         command=lambda: controller.show_page(TazSetupPage))
        btn2.grid(row=1, column=1, pady=5)

        btn3 = ttk.Button(frame, text="Mod Bike", width=15, padding=(35, 15),
                         command=lambda: controller.show_page(ModBikePage)) 
        btn3.grid(row=2, column=0, pady=5)

        btn4 = ttk.Button(frame, text="Mod Land Use", width=15,padding=(35, 15), 
                          command=lambda: controller.show_page(ScoreModsPage))
        btn4.grid(row=2, column=1, pady=5)

        back_button = ttk.Button(frame, text="🠜 Go Back", width=7,padding=(20, 15), command=lambda: controller.show_page(MainMenu))

        back_button.grid(row=3, column=0,columnspan=2,  padx=5, pady=5, sticky="ew")

# ====================== SCORE MODS PAGE CLASS ======================
class ModBikePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        
        frame = ttk.LabelFrame(self, text='3 Mod Bikes',  padding=(10, 10))
        frame.pack(padx=10, pady=10, fill="both", expand="yes")

        score_desc = '''Modify a copy of our baseline NetworkDataset with the candidate for improvement for bicycle projects.\n\nSet the scenario name and improvement type in the cell below before running the script.\n\nRun the script, ArcGIS Pro will launch.\n\nIMPORTANT: When you are done making your edits, leave the edited feature selected.\n\nRemember to save your edits and the project when you are finished'''
        desc_label = ttk.Label(frame, text=score_desc)
        desc_label.grid(row=0, column=0, columnspan=2, pady=5)

        back_button = ttk.Button(frame, text="🠜 Go Back", command=lambda: controller.show_page(MainMenu))
        run_button = ttk.Button(frame, text="Run Script 🠞", command=lambda: self.launch_script(config['mod_bike']))

        back_button.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        run_button.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # Output text box
        self.text_frame = tk.Frame(frame)
        self.text_frame.grid(row=2, column=0, columnspan=2,  sticky="nsew", padx=10, pady=10)

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
        




# ====================== MAIN APPLICATION START ======================
if __name__ == "__main__":
    root = tk.Tk()
    app = MyApp(root)
    root.mainloop()
