import tkinter as tk
from tkinter import Menu, filedialog, messagebox
from PIL import Image, ImageTk
import os
import yaml
import subprocess
import threading
import sys

def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


# source files and fields - update this before running!
config = load_yaml('0_config.yaml')
            
# Run the script with pythonw.exe to avoid the command window appearing (Windows only)

class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.insert(tk.END, string)  # Insert new text at the end
        self.text_widget.see(tk.END)  # Auto-scroll to the bottom
        self.text_widget.update_idletasks()  # Ensure UI updates immediately

    def flush(self):
        pass  # Not needed


class MyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ATO Impact Tool")
        self.root.geometry("430x500")

        # Create menu bar
        menu_bar = Menu(root)
        root.config(menu=menu_bar)

        # File menu
        file_menu = Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Exit", command=root.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        # Setup menu
        setup_menu = Menu(menu_bar, tearoff=0)
        setup_menu.add_command(label="Settings", command=self.open_config_file)
        setup_menu.add_command(label="Delete All Scenarios", command=None)
        menu_bar.add_cascade(label="Setup", menu=setup_menu)
       

        # Main frame with grid layout
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left frame with buttons in a grid
        left_frame = tk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="n")

        # Create buttons one by one
        btn1 = tk.Button(left_frame, text="1 Network Setup", font=('Arial', 16), width=15, command=lambda: self.launch_script(config['network_setup']))
        btn1.grid(row=0, column=0, pady=5, padx=10)

        btn2 = tk.Button(left_frame, text="2 TAZ Setup", font=('Arial', 16), width=15, command=lambda: self.launch_script(config['taz_setup']))
        btn2.grid(row=1, column=0, pady=5, padx=10)

        # go to mod projects window
        btn3 = tk.Button(left_frame, text="3 Mod Projects", font=('Arial', 16), width=15, command=None)
        btn3.grid(row=2, column=0, pady=5, padx=10)

        btn4 = tk.Button(left_frame, text="4 Score Projects", font=('Arial', 16), width=15, command=lambda: self.launch_script(config['4_score']))
        btn4.grid(row=3, column=0, pady=5, padx=10)

        # Right frame for the image
        self.right_frame = tk.Frame(main_frame)
        self.right_frame.grid(row=0, column=1, padx=20)

        # Load image
        self.load_image("ato_graphic.png")  # Change to the actual image path

        # Create a label to display output
        # Create a Text widget with a Scrollbar
        self.text_frame = tk.Frame(root)
        self.text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.text_output = tk.Text(self.text_frame, wrap="word", height=15)
        self.text_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = tk.Scrollbar(self.text_frame, command=self.text_output.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_output.config(yscrollcommand=self.scrollbar.set)
        # Redirect stdout to label
        sys.stdout = RedirectText(self.text_output)

        # # Bottom frame
        # self.bottom_frame = tk.Frame(main_frame)
        # self.bottom_frame.grid(row=1, column=0, padx=20)

        # self.description = tk.Label(self.bottom_frame, text='blah blah blah')
        # self.value = tk.StringVar()

        # self.output.label = tk.Label(self.bottom_frame, text=self.value)

    def open_file(self):
        file_path = filedialog.askopenfilename(title="Open File")
        if file_path:
            self.load_image(file_path)

    def show_settings(self):
        messagebox.showinfo("Settings", "Settings menu clicked.")

    def load_image(self, image_path):
        try:
            # Open and resize the image
            image = Image.open(image_path)
            w, h = 250, 500  # Width and height
            pct = 0.6 # Resize percentage
            image = image.resize((int(w * pct), int(h * pct)))  # No anti-aliasing

            self.img = ImageTk.PhotoImage(image)

            # Clear previous widgets in the frame
            for widget in self.right_frame.winfo_children():
                widget.destroy()

            # Create a Label with a border to display the image
            label = tk.Label(self.right_frame, image=self.img, bd=2, relief="solid")  # Border added
            label.pack(pady=10, padx=10)

        except Exception as e:
            print(f"Error loading image: {e}")


    def open_config_file(self):
        filepath = '0_config.yaml'
        if filepath:
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(filepath)
                elif os.name == 'posix':  # macOS & Linux
                    subprocess.run(["xdg-open", filepath], check=True)
            except Exception as e:
                print(f"Error opening file: {e}")
    
    def launch_script(self, script_path):
        def run():
            try:
                pythonw_path = config['pythonw']
                process = subprocess.Popen(
                    [pythonw_path, '-u', script_path], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,  # Ensures text output
                    bufsize=1  # Line buffering for real-time updates
                )

                # Read output line-by-line and update the label
                for line in process.stdout:
                    print(line.strip())  # Redirects output to the tkinter label

                process.stdout.close()
                process.wait()  # Wait for the process to complete
                
                messagebox.showinfo("Success", "Script finished successfully!")

            except Exception as e:
                print(f"Error: {e}")
                messagebox.showerror("Error", f"Failed to launch script:\n{e}")

        # Run in a separate thread to keep GUI responsive
        thread = threading.Thread(target=run, daemon=True)
        thread.start()


    

if __name__ == "__main__":
    root = tk.Tk()
    app = MyApp(root)
    root.mainloop()