import sys
import serial.tools.list_ports
import struct
import math
import datetime
import time
import inspect
from matplotlib import pyplot as plt
import numpy as np
import os
import shutil
import re

def VNA_setup(): # Detects and connects the VNA to serial via USB
    available_ports = list(serial.tools.list_ports.comports()) # sweep_lists all possible ports for port in serial.tools.list_ports.comports():
    # Or use this command in CMD terminal to find active VNA port: python -m serial.tools.list_ports
    #print(available_ports)
    device_port = None
    for port in available_ports:
        if "ACM" in port.device: # VNA appears to either be ACM0 or ACM1 in linux
            device_port = port.device
            break
        elif "USB Serial Device" in port.description: # Finds VNA port for com port in windows
            device_port = port.device
            break
        
    ser = None; vna = None; stop = None;
    if device_port != None:
        ser = serial.Serial(device_port, timeout=2) # opens and defines serial port for VNA with a timeout of 2 seconds to avoid endless read() function operation
        ser.baudrate = 9600 # sets baud rate for clear data communication with VNA
        print("Serial port connected successfully:", device_port)
        
        hard_address= bytes([0x12, 0xf2]); # Determines which VNA is being used (V2 Plus4 Pro can handle larger sweep points than V2 black/gold clone)
        ser.write(hard_address)
        hardware = ser.read() 
        
        v2_black_gold = False; v2_pro = False; default = False;
        if hardware == b'\x02':
            v2_black_gold = True
        elif hardware == b'\x04':
            v2_pro = True
        else:
            default = True
        vna = [v2_black_gold, v2_pro, default]
    else:
        print("Device port not found.")
        stop = True # terminates program if the VNA is not detected
        
    return ser, vna, stop



# Checks Responsiveness of VNA
def indicate(ser): 
    indicate_cmd = bytes([0x0d]);
    ser.write(indicate_cmd)
    print("Indicate Response: ", ser.read())

# Parses inputs for SI prefixes [G/M/k]
def si_prefix(value):
    prefixes = {
        '': 1,
        'k': 1e3,
        'M': 1e6,
        'm': 1e6,
        'G': 1e9,
        'g': 1e9
    }
    num_str, unit = value[:-1], value[-1]
    num = float(num_str)
    scaling_factor = prefixes.get(unit, 1)
    return int(num * scaling_factor)

# Sets Sweep Parameters for VNA
def sweep_param(ser, antenna, vna):
# Use Write8 to write to start, step (uint64) 64 bits => 8 bytes
# Use Write2 to write to points, and values per freq (uint16) 16 bits => 2 bytes

    if vna[1] is True:
        points = antenna.points;
    else:
        points = 201
    start = int(antenna.start); stop = int(antenna.stop); #points = antenna.points;
    #values=int(input("Please Enter Desired Number of Measured Values Per Frequency: "))
    values = 1 # Slows down VNA if set to values larger than 1
    #print(start,stop)
    step = (stop-start)/(points-1)
    #print(step)
    if step % 1 != 0:
        step = int(round(step))
        #print("Step is rounded to:",step)
    else:
        step = int(step)
        #print("Step is whole:",step)
    index=[]; freq_index=[]
    
    for i in range(points):
        freq = start + i * step
        idx = (freq - start)/step
        index.append(idx)
        freq_index.append(freq)
    
    sweep_start_bytes= start.to_bytes(8, byteorder='little'); #print("Start Freq: ", struct.unpack('<Q', sweep_start_bytes)[0])
    sweep_step_bytes= step.to_bytes(8, byteorder='little'); #print("Step Freq value: ", struct.unpack('<Q', sweep_step_bytes)[0])
    sweep_points_bytes= points.to_bytes(2, byteorder='little'); #print("Points value: ", struct.unpack('<H', sweep_points_bytes)[0])
    sweep_values_bytes= values.to_bytes(2, byteorder='little'); #print("Values Per Freq: ", struct.unpack('<H', sweep_values_bytes)[0])

    
    #Using Write8 (0x23) and register Address (0x00) for Start Freq
    start_cmd=bytes([0x23,0x00]) + sweep_start_bytes
    #print("Sending Start Command: ", sweep_start_bytes);
    ser.write(start_cmd) # Sends Write Command

    start_read= bytes([0x12, 0x00]) # Reads 4 Bytes from first Register Address
    ser.write(start_read) # Sends Read Command
    while True:
        start_data= ser.readline() # Reads reply, should be 4 bytes hence 4 value buffer
        #print("Start Read Data Received: ", start_data, 'or:', struct.unpack('<I', start_data)[0]) # Prints out what the VNA has the Start set to
        break
    
    #Using Write8 (0x23) and register Address (0x10) for Step Freq
    step_cmd=bytes([0x23,0x10]) + sweep_step_bytes
    ser.write(step_cmd)
    
    step_read=bytes([0x12, 0x10]) # Reads 4 Bytes from 10 Register Address
    ser.write(step_read) 
    while True:
        step_data= ser.readline()
        break
    
    #Using Write2 (0x21) and register Address (0x20) for sweep points
    points_cmd=bytes([0x21,0x20])  + sweep_points_bytes
    ser.write(points_cmd)
    
    points_read=bytes([0x11, 0x20]) # Reads 2 bytes at sweep points register
    ser.write(points_read)
    while True:
        points_data= ser.readline()
        break
    
    #Using Write2 (0x21) and register Address (0x22) for Values per Frequency
    values_cmd=bytes([0x21,0x22])  + sweep_values_bytes
    ser.write(values_cmd)
    
    values_read=bytes([0x11, 0x22]) # Reads 2 bytes at sweep points register
    ser.write(values_read)
    while True:
        values_data= ser.readline()
        break
    return [start, stop, step, points, values, freq_index, sweep_start_bytes, sweep_step_bytes, sweep_points_bytes];

def reset_sweep_param(ser, sweep_list):
    sweep_start_bytes = sweep_list[6]
    sweep_step_bytes = sweep_list[7]
    sweep_points_bytes = sweep_list[8]
    #Using Write8 (0x23) and register Address (0x00) for Start Freq
    start_cmd=bytes([0x23,0x00]) + sweep_start_bytes
    ser.write(start_cmd) # Sends Write Command

    start_read= bytes([0x12, 0x00]) # Reads 4 Bytes from first Register Address
    ser.write(start_read) # Sends Read Command
    while True:
        start_data= ser.readline() # Reads reply, should be 4 bytes hence 4 value buffer
        break
    
    #Using Write8 (0x23) and register Address (0x10) for Step Freq
    step_cmd=bytes([0x23,0x10]) + sweep_step_bytes
    ser.write(step_cmd)
    
    step_read=bytes([0x12, 0x10]) # Reads 4 Bytes from 10 Register Address
    ser.write(step_read) 
    while True:
        step_data= ser.readline()
        break
    
    #Using Write2 (0x21) and register Address (0x20) for sweep points
    points_cmd=bytes([0x21,0x20])  + sweep_points_bytes
    ser.write(points_cmd)
    
    points_read=bytes([0x11, 0x20]) # Reads 2 bytes at sweep points register
    ser.write(points_read)
    while True:
        points_data= ser.readline()
        break
    

def wire_prot(ser):
    wire_cmd= bytes([0x12, 0xf1]);
    ser.write(wire_cmd)
    print("Wire Protocol Version: ", ser.read())

def variant(ser):
    var_address= bytes([0x10, 0xf0]); # op code, op value, AA address
    ser.write(var_address)
    print("Device Variant: ", ser.read())

def write_FIFO(ser, num):
    write_cmd= bytes([0x20, 0x30, num]);
    ser.write(write_cmd)
    zero=ser.read(num)
    print(zero)
    time.sleep(0.5)
    indicate(ser)

def point_conversion(num):
    ff_value = num
    while ff_value >= 255: # number of times the \0xFF read command is sent
        ff_value //= 255
    difference = num - (255 * ff_value) # final unique hex read command to send
    return ff_value, difference

   
def read_FIFO(ser, sweep_list):
    total_points = sweep_list[3] - 1
    expected_bytes = total_points * 32
    count = 0
    for count in range(0, 2):
        if total_points > 255:
            ff_value, offset = point_conversion(total_points)
            for i in range(0, ff_value): # Loops the Command ff_value times
                FIFO_command= bytes([0x18, 0x30, 0xFF]); # Reads hex maximum of 255 points from FIFO, cmd is in form: op code, register AA adress, NN (# of data points)
                ser.write(FIFO_command)
            ser.write(bytes([0x18, 0x30, offset])) # Adds offset to the command, for instance of 1024: (4*255 = 1020 + offset = 1024)
        elif total_points <= 0:
            print("invalid sweep points")
        else:
            ser.write(bytes([0x18, 0x30, total_points]))
        if count == 0:
            while True: 
                hex_data1 = ser.read(expected_bytes) # creating two data sets to compare for a full sweep, otherwise gaps are present in the sweep
                break
        elif count == 1:
            while True:
                hex_data2 = ser.read(expected_bytes)
                break
        count += 1
    return hex_data1, hex_data2

def average_data(data, sweep_list):
    step = sweep_list[2]
    ref_channel1 = np.array(data[14])
    ref_channel2 = np.array(data[15])
    zero_phase1 = np.array(data[12])
    zero_phase2 = np.array(data[13])
    gain1 = np.array(data[3])
    gain2 = np.array(data[10])
    freq1 = np.array(data[0]) 
    freq2 = np.array(data[7])
    
    freq_indices = np.argsort(freq1) # Sorts the data in terms of increasing frequency
    gain1 = gain1[freq_indices]
    freq1 = freq1[freq_indices]
    zero1 = zero_phase1[freq_indices]
    
    freq_indices2 = np.argsort(freq2)
    gain2 = gain2[freq_indices2]
    freq2 = freq2[freq_indices2]
    zero2 = zero_phase2[freq_indices2]
    
    corrected_freq = np.array([])
    corrected_gain = np.array([])
    corrected_phase = np.array([])
    corrected_mag = np.array([])
    
    start_freq = min(freq1[0], freq2[0])
    stop_freq = max(freq1[-1], freq2[-1])
    
    for freq in np.arange(start_freq, stop_freq + step, step):
        idx1 = np.where(freq1 == freq)[0]
        idx2 = np.where(freq2 == freq)[0]
        
        if len(idx1) == 0 and len(idx2) == 0:
            continue
        if len(idx1) > 0 and len(idx2) > 0:
            averaged_gain = (gain1[idx1].mean() + gain2[idx2].mean())/2.0 
            averaged_phase = (zero1[idx1].mean() + zero2[idx2].mean())/2.0
        elif len(idx1) > 0:
            averaged_gain = gain1[idx1].mean()
            averaged_phase = zero1[idx1].mean()
        else:
            averaged_gain = gain2[idx2].mean()
            averaged_phase = zero2[idx2].mean()
        
        corrected_freq = np.append(corrected_freq, freq)
        corrected_gain = np.append(corrected_gain, averaged_gain) # Gain is loosely used as a name for magnitude
        corrected_phase = np.append(corrected_phase, averaged_phase)

    corrected_mag = 10 ** (corrected_gain/20)
    real = corrected_mag * np.cos(corrected_phase)
    imaginary = corrected_mag * np.sin(corrected_phase)
    corrected_sweep = [corrected_freq, corrected_gain, freq1, gain1, freq2, gain2, real, imaginary]
    return corrected_sweep

def process_data(ser, sweep_data1, sweep_data2, sweep_list): 
    chunks1 = [sweep_data1[i:i+32] for i in range(0, len(sweep_data1), 32)] # Slices sweep_data into 32 byte chunks
    chunks2 = [sweep_data2[i:i+32] for i in range(0, len(sweep_data2), 32)] # Slices sweep_data into 32 byte chunks
    frequency = []; zero_mag = []; first_mag = []; gain_ch0 = []; gain_ch1 = []; counter = 0; old_freqIndex = 0; zero_result = []; first_result = []; ch0_phase =[];
    frequency2 = []; zero_mag2 = []; first_mag2 = []; gain_ch02 = []; gain_ch12 = []; counter2 = 0; old_freqIndex2 = 0; zero_result2 = []; first_result2 = []; ch0_phase2 =[];
    for data in chunks1:
        if counter <= len(chunks1):
            # Unpack the received data based on the structure format
            fwd0Re= struct.unpack("<i", data[0:4])[0]
            fwd0Im= struct.unpack("<i", data[4:8])[0]
            rev0Re= struct.unpack("<i", data[8:12])[0]
            rev0Im= struct.unpack("<i", data[12:16])[0]
            rev1Re= struct.unpack("<i", data[16:20])[0]
            rev1Im= struct.unpack("<i", data[20:24])[0]
            freqIndex= struct.unpack("<H", data[24:26])[0]
            #reserved= struct.unpack("<6s", data[26:32])[0] # Unused as marked by manual
            
            ref_channel = complex(fwd0Re, fwd0Im) # Forms channels into their complex parts: Real & Imaginary
            zero_channel = complex(rev0Re, rev0Im)
            first_channel = complex(rev1Re, rev1Im)
        
            zero = zero_channel / ref_channel   # Complex division with reference channel data
            first = first_channel / ref_channel
        
            zero_phase = math.atan2(zero.imag, zero.real) # Solves for phase and magnitude of both channels
            zero_magnitude = abs(zero)
            first_phase = math.atan2(first.imag, first.real)
            first_magnitude = abs(first)
            
            if zero_magnitude != 0:
                gain0 = 20 * math.log10(zero_magnitude)
                gain_ch0.append(gain0)
            elif first_magnitude != 0:
                gain1 = 20 * math.log10(first_magnitude)
                gain_ch1.append(gain1)

            freq = sweep_list[0] + (freqIndex * sweep_list[2])
            frequency.append(freq) # Fills arrays with iterative data
            zero_mag.append(zero_magnitude)
            first_mag.append(first_magnitude)
            old_freqIndex = freqIndex
            zero_result.append(zero)
            first_result.append(first)
            ch0_phase.append(zero_phase)
            counter += 1
            
    for data in chunks2:
        if counter2 <= len(chunks2):
            # Unpack the received data based on the structure format #Pro VNA 
            fwd0Re2= struct.unpack("<i", data[0:4])[0]
            fwd0Im2= struct.unpack("<i", data[4:8])[0]
            rev0Re2= struct.unpack("<i", data[8:12])[0]
            rev0Im2= struct.unpack("<i", data[12:16])[0]
            rev1Re2= struct.unpack("<i", data[16:20])[0]
            rev1Im2= struct.unpack("<i", data[20:24])[0]
            freqIndex2= struct.unpack("<H", data[24:26])[0]
            #reserved= struct.unpack("<6s", data[26:32])[0] # Unused as marked by manual

            ref_channel2 = complex(fwd0Re2, fwd0Im2) # Forms channels into their complex parts: Real & Imaginary
            zero_channel2 = complex(rev0Re2, rev0Im2)
            first_channel2 = complex(rev1Re2, rev1Im2)
        
            zero2 = zero_channel2 / ref_channel2   # Complex division with reference channel data
            first2 = first_channel2 / ref_channel2
            
            zero_phase2 = math.atan2(zero2.imag, zero2.real) # Solves for phase and magnitude of both channels
            zero_magnitude2 = abs(zero2)
            first_phase2 = math.atan2(first2.imag, first2.real)
            first_magnitude2 = abs(first2)

            if zero_magnitude2 != 0:
                gain02 = 20 * math.log10(zero_magnitude2)
                gain_ch02.append(gain02)
            elif first_magnitude2 != 0:
                gain12 = 20 * math.log10(first_magnitude2)
                gain_ch12.append(gain12)

            freq2 = sweep_list[0] + (freqIndex2 * sweep_list[2])
        
            frequency2.append(freq2) # Fills arrays with iterative data
            zero_mag2.append(zero_magnitude2)
            first_mag2.append(first_magnitude2)
            old_freqIndex2 = freqIndex2
            zero_result2.append(zero2)
            first_result2.append(first2)
            ch0_phase2.append(zero_phase2)
            counter += 1
        
        # Gain is loosely used here as an alternative name for magnitude
    return frequency, zero_mag, first_mag, gain_ch0, gain_ch1, zero_result, first_result, frequency2, zero_mag2, first_mag2, gain_ch02, gain_ch12, ch0_phase, ch0_phase2, ref_channel, ref_channel2
    

def S11_plot(sweep_results, num, final, linear):
    current_time = datetime.datetime.now()
    plt.figure()  
    x=sweep_results[0]
    y=sweep_results[1]
    if linear == 1:
        plt.plot(x,y, 'b-', linewidth=4, label='Averaged S11 Sweep')
        if final == 1:
            x1=sweep_results[2] # scan 1
            y1=sweep_results[3]
            x2=sweep_results[4] # scan 2
            y2=sweep_results[5]
            plt.plot(x1,y1, 'r--', linewidth=2, label='1st Sweep')
            plt.plot(x2,y2, 'y--', linewidth=2, label='2nd Sweep')
            
    elif linear == 0:
        plt.scatter(x,y, color="blue", s=50, label="Averaged S11 Sweep")
        if final == 1:
            x1=sweep_results[2] # scan 1
            y1=sweep_results[3]
            x2=sweep_results[4] # scan 2
            y2=sweep_results[5]
            plt.scatter(x1,y1, color="red", s=15, label='1st Sweep')
            plt.scatter(x2,y2, color="yellow", s=15, label='2nd Sweep')
             
    if num == 1:
       plt.ion()  # enables matplotlib interactive mode for other plots to appear
    plt.title(f"S11 Plot at {current_time}"); plt.xlabel("Frequency (Hz)"); plt.ylabel("Magnitude (dB)"); plt.legend();
    plt.show()    # displays plot


def endless_S11_plot(sweep_results, num, count, final, linear):
    if num == 1 and count == 1:
        current_time = datetime.datetime.now()
        plt.figure() 
        print(count) 
        print("number of steps:", len(sweep_results[0]))
        x=sweep_results[0]
        y=sweep_results[1]
        if linear == 1:
            plt.plot(x,y, 'b-', linewidth=4, label='Averaged S11 Sweep')
            if final == 1:
                x1=sweep_results[2] # scan 1
                y1=sweep_results[3]
                x2=sweep_results[4] # scan 2
                y2=sweep_results[5]
                plt.plot(x1,y1, 'r--', linewidth=2, label='1st Sweep')
                plt.plot(x2,y2, 'y--', linewidth=2, label='2nd Sweep')
            
        elif linear == 0:
            plt.scatter(x,y, color="blue", s=50, label="Averaged S11 Sweep")
            if final == 1:
                x1=sweep_results[2] # scan 1
                y1=sweep_results[3]
                x2=sweep_results[4] # scan 2
                y2=sweep_results[5]
                plt.scatter(x1,y1, color="red", s=15, label='1st Sweep')
                plt.scatter(x2,y2, color="yellow", s=15, label='2nd Sweep')
             
        plt.title(f"S11 Plot at {current_time}"); plt.xlabel("Frequency (Hz)"); plt.ylabel("Magnitude (dB)");        
        plt.ion()  # enables interactive mode for other plots to appear
        plt.show() # displays plot
        plt.pause(0.1)
        time.sleep(0.1)
        
    elif num == 1 and count != 1:
        plt.clf()
        current_time = datetime.datetime.now()
        print(count)
        print("number of steps:", len(sweep_results[0]))
        x=sweep_results[0]
        y=sweep_results[1]
        if linear == 1:
            plt.plot(x,y, 'b-', linewidth=4, label='Averaged S11 Sweep')
            if final == 1:
                x1=sweep_results[2] # scan 1
                y1=sweep_results[3]
                x2=sweep_results[4] # scan 2
                y2=sweep_results[5]
                plt.plot(x1,y1, 'r--', linewidth=2, label='1st Sweep')
                plt.plot(x2,y2, 'y--', linewidth=2, label='2nd Sweep')
            
        elif linear == 0:
            plt.scatter(x,y, color="blue", s=50, label="Averaged S11 Sweep")
            if final == 1:
                x1=sweep_results[2] # scan 1
                y1=sweep_results[3]
                x2=sweep_results[4] # scan 2
                y2=sweep_results[5]
                plt.scatter(x1,y1, color="red", s=15, label='1st Sweep')
                plt.scatter(x2,y2, color="yellow", s=15, label='2nd Sweep')
             
        plt.title(f"S11 Plot at {current_time}"); plt.xlabel("Frequency (Hz)"); plt.ylabel("Magnitude (dB)"); 
        plt.show()
        plt.pause(0.1)
        time.sleep(0.1)
        
    elif num is False and count == 1:
        plt.figure(1)
        current_time = datetime.datetime.now()
        print(count) 
        print("number of steps:", len(sweep_results[0]))
        x=sweep_results[0]
        y=sweep_results[1]
        if linear == 1:
            plt.plot(x,y, 'b-', linewidth=4, label='Averaged S11 Sweep')
            if final == 1:
                x1=sweep_results[2] # scan 1
                y1=sweep_results[3]
                x2=sweep_results[4] # scan 2
                y2=sweep_results[5]
                plt.plot(x1,y1, 'r--', linewidth=2, label='1st Sweep')
                plt.plot(x2,y2, 'y--', linewidth=2, label='2nd Sweep')
            
        elif linear == 0:
            plt.scatter(x,y, color="blue", s=50, label="Averaged S11 Sweep")
            if final == 1:
                x1=sweep_results[2] # scan 1
                y1=sweep_results[3]
                x2=sweep_results[4] # scan 2
                y2=sweep_results[5]
                plt.scatter(x1,y1, color="red", s=15, label='1st Sweep')
                plt.scatter(x2,y2, color="yellow", s=15, label='2nd Sweep')
             
        plt.title(f"S11 Plot at {current_time}"); plt.xlabel("Frequency (Hz)"); plt.ylabel("Magnitude (dB)");        
    
    else:
        plt.figure(count)
        current_time = datetime.datetime.now()
        print(count) 
        print("number of steps:", len(sweep_results[0]))
        x=sweep_results[0]
        y=sweep_results[1]
        if linear == 1:
            plt.plot(x,y, 'b-', linewidth=4, label='Averaged S11 Sweep')
            if final == 1:
                x1=sweep_results[2] # scan 1
                y1=sweep_results[3]
                x2=sweep_results[4] # scan 2
                y2=sweep_results[5]
                plt.plot(x1,y1, 'r--', linewidth=2, label='1st Sweep')
                plt.plot(x2,y2, 'y--', linewidth=2, label='2nd Sweep')
            
        elif linear == 0:
            plt.scatter(x,y, color="blue", s=50, label="Averaged S11 Sweep")
            if final == 1:
                x1=sweep_results[2] # scan 1
                y1=sweep_results[3]
                x2=sweep_results[4] # scan 2
                y2=sweep_results[5]
                plt.scatter(x1,y1, color="red", s=15, label='1st Sweep')
                plt.scatter(x2,y2, color="yellow", s=15, label='2nd Sweep')
             
        plt.title(f"S11 Plot at {current_time}"); plt.xlabel("Frequency (Hz)"); plt.ylabel("Magnitude (dB)");
    return plt

def close_fig(plt, sweep_results, count, final, linear):    
        plt.figure(count)
        current_time = datetime.datetime.now()
        print('Loop Closed') 
        
        x=sweep_results[0]
        y=sweep_results[1]
        if linear == 1:
            plt.plot(x,y, 'b-', linewidth=4, label='Averaged S11 Sweep')
            if final == 1:
                x1=sweep_results[2] # scan 1
                y1=sweep_results[3]
                x2=sweep_results[4] # scan 2
                y2=sweep_results[5]
                plt.plot(x1,y1, 'r--', linewidth=2, label='1st Sweep')
                plt.plot(x2,y2, 'y--', linewidth=2, label='2nd Sweep')
            
        elif linear == 0:
            plt.scatter(x,y, color="blue", s=50, label="Averaged S11 Sweep")
            if final == 1:
                x1=sweep_results[2] # scan 1
                y1=sweep_results[3]
                x2=sweep_results[4] # scan 2
                y2=sweep_results[5]
                plt.scatter(x1,y1, color="red", s=15, label='1st Sweep')
                plt.scatter(x2,y2, color="yellow", s=15, label='2nd Sweep')
             
        plt.title(f"S11 Plot at {current_time}"); plt.xlabel("Frequency (Hz)"); plt.ylabel("Magnitude (dB)");
        plt.close('all')


def generate_file(sweep_results, sweep_list, count, name, result, scans, corrected_sweep, sweep_time, sweep_type, save_count): 
    # declaring data
    freq = corrected_sweep[0]
    re = corrected_sweep[6]
    imaginary = corrected_sweep[7]
    if sweep_type == 1:
        sweep_type = "Single Sweep";
    elif sweep_type == 2:
        sweep_type = "Multiple Sweep";
    elif sweep_type == 3:
        sweep_type = "Continuous Sweep";
    
    if scans == "": # fixes single scan saving to one file
        scans = count
    
    if result == 1 and count == 1: # initiates file to scan consecutive scans to a single file
        datafile = open(f"{name}.s1p","w")          # opens the text file

        # Header
        datafile.write(f"! VNA_S11_Sweeper\n")
        current_date= datetime.datetime.now().strftime("%Y-%m-%d")
        current_time= datetime.datetime.now().strftime("%H-%M-%S")
        datafile.write(f"! Date: {current_date} Time: {current_time} System Time: {sweep_time} \n")
        datafile.write(f"! Start: {sweep_list[0]} Hz Stop: {sweep_list[1]} Hz Sweep Points: {sweep_list[3]}\n")

        # Frequency Data
        datafile.write(f"! Sweep Mode: {sweep_type} Scan number: {count}:\n")
        datafile.write("# Hz S RI R 50\n")
    
        # Sorting and Data Processing
        for i in range(len(freq)): 
            frequency = freq[i]
            real = re[i]
            imag = imaginary[i]
            datafile.write(f"{frequency} {real} {imag}\n")
        datafile.close()
        
    elif result == 1 and count != 1 and count < scans: # Saves consecutive scans
        datafile = open(f"{name}.s1p","a")          # opens the text file
        for i in range(0,3): # writes 3 line gap between previous scan data
            datafile.write("\n")
        current_date= datetime.datetime.now().strftime("%Y-%m-%d")
        current_time= datetime.datetime.now().strftime("%H-%M-%S")
        datafile.write(f"! Date: {current_date} Time: {current_time} System Time: {sweep_time} \n")
        datafile.write(f"! Sweep Mode: {sweep_type} Scan number: {count}:\n")
    
        for i in range(len(freq)): 
            frequency = freq[i]
            real = re[i]
            imag = imaginary[i]
            datafile.write(f"{frequency} {real} {imag}\n")
        datafile.close()
        
    elif result == 1 and count != 1 and count == scans: # Saves last sweep and closes file
        datafile = open(f"{name}.s1p","a")          # opens the text file
        for i in range(0,3): # writes 3 line gap between previous scan data
            datafile.write("\n")
        current_date= datetime.datetime.now().strftime("%Y-%m-%d")
        current_time= datetime.datetime.now().strftime("%H-%M-%S")
        datafile.write(f"! Date: {current_date} Time: {current_time} System Time: {sweep_time} \n")
        datafile.write(f"! Sweep Mode: {sweep_type} Scan number: {count}:\n")
        
        for i in range(len(freq)): 
            frequency = freq[i]
            real = re[i]
            imag = imaginary[i]
            datafile.write(f"{frequency} {real} {imag}\n")
        datafile.close()
        
    elif result == 0: # Scans files individually
        if count > 1:
            num = count - 1
            if save_count != 0:
                num = save_count
            filename = f"{name}{num}.s1p"      # Names the new file
        else:
            filename = f"{name}.s1p"
        datafile = open(filename,"w")          # Generates the text file

        # Header
        datafile.write(f"! VNA_S11_Sweeper\n")
        current_date= datetime.datetime.now().strftime("%Y-%m-%d")
        current_time= datetime.datetime.now().strftime("%H-%M-%S")
        datafile.write(f"! Date: {current_date} Time: {current_time} System Time: {sweep_time} \n")
        datafile.write(f"! Start: {sweep_list[0]} Hz Stop: {sweep_list[1]} Hz Sweep Points: {sweep_list[3]}\n")

        # Frequency Data
        datafile.write(f"! Sweep Mode: {sweep_type}\n")
        datafile.write("# Hz S RI R 50\n")
    
        for i in range(len(freq)): 
            frequency = freq[i]
            real = re[i]
            imag = imaginary[i]
            datafile.write(f"{frequency} {real} {imag}\n")
        datafile.close()
    return datafile

def folder(file, save_type):
    directory = os.getcwd()
    new_folder = "Saved_S1P_Files"
    new_path = os.path.join(directory, new_folder)
    if not os.path.exists(new_path):
        os.makedirs(new_folder)
        
    file_name = os.path.basename(file.name)
    old_file_path = f"{new_path}\{file_name}"
    
    if os.path.exists(old_file_path):
        if save_type == 0:
            count = 0
            while os.path.exists(old_file_path):
                temp_name = re.sub(r'\d+', '', os.path.splitext(file_name)[0])
                count += 1
                old_file_path = f"{new_path}\{temp_name}{count}.s1p"
                
            new_name = f"{temp_name}{count}.s1p"
            source_file = shutil.move(file.name, os.path.join(new_path, new_name)) 
            return
        #print("The file does exist.")
        with open(old_file_path, "a") as f:
            new_name = "temp.s1p"
            source_file = shutil.move(file.name, os.path.join(new_path, new_name))
            with open(source_file, "r") as new:
                shutil.copyfileobj(new, f)
        
    else:
        #print("The file does not exist.")
        move_file = os.path.join(new_path, file_name)
        shutil.move(file.name, os.path.join(new_path, file_name))
    

def ask_name(single):
    name = input("Please type filename for S11 datafile: ")
    
    if single == 0: # multiple scans
        ans = input("Would you like to save consecutive S11 scans to the same file?\nSaving to the same file will yield a 3 line gap between scans.\nSaving to new files will number each file accordingly.\n[Y/N]: ")
        scan_size = int(input("Please type the number of desired S11 sweeps: "))
        time_delay = int(input("Please type the amount of time delay in seconds between scans: "))
        
        if scan_size <= 0:
            print("invalid number of scans, setting to default of 1 scan.")
            scan_size = 1
            
        if time_delay < 0:
            print("invalid time delay, setting to default of 1 second.")
            time_delay = 1
            
        if ans == "Y":
            result = 1
        else:
            result = 0
        return name, result, scan_size, time_delay
        
    elif single == 1: # single scan
        result = 0; scan_size = 1; #time_delay = 0;
        return name, result, scan_size

def sweep(ser, sweep_list):
    sweep_data1, sweep_data2 = read_FIFO(ser, sweep_list) # returns sweep data per each sweep point in hexadecimal bytes
    sweep_results = process_data(ser, sweep_data1, sweep_data2, sweep_list) # processes data into 32 byte chunks and derives phase, magnitude, frequency, and complex values
    corrected_sweep = average_data(sweep_results, sweep_list)
    return sweep_results, corrected_sweep

## Bootload Mode Operations ##
def reset(ser):
    reset_cmd= bytes([0x20, 0xef, 0x5e]);
    print("Rebooting...")
    ser.write(reset_cmd)