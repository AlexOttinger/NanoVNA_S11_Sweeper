import tkinter as tk
import customtkinter as ctk
import pickle
import os
import threading
from PIL import Image, ImageTk
from VNA_Functions import * # provides functions for handling the VNA Hardware per Commands given
from VNA_Commands import *  # provides sequencing logic for main GUI operation

endless_on = False
single_on = False
multiple_on = False
stype = 0
flag = 0
flag2 = 0
save = 0
final = 0
linear = 1


def on_closing():
    print("Closing the window...")
    gui.destroy()
    gui.update_idletasks()
    gui.quit()

    

class Sweeper(ctk.CTk):
    def __init__(self):
        ctk.CTk.__init__(self)
        self.single_state = False
        self.multiple_state = False
        self.endless_state = False # creates toggle for continuous sweeps
        self.ion = False
        self.save_state = False
        self.saved = False
        self.scans = 3   # default number of sweeps is set to 3 sweeps
        self.timed = 0.01 # default time delay between sweeps is set to 0.1 seconds
        self.line_state = False
        self.save_class_state = False
        self.single_scan = 0
        self.save_count = 0
        
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure((1,2), weight=1)
        
        ctk.set_appearance_mode("System")   # Modes: system (default), light, or dark
        ctk.set_default_color_theme("blue") # Themes: blue (default), dark-blue, or green

        self.title("NanoVNA S11 Sweeper") # Titles the Application Window
        self.geometry("800x575") # defines size of window

        self.frame = ctk.CTkFrame(master=self)
        self.frame.pack(pady=20, padx=25, fill="both", expand=True)
        
        self.label = ctk.CTkLabel(self.frame, text="NanoVNA S11 Sweeper", font=("Roboto", 28))
        self.label.grid(row=0, column=0, columnspan=3, pady=12, padx=10, sticky="ew")
        
        
        ### Antenna Sweep Parameters ###
        self.antenna = None
        global new_class
        use_new_antenna, new_class = self.open_new()
        if use_new_antenna == 1:
            try:
                self.small_dipole = ctk.CTkRadioButton(self.frame, text=f"{new_class[0][4]}", command=self.new_small_ant)
            
                if new_class[1][4] == None:
                    self.large_dipole = ctk.CTkRadioButton(self.frame, text="Default Large Antenna", command=self.large_ant)
                else:
                    self.large_dipole = ctk.CTkRadioButton(self.frame, text=f"{new_class[1][4]}", command=self.new_large_ant)
            except:
                if new_class[0][4] == None:
                    self.small_dipole = ctk.CTkRadioButton(self.frame, text="Default Small Antenna", command=self.small_ant)
                else:
                    self.large_dipole = ctk.CTkRadioButton(self.frame, text="Default Large Antenna", command=self.large_ant)
                
        elif use_new_antenna == 0:
            self.small_dipole = ctk.CTkRadioButton(self.frame, text="Default Small Antenna", command=self.small_ant)
            self.large_dipole = ctk.CTkRadioButton(self.frame, text="Default Large Antenna", command=self.large_ant)
            
        self.small_dipole.grid(row=1, column=0, pady=12, padx=10, sticky="ew")
        self.large_dipole.grid(row=2, column=0, pady=12, padx=10, sticky="ew")
        
        self.new_antenna = ctk.CTkRadioButton(self.frame, text="Custom Sweep Parameters", command=self.new_ant)
        self.new_antenna.grid(row=3, column=0, columnspan=1, pady=12, padx=10, sticky="ew")
        
        self.start = ctk.CTkEntry(self.frame, placeholder_text="Start Frequency [G/M/kHz]")
        self.start.grid(row=1, column=1, columnspan=2, pady=5, padx=10, sticky="ew")
        
        self.stop = ctk.CTkEntry(self.frame, placeholder_text="Stop Frequency [G/M/kHz]")
        self.stop.grid(row=2, column=1, columnspan=2, pady=5, padx=10, sticky="ew")
        
        self.points = ctk.CTkEntry(self.frame, placeholder_text="Number of Sweep Points")
        self.points.grid(row=3, column=1, columnspan=2, pady=5, padx=10, sticky="ew")
        
        
        ### Sweep style ###
        self.single_switch = ctk.CTkSwitch(self.frame, text="Single Sweep [OFF]", command=self.single)
        self.single_switch.grid(row=5, column=0, pady=12, padx=10, sticky="ew")
        
        self.multiple_switch = ctk.CTkSwitch(self.frame, text="Multiple Sweeps [OFF]", command=self.multiple)
        self.multiple_switch.grid(row=6, column=0, pady=12, padx=10, sticky="ew")
        
        self.scan_number = ctk.CTkEntry(self.frame, placeholder_text="Number of Sweeps")
        self.scan_number.grid(row=6, column=1, columnspan=2, pady=5, padx=10, sticky="ew")
        
        self.delay = ctk.CTkEntry(self.frame, placeholder_text="Sweep Time Delay")
        self.delay.grid(row=5, column=1, columnspan=2, pady=5, padx=10, sticky="ew")
        
        self.endless_switch = ctk.CTkSwitch(self.frame, text="Continuous Sweep [OFF]", command=self.endless)
        self.endless_switch.grid(row=7, column=0, pady=12, padx=10, sticky="ew")
        
        
        ### Save Options Menus ###
        # Antenna Sweep Parameters Class Save
        value, names, classes = self.load_antenna_class()
        self.sweepcombo = ctk.CTkOptionMenu(self.frame, values=value, command=self.input_sweep_param)
        self.sweepcombo.grid(row=4, column=0, columnspan=3, pady=12, padx=10, sticky="ew")
        
        # File Save Settings
        self.combo = ctk.CTkOptionMenu(self.frame, values=["Default: Do Not Save          ", "Save All to One File            ", "Save All to Separate Files"], command=self.save)
        self.combo.grid(row=7, column=1, columnspan=2, pady=12, padx=10, sticky="ew")
        
        
        ### Sweep Button, File Name, and Progress Bar ###
        self.filename = ctk.CTkEntry(self.frame, placeholder_text="Filename Entry")
        self.filename.grid(row=8, column=0, columnspan=3, pady=12, padx=10, sticky="ew")
        
        self.sweeper = ctk.CTkButton(self.frame, text="Sweep", command=self.sweep_control)
        self.sweeper.grid(row=9, column=0, columnspan=3, pady=12, padx=10, sticky="ew")
        
        self.bar = ctk.CTkProgressBar(self.frame, orientation="vertical", mode="determinate")
        self.bar.grid(row=0, column=3, rowspan=10, pady=12, padx=10, sticky="nsew")
        self.bar.set(100)
        
        
        ### S11 Plotter Settings, Help, and Customization ###
        self.label2 = ctk.CTkLabel(self.frame, text="S11 Plot Settings", font=("Roboto", 28))
        self.label2.grid(row=0, column=4, columnspan=1, pady=12, padx=10, sticky="ew")
        
        self.combo2 = ctk.CTkOptionMenu(self.frame, values=["Show Final Result", "Show Scan Averaging", "Do Not Show Plot"], command=self.show)
        self.combo2.grid(row=1, column=4, columnspan=1, pady=12, padx=10, sticky="nsew")
        
        self.scatter = ctk.CTkRadioButton(self.frame, text="Display Plot as Scatter Plot", command=self.scatter)
        self.scatter.grid(row=2, column=4, columnspan=1, pady=12, padx=10, sticky="ew")
        
        self.line = ctk.CTkRadioButton(self.frame, text="Display Plot as Line Plot", command=self.linear)
        self.line.grid(row=3, column=4, columnspan=1, pady=12, padx=10, sticky="ew")
        self.line.select()
        
        self.label3 = ctk.CTkLabel(self.frame, text="Display Customization", font=("Roboto", 28))
        self.label3.grid(row=4, column=4, columnspan=1, pady=12, padx=10, sticky="ew")
        
        self.custom_menu = ctk.CTkOptionMenu(self.frame, values=["System", "Light", "Dark"], command=self.change_appearance)
        self.custom_menu.grid(row=5, column=4, columnspan=1, pady=12, padx=10, sticky="ew")
        
        self.help = ctk.CTkButton(self.frame, text="Help/About", command=self.help_popup)
        self.help.grid(row=6, column=4, columnspan=1, pady=12, padx=10, sticky="ew")
        
        ### Project Logos ###
        image_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "images")
        self.jayhawk = ctk.CTkImage(Image.open(os.path.join(image_path, "jayhawk_cresis_clear.png")), size=(200,67))
        self.image = ctk.CTkLabel(self.frame, image=self.jayhawk, text="")
        self.image.grid(row=8, column=4, rowspan=2, pady=0, padx=0)
        
    # GUI Control Handlers
    def small_ant(self):
        self.antenna = small_vhf_dipole(1)
        print("Antenna Class Selected: Default Small Antenna")
        self.small_dipole.configure(border_width_checked=6, fg_color=("#3B8ED0", "#1F6AA5"))
        self.large_dipole.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
        self.new_antenna.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
        self.reset_color(1)
    
    def new_small_ant(self):
        self.antenna = saved_new_antenna(new_class[0][0], new_class[0][1], new_class[0][2], new_class[0][3])
        print(f"Antenna Class Selected: {new_class[0][4]}")
        self.small_dipole.configure(border_width_checked=6, fg_color=("#3B8ED0", "#1F6AA5"))
        self.large_dipole.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
        self.new_antenna.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
        self.reset_color(1)

    def large_ant(self):
        self.antenna = large_dipole(2)
        print("Antenna Class Selected: Default Large Antenna")
        self.small_dipole.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
        self.large_dipole.configure(border_width_checked=6, fg_color=("#3B8ED0", "#1F6AA5"))
        self.new_antenna.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
        self.reset_color(1)
    
    def new_large_ant(self):
        self.antenna = saved_new_antenna(new_class[1][0], new_class[1][1], new_class[1][2], new_class[1][3])
        print(f"Antenna Class Selected: {new_class[1][4]}")
        self.small_dipole.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
        self.large_dipole.configure(border_width_checked=6, fg_color=("#3B8ED0", "#1F6AA5"))
        self.new_antenna.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
        self.reset_color(1)
    
    def new_ant(self):
        self.small_dipole.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
        self.large_dipole.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
        self.new_antenna.configure(border_width_checked=6, fg_color=("#3B8ED0", "#1F6AA5"))
        start_entry = self.start.get()
        stop_entry = self.stop.get()
        points_entry = self.points.get()
        global flag
        if start_entry == "" and stop_entry == "" and points_entry == "":
            print("Please Enter Sweep Parameters First")
            flag = 1
            self.start.configure(fg_color=("#54EFFF","#54EFFF"))
            self.stop.configure(fg_color=("#54EFFF","#54EFFF"))
            self.points.configure(fg_color=("#54EFFF","#54EFFF"))
        elif start_entry == "":
            print("Please Enter Start Frequency")
            flag = 1
            self.start.configure(fg_color=("#54EFFF","#54EFFF"))
        elif stop_entry == "":
            print("Please Enter Stop Frequency")
            flag = 1
            self.stop.configure(fg_color=("#54EFFF","#54EFFF"))
        elif points_entry == "":
            print("Please Enter Number of Sweep Points")
            flag = 1
            self.points.configure(fg_color=("#54EFFF","#54EFFF"))
        else:
            flag = 0
            self.antenna = new_antenna(start_entry, stop_entry, points_entry, 3)
            
    def open_new(self):
        try:
            with open("Saved_Antenna_Classes", 'rb') as file:
                antenna_class = pickle.load(file)
                if antenna_class != []:
                    global use_new_antenna
                    use_new_antenna = 1
                    return use_new_antenna, antenna_class
                else:
                    return 0,0
        except:
            return 0,0
            
    ## Logic for Antenna Class Dropdown Menu and Popup ##        
    def save_antenna_class(self, new_antenna, old_antennas, pop):
            antenna_list = old_antenna_classes + [new_antenna] # saves antenna classes in a list
            print("Saved New Antenna Class:", [new_antenna])
            with open("Saved_Antenna_Classes", 'wb') as file:
                pickle.dump(antenna_list, file)
            print("New Antenna Selected:", new_antenna[4])
            self.antenna = saved_new_antenna(new_antenna[0], new_antenna[1], new_antenna[2], new_antenna[3])
            self.small_dipole.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
            self.large_dipole.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
            self.new_antenna.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
            self.reset_color(1)
            try:
                pop.destroy()
            except:
                pass
    
    def load_antenna_class(self):
        try:
            with open("Saved_Antenna_Classes", 'rb') as file:
                antenna_class = pickle.load(file)
                global old_antenna_classes
                old_antenna_classes = antenna_class
                if antenna_class != []:
                    print("Opened:", antenna_class)
            pass
        except IOError:
            antenna_list = []
            with open("Saved_Antenna_Classes", 'wb') as file: # saves a temporary file using default small and large antennas
                pickle.dump(antenna_list, file)
            with open("Saved_Antenna_Classes", 'rb') as file:
                antenna_class = pickle.load(file)
                old_antenna_classes = antenna_class
                print(antenna_class)
                
        global antenna_names
        antenna_names = []; 
        def flatten_list(lst, values): # returns only the string values to values list for dropdown menu
            for i in lst:
                if isinstance(i, list):
                    flatten_list(i, values)
                elif isinstance(i, str):
                    antenna_names.append(i)
                    values.append(i)
                    
        global values
        values=["Default: Custom Antenna Class Not Selected", "Save and Use New Antenna Class"]
        flatten_list(antenna_class, values)
        return values, antenna_names, antenna_class
    
    def input_sweep_param(self, config: str): # Operation for Sweep Parameters Dropdown menu
        if config == 'Save and Use New Antenna Class':
            print("Save New Antenna Class")
            self.show_popup() # opens window for class name entry and saves in binary (writes to pickle)
            
        elif any(values[i] == config for i in range(2, len(values))): # Checks for selected Antenna Class Name
            print("Antenna Class Selected:", config)
            indices = [i for i, x in enumerate(values) if x == config]
            indices = indices[0] - 2
            self.antenna = saved_new_antenna(old_antenna_classes[indices][0], old_antenna_classes[indices][1], old_antenna_classes[indices][2], old_antenna_classes[indices][3])
            # sets sweep parameters for sweeper control
        else:
            print("No Antenna Class Selected")

    def show_popup(self):
        pop = tk.Toplevel(self)
        pop.configure(background='light blue')
        pop.title("Save Antenna Class")
        pop.geometry("300x350")
        pop.focus_set()
        
        label = ctk.CTkLabel(pop, text="Please Input Required Entries:", text_color=("#000000", "#000000"))
        label.pack(pady=12)
        
        
        name = ctk.CTkEntry(pop, placeholder_text="Antenna Class Name:")
        name.pack(pady=12)
        
        start = ctk.CTkEntry(pop, placeholder_text="Start Frequency [G/M/kHz]")
        start.pack(pady=12)
        
        stop = ctk.CTkEntry(pop, placeholder_text="Stop Frequency [G/M/kHz]")
        stop.pack(pady=12)
        
        points = ctk.CTkEntry(pop, placeholder_text="Number of Sweep Points")
        points.pack(pady=12)
                 
        save = ctk.CTkButton(pop, text="Save", command=lambda: self.check_entry(name, start, stop, points, antenna_names, pop))
        save.pack(pady=12)
    
    def check_entry(self, name, start, stop, points, old_antennas, pop):
            if name.get() != "" and start.get() != "" and stop.get() != "" and points.get() !="":
                new_antenna = [int(si_prefix(start.get())), int(si_prefix(stop.get())), int(points.get()), 3, name.get()]
                print(new_antenna)
                self.save_antenna_class(new_antenna, old_antennas, pop) 
                
            elif name.get() == "" and start.get() == "" and stop.get() == "" and points.get() == "":
                name.configure(fg_color=("#54EFFF","#54EFFF"))
                start.configure(fg_color=("#54EFFF","#54EFFF"))
                stop.configure(fg_color=("#54EFFF","#54EFFF"))
                points.configure(fg_color=("#54EFFF","#54EFFF"))
                print("Please Fill Entries")
            elif name.get() == "":
                name.configure(fg_color=("#54EFFF","#54EFFF"))
            elif start.get() == "":
                start.configure(fg_color=("#54EFFF","#54EFFF"))
            elif stop.get() == "":
                stop.configure(fg_color=("#54EFFF","#54EFFF"))
            elif points.get() == "":
                points.configure(fg_color=("#54EFFF","#54EFFF"))
    
    def help_popup(self):
        pop = tk.Toplevel(self)
        pop.configure(background='light blue')
        pop.title("About VNA S11 Sweeper")
        pop.geometry("1350x750")
        
        label = ctk.CTkLabel(pop, text="About VNA S11 Sweeper", font=("Roboto", 28), text_color=("#000000", "#000000"))
        label.pack(pady=12, padx=10)
        
        textbox = ctk.CTkTextbox(pop, width=1300, height=700)
        textbox.pack(pady=12, padx=10, expand= True, fill="both")
        textbox.insert("0.0", "Input Sweep Parameters:\n" + "There are many ways to input or select desired sweep parameters: (Start/Stop) Frequencies and number of Sweep Points:\n" + "1. Populate sweep parameters entries and select 'Custom Sweep Parameters' radio button.\n" + "2. Select either 'Default Small Antenna' or 'Default Large Antenna' placeholder radio buttons.\n" + "3. Click the dropdown menu and select the 'Save and Use New Antenna Class'. This will generate a popup that will allow you to input sweep parameters and a name for the class.\n"+ "Using this method, current sweep parameters will be logged as its own class and will be available in the dropdown menu.\n"+ "Additionally, the default radio buttons will be replaced by the first two classes that you may save. You can delete the generated binary file called 'Saved_Antenna_Classes' to reset the displayed classes.\n" + "Doing this will unfortunately delete all of your custom classes. Therefore, it is advisable to access every subquential custom class in the dropdown menu.\n\n" + "Selecting Sweep Mode Switches:\n" + "There are three different styles of sweeping (Single, Multiple, Continuous) and only one style can be selected per sweep.\n" + "1. Single returns only one sweep.\n" + "2. Multiple requires you to set the number of sweeps you would like to scan using the entry to the right labeled by 'Number of Sweeps'.\n" + "3. Continuous will sweep endlessly until the popup button is pressed or the GUI time duration is given (Appears when 'Do Not Show Plot' is chosen).\n" + "*Do not exit the figure window or main GUI while sweeping as this will prevent the program from stopping. If this error occurs, use task manager to end the program.\n" + "*Additionally, it is advisable to set a desired time delay between plots for continuous mode or multiple mode using the 'Sweep Time Delay' entry. The default time delay is 0.1 seconds.\n\n"+"Saving File and Sweep:\n"+"Right of the continuous sweep mode switch is a dropdown menu for saving data to file. The options are:\n"+ "1. 'Default: Do Not Save' which will prevent the program from saving to file.\n" + "2. 'Save All to One File' will save every scan to a single file with 3 line gaps between sweeps. Each scan will be labeled with the time and is numbered.\n" + "3. 'Save All to Separate Files' will save consecutive scans to numbered files retaining the given filename.\n" + "*You can set the file's name using the entry below the dropdown menu.\n" + "Finally, once the sweep mode switch is selected and the sweep parameters are set, you can press the 'Sweep' button at the bottom to perform the desired S11 operation.\n\n" + "S11 Plot Settings:\n"+"Before Sweeping, the plotting style can be adjusted using the dropdown menu and radio buttons towards the top-right side of the program.\n"+"The dropdown menu options are as followed:\n"+"1. 'Show Final Result' will display corrected data from the averaging algorithm. This data is what is saved to file when using the file save widgets.\n"+"2. 'Show Scan Averaging' will display the two additional scans that operate in the averaging algorithm.\n"+ "The averaging algorithm ensures that sweeps return the desired number of sweep points and that there are no discontinuities or gaps present due to the VNA FIFO buffer. This option does not effect how data is saved.\n"+"3. 'Do Not Show Plot' will not show the plot by not processing the plotting functions. It is advised to use it in cases to decrease processing power for only saving to file.\n" + "Display Plot Radio Buttons:\n" +"1. 'Display Plot as Scatter Plot' will simply change the plotting style to be scattered. This is toggled against the linear plot style.\n" + "2. 'Display Plot as Line Plot' will simply change the plotting style to a line graph. This is toggled against the scattered plot style.\n\n" + "Display Customization:\n" + "Provides a dropdown menu with options to change the window theme to either your system's windows theme, a light theme, or a dark theme.")
        
    ## Logic for Switch Sweep Types ## 
    def single(self):
        global single_on
        self.single_state = not self.single_state
        if self.single_state:
            self.single_switch.configure(text="Single Sweep [ON]")
            single_on = True
        else:
            self.single_switch.configure(text="Single Sweep [OFF]")
            single_on = False
        
    def multiple(self):
        global flag2
        flag2 = 0
        global scans
        scans = self.scan_number.get()
        if scans == "":
            print("Please Enter Number of Sweeps")
            self.scan_number.configure(fg_color=("#54EFFF","#54EFFF"))
            flag2 = 1
        else:
            scans = int(scans)
            print(scans)
            
        global multiple_on
        self.multiple_state = not self.multiple_state
        if self.multiple_state:
            self.multiple_switch.configure(text="Multiple Sweep [ON]")
            multiple_on = True
        else:
            self.multiple_switch.configure(text="Multiple Sweep [OFF]")
            self.scan_number.configure(fg_color=("#f9f9fa","#343638"))
            multiple_on = False
            
    def multiple_check(self):
        global scans
        scans = self.scan_number.get()
        if scans == "" and self.multiple_state is True:
            self.scan_number.configure(fg_color=("#54EFFF","#54EFFF"))
            global flag2
            flag2 = 1
        elif scans != "" and self.multiple_state is True:
            scans = int(scans)
            if scans <= 10:
                self.ion = False
            else:
                self.ion = True
    
    def endless(self):
        global endless_on
        self.endless_state = not self.endless_state
        if self.endless_state:
            self.endless_switch.configure(text="Continuous Sweep [ON]")
            self.ion = 1
            endless_on = True
        else:
            self.endless_switch.configure(text="Continuous Sweep [OFF]")
            endless_on = False
            
    ## Logic for Saving Sweeps to File ##
    def save_name(self):
        global name
        name = self.filename.get()
        
    def save_type(self):
        global stype
        self.save_state = not self.save_state
        if self.save_state:
            stype = 1
        else:
            stype = 0
    
    def save(self, save_style: str):
        global save # Toggles whether the data is saved at all
        global stype # Toggles whether the data is saved to one file or every file
        
        if save_style == "Save All to One File            ":
            stype = 1
            save = 1
        elif save_style == "Save All to Separate Files":
            stype = 0
            save = 1
        elif save_style == "Default: Do Not Save          ": # Default is a placeholder case that does not save
            stype = 0
            save = 0
            
    ## Logic for Plotting Style and Customization ##
    def show(self, style: str): #"Show Final Result", "Show Scan Averaging", "Do Not Show Scan"
        global final
        if style == "Show Final Result":
            final = 0 # does not display averaging
        elif style == "Do Not Show Plot":
            final = 2 # does not display any plot
        else:
            final = 1 # displays averaging
    
    def scatter(self):
        self.scatter.configure(border_width_checked=6, fg_color=("#3B8ED0", "#1F6AA5"))
        self.line.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
        global linear
        linear = 0
    def linear(self):
        self.scatter.configure(border_width_checked=3, fg_color=("#3E454A", "#949A9F"))
        self.line.configure(border_width_checked=6, fg_color=("#3B8ED0", "#1F6AA5"))
        global linear
        self.line_state = not self.line_state
        if self.line_state:
            linear = 1
        else:
            linear = 0
            
    def change_appearance(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)
        

    ## Ensures Entry Components are entered ##
    def flag_check(self):
        global flag
        global flag2
        if flag == 1:
            start_entry = self.start.get()
            stop_entry = self.stop.get()
            points_entry = self.points.get()
            if start_entry != "" and stop_entry != "" and points_entry != "":
                self.antenna = new_antenna(start_entry, stop_entry, points_entry, 3)
        
        if self.antenna is None:
            print("Error: Antenna class selection not provided.")
            return True
                
        switches_state = [self.single_state, self.multiple_state, self.endless_state]
        number_on = sum(switches_state)
        if number_on >= 2:
            print("Error: More than one sweep type selected. Please choose one sweep type.")
            return True

        if flag2 == 1:
            if self.scan_number.get() == "":
                print("Error: Please input desired number of scans to sweep.")
                self.scan_number.configure(fg_color=("#54EFFF","#54EFFF"))
                return True
            else:
                self.scans = int(self.scan_number.get())
    
    ## Logic to run/cease Endless Sweep##
    def close_endless(self): # Pop up for when plot is displayed
        pop = tk.Toplevel(self)
        pop.configure(background='light blue')
        pop.title("Endless Sweeper Control")
        pop.geometry("300x150")
        pop.focus_set()
        
        pop.label = ctk.CTkLabel(pop, text="Press to End Continuous Sweep", text_color=("#000000", "#000000"))
        pop.label.pack(pady=12)
        
        pop.exit = ctk.CTkButton(pop, text="Exit", command=lambda: self.exit_endless_sweep(pop))
        pop.exit.pack(pady=12)
        
    
    def exit_endless_sweep(self, pop):
        print("Closing...")
        pop.destroy()
        global off
        off = True;
        

    def exit_endless(self, sw): # pop up for when plot is not displayed
        pop = tk.Toplevel(self) 
        pop.configure(background='light blue')
        pop.title("Time Loop Control")
        pop.geometry("300x150")
        
        label = ctk.CTkLabel(pop, text="Please input desired duration to sweep in minutes:", text_color=("#000000", "#000000"))
        label.grid(row=1, pady=12, padx=10, sticky="ew")
        
        entry = ctk.CTkEntry(pop, placeholder_text="Time duration in minutes:")
        entry.grid(row=2, pady=12, padx=10, sticky="ew")
        
        button = ctk.CTkButton(pop, text="Start Loop", command=lambda: self.toggle_loop(sw, entry, pop))
        button.grid(row=3, pady=12, padx=10, sticky="ew")
    
    def toggle_loop(self, sw, entry, pop):
        time = entry.get()
        if time != "":
            pop.destroy()
            on_state = True
            self.continuous_sweep(sw, float(time))
        else:
            entry.configure(fg_color=("#54EFFF","#54EFFF"))
            print("Please input desired time.")
        
    def continuous_sweep(self, sw, duration): # Performs endless sweeping and data saving
        ## VNA and Scan initialization ##
        count = 0; interactive_mode = sw.intmode;
        ser, vna, stop = VNA_setup() # Automatically detects and connects VNA via pyserial in functions.py file, then returns serial port integer
        if stop == True:
            return
        if len(inspect.getmembers(sw)) != 0:
            name = sw.name; result = sw.savetype; scans = sw.number_of_sweeps; time_delay = sw.time;
        else:
            name, result, scans, time_delay = ask_name(0)
    
        scans = 1
        sweep_list = sweep_param(ser, sw.antenna, vna);
        print("Sweeping endless loop...")
        start_time = time.time();
        global off
        off = False
        while True:
            sweep_time = time.time() - sw.start_time # calculates instance that a sweep is performed
            sweep_results, corrected_sweep = sweep(ser, sweep_list)
            count += 1; scans += 1;
            if sw.save == 1:
                endless_type = 3;
                file = generate_file(sweep_results, sweep_list, count, name, result, scans, corrected_sweep, sweep_time, endless_type, 0)
                if result == 0:
                        try:
                            folder(file, stype)
                        except:
                            pass
            if sw.final != 2:
                plt = endless_S11_plot(corrected_sweep, interactive_mode, count, sw.final, sw.linear)
                
            #if count >= 50:
            #  close_fig(plt, sweep_results, count, sw.final, sw.linear)
            # ser.close()
            # break
                
            if off is True:
                try:
                    close_fig(plt, sweep_results, count, sw.final, sw.linear)
                except:
                    plt.close("all")
                ser.close()
                break
                
            elapsed_time = time.time() - start_time
            if duration != 0:
                if elapsed_time >= duration * 60:
                    ser.close()
                    break
            time.sleep(time_delay)
            if sw.final != 2:
                plt.clf()
        print(f"Finished Sweeping {count} total S11 scans.")
        try:
            if result != 0:
                folder(file, stype)
            ser.close() # closes serial port
        except:
            ser.close() # closes serial port
        
    ## Resets GUI Colors ##
    def reset_color(self, color_flag):
        if color_flag == 1:
            self.single_switch.configure(fg_color=("#939ba2", "#4a4d50"), text_color=("gray14", "gray84"))
            self.multiple_switch.configure(fg_color=("#939ba2", "#4a4d50"), text_color=("gray14", "gray84"))
            self.endless_switch.configure(fg_color=("#939ba2", "#4a4d50"), text_color=("gray14", "gray84"))
            self.start.configure(fg_color=("#f9f9fa","#343638"))
            self.stop.configure(fg_color=("#f9f9fa","#343638"))
            self.points.configure(fg_color=("#f9f9fa","#343638"))
        else:
            self.single_switch.configure(fg_color=("#939ba2", "#4a4d50"), text_color=("gray14", "gray84"))
            self.multiple_switch.configure(fg_color=("#939ba2", "#4a4d50"), text_color=("gray14", "gray84"))
            self.endless_switch.configure(fg_color=("#939ba2", "#4a4d50"), text_color=("gray14", "gray84"))
            self.start.configure(fg_color=("#f9f9fa","#343638"))
            self.stop.configure(fg_color=("#f9f9fa","#343638"))
            self.points.configure(fg_color=("#f9f9fa","#343638"))
            self.scan_number.configure(fg_color=("#f9f9fa","#343638"))

    ### S11 Sweep Control and Operation ### (Main Operation of Sweep Button)
    def sweep_control(self):
        start_time = time.time()
        self.multiple_check()
        stop_sweep = self.flag_check()
        if stop_sweep:
            return
        if single_on is True: # Counts the number of times single sweep is performed to allow the saving logic to work properly
            self.single_scan += 1
            if stype == 0:
                self.save_count += 1
        sw = sweeper(self.filename.get(), stype, scans, self.timed, self.antenna, self.ion, save, final, linear, start_time)
        self.reset_color(0)
        if endless_on is True and final == 2:
            self.exit_endless(sw)
        elif self.antenna.check == 3:                 
            if endless_on is True:
                stop_thread = threading.Thread(target=self.close_endless)
                stop_thread.start()
                self.continuous_sweep(sw, 0)
            elif multiple_on is True:
                sw.multiple_scans()
            elif single_on is True:
                sw.single_scan(self.single_scan, self.save_count)
            else:
                self.single_switch.configure(fg_color=("#54EFFF","#54EFFF"), text_color=("#0055ff","#0055ff"))
                self.multiple_switch.configure(fg_color=("#54EFFF","#54EFFF"), text_color=("#0055ff","#0055ff"))
                self.endless_switch.configure(fg_color=("#54EFFF","#54EFFF"), text_color=("#0055ff","#0055ff"))
                print("Error: Sweep Type Not Selected.")
                
        elif self.antenna.check == 2: # checks for large dipole antenna to sweep
            if endless_on is True:
                stop_thread = threading.Thread(target=self.close_endless)
                stop_thread.start()
                self.continuous_sweep(sw, 0)
            elif multiple_on is True:
                sw.multiple_scans()
            elif single_on is True:
                sw.single_scan(self.single_scan, self.save_count)
            else:
                self.single_switch.configure(fg_color=("#54EFFF","#54EFFF"), text_color=("#0055ff","#0055ff"))
                self.multiple_switch.configure(fg_color=("#54EFFF","#54EFFF"), text_color=("#0055ff","#0055ff"))
                self.endless_switch.configure(fg_color=("#54EFFF","#54EFFF"), text_color=("#0055ff","#0055ff"))
                print("Error: Sweep Type Not Selected")
                
        elif self.antenna.check == 1: # checks for small antenna to sweep
            if endless_on is True:
                stop_thread = threading.Thread(target=self.close_endless)
                stop_thread.start()
                self.continuous_sweep(sw, 0)
            elif multiple_on is True:
                sw.multiple_scans()
            elif single_on is True:
                sw.single_scan(self.single_scan, self.save_count)
            else:
                self.single_switch.configure(fg_color=("#54EFFF","#54EFFF"), text_color=("#0055ff","#0055ff"))
                self.multiple_switch.configure(fg_color=("#54EFFF","#54EFFF"), text_color=("#0055ff","#0055ff"))
                self.endless_switch.configure(fg_color=("#54EFFF","#54EFFF"), text_color=("#0055ff","#0055ff"))
                print("Error: Sweep Type Not Selected")
        else:
            print("Error: Sweep antenna class undefined.")
        

if __name__ == "__main__":
    gui = Sweeper()
    gui.mainloop()
    try:
        gui.protocol("WM_DELETE_WINDOW", on_closing)
    except:
        pass