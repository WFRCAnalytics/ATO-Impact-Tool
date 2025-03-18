import tkinter as tk

class MyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Layout Tkinter App")
        self.root.geometry("500x400")

        # Create a container frame that will hold all the pages
        self.container = tk.Frame(root)
        self.container.pack(fill="both", expand=True)

        # Dictionary to store pages
        self.pages = {}

        # Create pages
        for Page in (MainMenu, SecondPage):
            page_instance = Page(self.container, self)
            self.pages[Page] = page_instance
            page_instance.grid(row=0, column=0, sticky="nsew")

        self.show_page(MainMenu)  # Show the main menu first

    def show_page(self, page):
        """Raises the selected page to the front."""
        self.pages[page].tkraise()

# ========== Page 1: Main Menu ==========
class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        label = tk.Label(self, text="Main Menu", font=("Arial", 18))
        label.pack(pady=20)

        switch_button = tk.Button(self, text="Go to Second Page",
                                  command=lambda: controller.show_page(SecondPage))
        switch_button.pack()

# ========== Page 2: Second Layout ==========
class SecondPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        label = tk.Label(self, text="Second Page", font=("Arial", 18))
        label.pack(pady=20)

        back_button = tk.Button(self, text="Back to Main Menu",
                                command=lambda: controller.show_page(MainMenu))
        back_button.pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = MyApp(root)
    root.mainloop()