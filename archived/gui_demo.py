import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

class MyGUI:
    def __init__(self):
        
        self.root = tk.Tk()
        self.root.title("ATO Impact Tool")

        self.menubar = tk.Menu(self.root)
        self.filemenu = tk.Menu(self.menubar, tearoff=0)
        self.filemenu.add_command(label="Close",command=self.on_closing)
        self.filemenu.add_separator()
        self.filemenu.add_command(label="Close Without Question",command=exit)

        self.actionmenu = tk.Menu(self.menubar, tearoff=0)
        self.actionmenu.add_command(label="Show Meessage",command=self.show_message)

        self.menubar.add_cascade(menu=self.filemenu, label='File')
        self.menubar.add_cascade(menu=self.actionmenu, label='Action')
        self.root.config(menu=self.menubar)


        self.label = tk.Label(self.root , text="Message", font=('Arial', 18))
        self.label.pack(padx=10, pady=10)

        self.textbox = tk.Text(self.root, height=5,  font=('Arial', 16))
        self.textbox.bind('<KeyPress>', self.shortcut)
        self.textbox.pack(padx=10, pady=10)

        self.check_state = tk.IntVar()

        self.check = tk.Checkbutton(self.root, text='Show Messagebox', font=('Arial', 16), variable=self.check_state)
        self.check.pack(padx=10, pady=10)

        self.button = tk.Button(self.root, text='show message', font=('Arial', 18),command=self.show_message)
        self.button.pack(padx=10, pady=10)

        self.clear_button = tk.Button(self.root, text='Clear', font=('Arial', 18),command=self.clear)
        self.clear_button.pack(padx=10, pady=10)

        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
        self.root.mainloop()


    def show_message(self):
        if(self.check_state.get()) == 0:
            print(self.textbox.get('1.0', tk.END))
        else:
            messagebox.showinfo(title='ALERT!!!', message=self.textbox.get('1.0', tk.END))

    def shortcut(self, event):
        # print(event.keysym)
        # print(event.state)
        if event.state== 12 and event.keysym == 'Return':
            print('help!!')

    def on_closing(self):
        if messagebox.askyesno(title='Quit?', message='Do you really want to quit?'):
            print('Goodbye world')
            self.root.destroy()

    def clear(self):
        self.textbox.delete('1.0', tk.END)



MyGUI()
# root.geometry('800x500')
# root.title('ATO Impact Tool')

# label = tk.Label(root, text='Click a button to begin a process', font=('Arial', 18))
# label.pack(padx=20, pady=20)


# # textbox = tk.Text(root, height=3, font=('Arial', 16))
# # textbox.pack(padx=10)

# scenario_name_entry = tk.Entry(root)
# scenario_name_entry.pack()

# # this can have domains
# facility_type_entry = tk.Entry(root)
# facility_type_entry.pack()

# network_setup_button = tk.Button(root, text='1. Network Setup', font=('Arial', 18))
# network_setup_button.pack(padx=10, pady=10)

# taz_setup_button = tk.Button(root, text='2. TAZ Setup', font=('Arial', 18))
# taz_setup_button.pack(padx=10, pady=10)

# mod_frame = tk.Frame(root)
# mod_frame.columnconfigure(0, weight=1)
# mod_frame.columnconfigure(1, weight=1)
# mod_frame.columnconfigure(2, weight=1)
# mod_frame.columnconfigure(3, weight=1)

# mod_road_button = tk.Button(mod_frame, text='3. Mod Road', font=('Arial', 18))
# mod_road_button.grid(row=0, column=0, sticky=tk.W +tk.E)

# mod_bike_button = tk.Button(mod_frame, text='3. Mod Bike', font=('Arial', 18))
# mod_bike_button.grid(row=0, column=1, sticky=tk.W +tk.E)

# mod_transit_button = tk.Button(mod_frame, text='3. Mod Transit', font=('Arial', 18))
# mod_transit_button.grid(row=0, column=2, sticky=tk.W +tk.E)

# mod_landuse_button = tk.Button(mod_frame, text='3. Mod Land Use', font=('Arial', 18))
# mod_landuse_button.grid(row=0, column=3, sticky=tk.W +tk.E)

# mod_frame.pack(fill='x')

# score_button = tk.Button(root, text='4. Score', font=('Arial', 18))
# score_button.pack(padx=10, pady=10)

