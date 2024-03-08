from VNA_Functions import * # imports every function from functions.py file
from VNA_GUI import *
import customtkinter as ctk
import time
import inspect

# Settings for test antennas and new antenna classes
class small_vhf_dipole: 
    def __init__(self, check):
        self.start = 1e9
        self.stop = 1.5e9
        self.points = 401
        self.check = check
    
class large_dipole:
    def __init__(self, check):
        self.start = 100e6
        self.stop = 300e6
        self.points = 401
        self.check = check
        
class new_antenna:
    def __init__(self, start_entry, stop_entry, points_entry, check):
        self.start = si_prefix(start_entry)
        self.stop = si_prefix(stop_entry)
        self.points = int(points_entry)
        self.check = check

class saved_new_antenna:
    def __init__(self, start, stop, points, check):
        self.start = start
        self.stop = stop
        self.points = points
        self.check = check

# Main class for configuration, sweeping, and saving # (Neatly Interfaces GUI Module with Functions Module)
class sweeper():
    def __init__(self, name, savetype, number_of_sweeps, time, antenna, intmode, save, final, linear, start_time):
        self.name = name                          # file name
        self.savetype = savetype                  # determines if sweeps are saved to separate files (save must be true)
        self.number_of_sweeps = number_of_sweeps  # returns number of sweeps to perform
        self.time = time                          # returns time delay between sweeps
        self.antenna = antenna                    # returns antenna sweep config/parameters
        self.intmode = intmode                    # interactive mode for plots
        self.save = save                          # determines whether to save data to a file or not
        self.final = final                        # determines whether to show averaging in plots
        self.linear = linear                      # determines whether the plot is a scatter plot or a line plot
        self.start_time = start_time              # initializes internal system time for log
        
        
    def single_scan(sw, count, save_count): # sweeps only one scan and saves data
        ## VNA and Scan initialization ##
        ser, vna, stop = VNA_setup() # Automatically detects and connects VNA via pyserial in functions.py file, then returns serial port integer
        if stop == True:
            return
        if len(inspect.getmembers(sw)) != 0:
            name = sw.name; result = sw.savetype; scans = sw.number_of_sweeps;
        else:
            name, result, scans = ask_name(1)
           
        sweep_list = sweep_param(ser, sw.antenna, vna)
        sweep_time = time.time() - sw.start_time # calculates instance that a sweep is performed
        print("Sweeping single scan...")
        sweep_results, corrected_sweep = sweep(ser, sweep_list) # sweep_list array of start freq., stop freq., step size, number of sweep points, and values per freq.
    
        if sw.save == 1:
            if scans != "": 
                scans = "";
            single_type = 1;
            file = generate_file(sweep_results, sweep_list, count, name, result, scans, corrected_sweep, sweep_time, single_type, save_count)
        if sw.final != 2:
            S11_plot(corrected_sweep, 0, sw.final, sw.linear)
        print("Finished Sweeping single S11 scan.")
        try:
            folder(file, result)
            ser.close() # closes serial port
        except:
            ser.close() # closes serial port
        
    def multiple_scans(sw): # sweeps to desired number of scans, includes time delay between scans, and saves data
        ## VNA and Scan initialization ##
        count = 0; interactive_mode = sw.intmode;
        ser, vna, stop = VNA_setup() # Automatically detects and connects VNA via pyserial in functions.py file, then returns serial port integer
        if stop == True:
            return
        if len(inspect.getmembers(sw)) != 0:
            name = sw.name; result = sw.savetype; scans = sw.number_of_sweeps; time_delay = sw.time; print("number of scans", scans);
        else:
            name, result, scans, time_delay = ask_name(0)
            
        sweep_list = sweep_param(ser, sw.antenna, vna)
        try: 
            print("Sweeping ", scans, " scans...")
            while count < scans:
                sweep_time = time.time() - sw.start_time # calculates instance that a sweep is performed
                sweep_results, corrected_sweep = sweep(ser, sweep_list)
                count += 1;
                if sw.save == 1:
                    multiple_type = 2;
                    file = generate_file(sweep_results, sweep_list, count, name, result, scans, corrected_sweep, sweep_time, multiple_type, 0)
                    if result == 0:
                        try:
                            folder(file, result)
                        except:
                            pass
                if sw.final != 2:
                    endless_S11_plot(corrected_sweep, interactive_mode, count, sw.final, sw.linear)
                time.sleep(time_delay)
            plt.show()
            print(f"Finished Sweeping {count} total S11 scans.")
        except:
            pass
        try:
            if result != 0:
                folder(file, result)
            ser.close() # closes serial port
        except:
            ser.close() # closes serial port