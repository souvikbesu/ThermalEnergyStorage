#Author: Souvik Roy
#Description: Thermal Storage Project, operate Golander pump and BK Precision Power Source, acquire Temp data through NI DAQ

#Connecting GOLANDER PUMP
from pymodbus.client.sync import ModbusSerialClient as ModbusClient
client = ModbusClient(method='rtu', port='COM3', timeout=1, stopbits=1, bytesize=8, parity='E', baudrate=9600)
client.connect()

#Import modules
import time
import nidaqmx
import matplotlib.pyplot as plt
import serial
import sys
import numpy as np

d = np.loadtxt("input.txt", delimiter="\t", skiprows=1)

#Turn on Pump:
ww = client.write_register(address = 3102, value=1, unit=1)

#Connecting BK Precision 9916 Power Source
v0 = serial.Serial('COM6', 57600, timeout=1)
v0.isOpen()

v0.flushInput()
v0.flushOutput()

v0.write(b"*IDN?\n")
a = v0.readlines()
print(a)

v0.write(b"VOLT?\n")
a = v0.readlines()
print(a)


v0.write(b"OUTP?\n")
a = v0.readlines()
print(a)

#This command is used to switch to the remote control mode (PC control).
v0.write(b"SYST:REM\n")

#Specify Max Current
v0.write(b"CURR 5\n")

#Specify Max Voltage
#v0.write(b"VOLT 105\n")
#Initialize Variable (For first print statement)
Volt = 0.0


#Turn On the Power Supply
v0.write(b"OUTP ON\n")

#Create a file where the output will be written
f = open('tvsT.txt', 'w')
print("time \t Heater_Tin \t Sys_Tin \t Sys_Tout \t T_amb  \t Heater_T \t daq_Temp \t PrGage_T \t CJC_Temp \t Volt \t Curr \t PowerIn \t Rot \t RPM \t Clock", file=f)
#Turn the MATPLOT interactive mode on.
plt.ion()


def Voltage(m_dot, Cp, Tin, Tout):
    delT = Tout - Tin
    if delT < 0.0:
        delT = 0.0
    # print("TAG1",m_dot, Cp, Tin, Tout)
    return int(min(120, np.sqrt(m_dot*Cp*delT*57.5)))



init_time = int(round(time.time()))

with nidaqmx.Task() as task:
    task.ai_channels.add_ai_thrmcpl_chan("cDAQ1Mod1/ai0:3", thermocouple_type=nidaqmx.constants.ThermocoupleType.K, cjc_source=nidaqmx.constants.CJCSource.BUILT_IN)
    task.ai_channels.add_ai_thrmcpl_chan("cDAQ1Mod2/ai0:3", thermocouple_type=nidaqmx.constants.ThermocoupleType.K, cjc_source=nidaqmx.constants.CJCSource.BUILT_IN)
    task.ai_channels.add_ai_voltage_chan("cDAQ1Mod3/ai0:1", max_val=10.0)
    for drow in d:
        # Set rotation counterclockwise:
        ww = client.write_register(address=3101, value=int(drow[4]), unit=1)
        if int(drow[4])==1:
            rotation = "CCW"
        else:
            rotation ="CW"
        # Set RPM:
        rpm = int(drow[5]*10)
        ww = client.write_register(address=3100, value=rpm, unit=1)
        while (int(round(time.time())) - init_time) < drow[0]:
            data = task.read(number_of_samples_per_channel=1)
            time.sleep(1)
            #Measure Actual Current:
            v0.write(b"MEAS:CURR?\n")
            a = v0.readlines()

            # Measure Heater POwer Input:
            v0.write(b"MEAS:POW?\n")
            b = v0.readlines()

            print("%10.3f \t %.7s \t %.7s \t %.7s \t %.7s \t %.7s \t %.7s \t %.7s \t %.7s \t %.7s \t %.12s \t %.14s \t %s \t %d \t %s" %(time.clock(), \
                    str(data[0])[1:-1], str(data[1])[1:-1], str(data[2])[1:-1], str(data[3])[1:-1], str(data[4])[1:-1], str(data[5])[1:-1], \
                    str(data[6])[1:-1], str(data[7])[1:-1], Volt, str(a)[3:-4], str(b)[3:-4], rotation, int(drow[5]), time.ctime()), file=f)
            f.flush()
            Volt = Voltage(drow[2],drow[3],float(str(data[0])[1:-1]),drow[1])
            time.sleep(2)
            Volt_ = str(Volt)
            str1 = "VOLT " + Volt_ +"\n"
            b1 = str1.encode('utf-8')
            v0.write(b1)



            if float(str(data[4])[1:-1]) > 200.0:
                #set Volatge to zero
                v0.write(b"VOLT 0\n")
                # Turn Off the Power Supply
                v0.write(b"OUTP OFF\n")
                # Turn off Pump:
                ww = client.write_register(address=3102, value=0, unit=1)
                print("Max Temp Reached! Exit ")
                exit(1)

#Close file created
f.close()

#Turn Off the Power Supply
v0.write(b"OUTP OFF\n")

#Turn off Pump:
ww = client.write_register(address = 3102, value=0, unit=1)