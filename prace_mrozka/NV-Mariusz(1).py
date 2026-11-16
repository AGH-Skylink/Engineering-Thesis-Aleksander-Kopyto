# ------------------------------------------------------
# LIBRARIES
# ------------------------------------------------------
import sys
import time
import math
import datetime
import numpy as np
import pyvisa as visa

# GUI Libraries
from tkinter import *
from tkinter import filedialog
from tkinter import ttk
from tkinter import messagebox

# Note: tkinter.tix is deprecated in newer Python versions, kept for compatibility
try:
    from tkinter.tix import *
except ImportError:
    print("Warning: tkinter.tix not found. Tooltips might not work.")

# Plotting Libraries
import matplotlib

matplotlib.use('TkAgg')  # Set backend strictly to TkAgg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Hardware Libraries (Wrapped in try-except for offline testing capability)
try:
    from pulsestreamer import PulseStreamer
    from pulsestreamer import TriggerStart, TriggerRearm
    from pulsestreamer import Sequence, OutputState
except ImportError:
    print("PulseStreamer library not found - Hardware calls will fail.")

# -----------------------------------------------------
# GLOBAL VARIABLES
# -----------------------------------------------------
stop_flag = False  # Flag to control the measurement loop

# -----------------------------------------------------
# MAIN SETUP
# -----------------------------------------------------
GUI = Tk()
GUI.title("Pulse manipulation v.0.3 - RealTime")
try:
    GUI.iconbitmap("ZF.ico")
except:
    pass  # Ignoruj, jesli plik ikony nie istnieje
GUI.configure(background='black')

# Create a dedicated frame for the plot on the right side or bottom
plot_frame = Frame(GUI, bg='white')
plot_frame.pack(side=BOTTOM, fill=BOTH, expand=True, padx=10, pady=10)

# Initialize Matplotlib Figure inside Tkinter
fig = Figure(figsize=(6, 4), dpi=100)
ax = fig.add_subplot(111)
line, = ax.plot([], [], 'r-')
ax.set_title("Real-time Measurement")
ax.set_xlabel("Parameter")
ax.set_ylabel("Normalized Signal")
ax.grid(True)

canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.draw()
canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

toolbar = NavigationToolbar2Tk(canvas, plot_frame)
toolbar.update()
canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)


# -----------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------
def gaus(x, a, b, x0, sigma):
    return b + a * np.exp(-(x - x0) ** 2 / (2 * sigma ** 2))


def browseFiles():
    # Adjusted to allow default dir fallback
    try:
        initial = "/Users/NVlab_cxd17a6/Desktop/NV-"
        filename = filedialog.askdirectory(initialdir=initial, title="Select a Directory")
    except:
        filename = filedialog.askdirectory(title="Select a Directory")

    if not filename: return ""

    date = str(datetime.datetime.now())
    date = "__" + date[0:10] + '_' + date[11:13] + '-' + date[14:16]
    current_tab_idx = tab_parent.index(tab_parent.select())
    return filename + '/' + progs[current_tab_idx] + date + '.txt'


def save(prog):
    try:
        ostream = []
        for x in range(0, len(names)):
            z = prog
            # Logic to find which tab owns the parameter
            while prog_options[z].count(names[x]) == 0:
                z -= 1
                if z < 0:
                    z = len(prog_options) - 1

            val = entries[z][x].get()
            if len(names[x]) > 7:
                ostream.append(names[x] + '\t' + val + '\n')
            else:
                ostream.append(names[x] + '\t\t' + val + '\n')
            values[x] = int(float(val))  # Safe cast float->int

        # RESTORED PATH: Absolute path as in original file
        with open("C:/Users/NVlab_cxd17a6/Desktop/NV-/PARAMETERS.txt", 'w') as param:
            param.writelines(ostream)
    except Exception as e:
        print(f"Error saving parameters: {e}")


def stop_measurement():
    global stop_flag
    stop_flag = True
    print(">>> STOP REQUESTED <<<")


def q():
    GUI.quit()
    GUI.destroy()


# -----------------------------------------------------
# MAIN MEASUREMENT LOGIC
# -----------------------------------------------------

def run(prog, draw, write):
    global stop_flag
    stop_flag = False  # Reset flag at start

    # 1. Prepare File
    file_handle = None
    if write:
        fname = browseFiles()
        if not fname:
            print("No file selected, canceling write.")
            write = False
        else:
            file_handle = open(fname, 'w')

    # 2. Hardware Connection (Wrapped)
    try:
        pulser = PulseStreamer('192.168.0.5')
        pulser.reset()
        rm = visa.ResourceManager()

        # RESTORED SCOPE ADDRESS: Using the one that was active in original file
        scope = rm.open_resource('USB0::0x0957::0x17A4::MY53160630::INSTR')
        # scope = rm.open_resource('USB0::0x2A8D::0x9007::MY60320117::INSTR') # connecting with Oscilloscope via USB - testy MXR 604 (6 GHz)

        scope.timeout = 2000  # Increased timeout
        srs = rm.open_resource('TCPIP0::192.168.0.6::inst0::INSTR')
    except Exception as e:
        messagebox.showerror("Hardware Error", f"Connection failed: {e}\nRunning in simulation/debug mode might fail.")
        if file_handle: file_handle.close()
        return

    # 3. Parameter Fetching
    # Update global values list from GUI entries before running
    for y_idx in range(len(progs)):
        for x_idx in range(len(names)):
            # This finding logic replicates the user's original structure
            if prog_options[y_idx].count(names[x_idx]):
                try:
                    # Find where this entry is stored in the jagged array
                    # This part of original code was a bit complex, assuming values are updated
                    # via the 'save' function call prior to 'run'.
                    pass
                except:
                    pass

    # Re-read values from the global 'values' list which should be updated by save()
    # Ideally, we should read directly from entries here to be sure.

    TRIGGER_CHANNEL = 1
    MAIN_CHANNEL = 2
    buff_len = 2000
    SIGNAL_SCALE = values[names.index("SIGNAL_SCALE")] * 0.001
    POWER = values[names.index("POWER")]

    # PS Outputs
    TRIGG, SHUTTER, MW = 0, 3, 1
    # Logic
    mw_on, laser_on, tr_on = 1, 0, 1
    mw_off, laser_off, tr_off = 0, 1, 0
    I_ch, Q_ch = 0, 1

    # Times (ns)
    laser_time = 2000000
    dark_time = 1600000
    mw_time = 500
    tr_time = 300
    laser_delay = 500

    dif = 0
    dif1 = []
    arg1 = []
    STEPS = values[names.index(progs[prog] + "STEPS")]

    # 4. Instrument Config
    try:
        srs.write("ENBR 1")
        srs.write("MODL 1")
        srs.write("TYPE 6")
        srs.write("QFNC 5")
        srs.write("ampr " + str(POWER * 1.0) + "\n")

        # Scope Config
        scope.write('*CLS')
        scope.write(':ACQ:TYPE AVER')
        scope.write(':ACQ:COMP NORM')
        scope.write(':ACQ:COUN ' + str(2 ** values[names.index("PRECISION")]))
        scope.write(':TRIGGER:SOURCE CHANNEL ' + str(TRIGGER_CHANNEL))
        scope.write(':TRIGGER:MODE EDGE')
        scope.write(':TRIGGER:SLOPE POSITIVE')
        scope.write(':TRIGGER:LEVEL 0.25')
        scope.write(':CHAN' + str(MAIN_CHANNEL) + ':SCAL ' + str(SIGNAL_SCALE))
        scope.write(':CHAN' + str(MAIN_CHANNEL) + ':OFFS ' + str(SIGNAL_SCALE * 3.5))
        scope.write(':TIM:SCAL ' + str(buff_len / (10 ** 7)))
        scope.write(':TIM:POS ' + str(buff_len / (2 * 10 ** 6) - 4 * laser_delay / (10 ** 9)))
        scope.write(':WAV:SOUR CHAN' + str(MAIN_CHANNEL))
        scope.write(':WAV:FORM WORD')
        scope.write(':WAV:POIN:MODE MAX')
        scope.write(':WAV:POIN ' + str(buff_len * 1000))
    except Exception as e:
        print(f"Instrument setup error: {e}")

    # Specific Params
    PRECISION = values[names.index("PRECISION")]
    FREQ = values[names.index("FREQ")] * 10 ** 6
    FREQ1 = values[names.index("FREQ1")] * 10 ** 6
    FREQ2 = values[names.index("FREQ2")] * 10 ** 6
    RABI1 = values[names.index("RABI1")]
    RABI2 = values[names.index("RABI2")]
    PIPULSE = values[names.index("PIPULSE")]
    T11 = values[names.index("T11")]
    T12 = values[names.index("T12")]
    PI2PULSE = values[names.index("PI2PULSE")]
    MWDELAY1 = values[names.index("MWDELAY1")]
    MWDELAY2 = values[names.index("MWDELAY2")]
    CPMG_N = values[names.index("CPMG_N")]
    UR_N = values[names.index("UR_N")]
    PHASE1 = values[names.index("PHASE1")]
    PHASE2 = values[names.index("PHASE2")]
    ELONG2 = values[names.index("ELONG2")]

    # Preamble Write
    if write and file_handle:
        file_handle.write("CONSTANT PARAMETERS OF RUN:\n")
        file_handle.write(f"POWER\t\t{POWER}\n")
        file_handle.write(f"FREQ\t\t{int(FREQ / 10 ** 6)}\n")
        if prog != progs.index("RABI"):
            file_handle.write(f"PIPULSE\t\t{PIPULSE}\nPI2PULSE\t{PI2PULSE}\n")
        file_handle.write("\n")

    # Arrays/Constants for Sequences
    URS = [4, 6, 8, 10, 12, 14, 16]
    if UR_N not in URS and prog == progs.index("UR"):
        print("Wrong UR_N")
        return

    N = [4, 6, 8, 10, 12, 14, 16]
    phases = [[0, 1, 1, 0], [0, 2, 0, 0, 2, 0], [0, 1, 3, 2, 2, 3, 1, 0], [0, 4, 2, 4, 0, 0, 4, 2, 4, 0],
              [0, 1, 3, 0, 4, 3, 3, 4, 0, 3, 1, 0], [0, 6, 4, 8, 4, 6, 0, 0, 6, 4, 8, 4, 6, 0],
              [0, 1, 3, 6, 2, 7, 5, 4, 4, 5, 7, 2, 6, 3, 1, 0]]
    multipliers = [math.pi, math.pi / 3, math.pi / 2, math.pi / 5, math.pi / 3, math.pi / 7, math.pi / 4]

    srs.write('FREQ ' + str(FREQ))

    # Initialize Plot for new run
    ax.cla()
    ax.set_xlabel("X Axis")
    ax.set_ylabel("Contrast (Signal/Ref)")
    ax.grid(True)
    line, = ax.plot([], [], 'b-o', markersize=3)
    canvas.draw()

    final = OutputState([SHUTTER], 0, 0)  # Default state after sequence

    # -----------------------------------------------------
    # MEASUREMENT LOOP
    # -----------------------------------------------------
    for probe in range(0, STEPS + 1):
        # CHECK STOP FLAG
        if stop_flag:
            print("Measurement stopped by user.")
            break

        # Refresh GUI
        GUI.update()

        # Parameter Calculation
        arg = 0
        if prog == progs.index("ODMR"):
            freq = FREQ1 + probe * (FREQ2 - FREQ1) / STEPS
            srs.write('FREQ ' + str(freq))
            mw_time = PIPULSE
            arg = freq / 10 ** 9
        elif prog == progs.index("RABI"):
            mw_time = RABI1 + round(probe * (RABI2 - RABI1) / STEPS)
            arg = mw_time
        elif prog == progs.index("T1"):
            mw_time = PIPULSE * (probe % 2)
            dark_time = round(T11 + (T12 - T11) * (probe - probe % 2) / STEPS)
            arg = dark_time / 10 ** 6
        elif prog == progs.index("RAMSEY") or prog == progs.index("ECHO"):
            mw_delay = MWDELAY1 + round(probe * (MWDELAY2 - MWDELAY1) / STEPS)
            arg = 2 * mw_delay
        elif prog == progs.index("CPMG"):
            mw_delay = MWDELAY1 + round(probe * (MWDELAY2 - MWDELAY1) / STEPS)
            arg = 2 * CPMG_N * mw_delay
        elif prog == progs.index("UR"):
            mw_delay = MWDELAY1 + round(probe * (MWDELAY2 - MWDELAY1) / STEPS)
            arg = (UR_N - 1) * mw_delay

        # Trigger Scope
        scope.write(':RUN')

        # --- SEQUENCE BUILDING (Same as original, condensed) ---
        mw_seq = []
        I_seq, Q_seq = [], []

        # Default empty sequences
        I_seq = [[1, 0]]
        Q_seq = [[1, 0]]

        if prog in [progs.index("ODMR"), progs.index("RABI"), progs.index("T1")]:
            mw_seq = [(laser_time + laser_delay, mw_off), (mw_time, mw_on), (1, mw_off)]
            I_seq = [[laser_time, 0], [2 * laser_delay + mw_time, 0.5], [1, 0]]

        elif prog == progs.index("RAMSEY"):
            mw_seq = [(laser_time + laser_delay, mw_off), (PI2PULSE, mw_on), (mw_delay, mw_off), (PI2PULSE, mw_on),
                      (1, mw_off)]
            I_seq = [[laser_time, 0], [2 * laser_delay + mw_delay + 2 * PI2PULSE, 0.5], [1, 0]]

        elif prog == progs.index("ECHO"):
            mw_seq = [(laser_time + laser_delay, mw_off), (PI2PULSE, mw_on), (mw_delay, mw_off), (PIPULSE, mw_on),
                      (mw_delay, mw_off), (PI2PULSE, mw_on), (1, mw_off)]
            # (Keeping original I/Q logic for Echo)
            I_seq = [[laser_time, 0],
                     [laser_delay + PI2PULSE + round(mw_delay / 2.0), math.cos(PHASE1 * math.pi / 180.0) * 0.5],
                     [mw_delay + PIPULSE, 0.5], [round(mw_delay / 2.0) + PI2PULSE + round(ELONG2) + laser_delay,
                                                 math.cos(PHASE2 * math.pi / 180.0) * 0.5], [1, 0]]
            Q_seq = [[laser_time, 0],
                     [laser_delay + PI2PULSE + round(mw_delay / 2.0), math.sin(PHASE1 * math.pi / 180.0) * 0.5],
                     [mw_delay + PIPULSE, 0], [round(mw_delay / 2.0) + PI2PULSE + round(ELONG2) + laser_delay,
                                               math.sin(PHASE2 * math.pi / 180.0) * 0.5], [1, 0]]

        elif prog == progs.index("CPMG"):
            # Reconstruction of CPMG logic
            Q_seq = [[laser_time + laser_delay + PI2PULSE + mw_delay / 2, 0],
                     [(mw_delay) * (CPMG_N * 2 - 1) + PIPULSE * CPMG_N, 0.5], [1, 0]]
            mw_seq = [(laser_time + laser_delay, mw_off), (PI2PULSE, mw_on), (mw_delay, mw_off)]
            for it in range(CPMG_N - 1):
                mw_seq = np.concatenate((mw_seq, [[PIPULSE, mw_on], [2 * mw_delay, mw_off]]), axis=0)
            mw_seq = np.concatenate((mw_seq, [[PIPULSE, mw_on], [mw_delay, mw_off], [PI2PULSE, mw_on], [1, mw_off]]),
                                    axis=0)
            I_seq = [[laser_time + laser_delay + PI2PULSE + mw_delay / 2, 0.5],
                     [(mw_delay) * (CPMG_N * 2 - 1) + PIPULSE * CPMG_N, 0],
                     [mw_delay / 2 + PI2PULSE + laser_delay, 0.5], [1, 0]]

        elif prog == progs.index("UR"):
            # UR Logic
            Q_seq = [[laser_time + laser_delay - mw_delay / 2, 0]]
            I_seq = [[laser_time + laser_delay - mw_delay / 2, 0]]
            mw_seq = [(laser_time + laser_delay, mw_off)]
            for it in range(UR_N - 1):
                idx = N.index(UR_N)
                mw_seq = np.concatenate((mw_seq, [[PI2PULSE, mw_on], [mw_delay, mw_off]]), axis=0)
                Q_seq = np.concatenate(
                    (Q_seq, [[mw_delay + PI2PULSE, math.cos(phases[idx][it] * multipliers[idx]) * 0.5]]), axis=0)
                I_seq = np.concatenate(
                    (I_seq, [[mw_delay + PI2PULSE, math.sin(phases[idx][it] * multipliers[idx]) * 0.5]]), axis=0)
            mw_seq = np.concatenate((mw_seq, [[PI2PULSE, mw_on], [1, mw_off]]), axis=0)
            # Note: UR last append was slightly buggy in original indentation, fixed here assuming last elements
            idx = N.index(UR_N)
            Q_seq = np.concatenate(
                (Q_seq, [[mw_delay / 2 + PI2PULSE + laser_delay, math.cos(phases[idx][it] * multipliers[idx]) * 0.5]]),
                axis=0)
            I_seq = np.concatenate(
                (I_seq, [[mw_delay / 2 + PI2PULSE + laser_delay, math.sin(phases[idx][it] * multipliers[idx]) * 0.5]]),
                axis=0)

        sh_seq = [(laser_time, laser_on), (dark_time, laser_off)]
        tr_seq = [(laser_time + dark_time - laser_delay, tr_off), (tr_time, tr_on), (1, tr_off)]

        # Sequence Upload
        seq = Sequence()
        seq.setDigital(SHUTTER, sh_seq)
        seq.setDigital(TRIGG, tr_seq)
        seq.setDigital(MW, mw_seq)
        seq.setAnalog(I_ch, I_seq)
        seq.setAnalog(Q_ch, Q_seq)

        n_runs = 2 ** PRECISION + 2
        seq_time = laser_time + dark_time
        pulser.stream(seq, n_runs, final=final)

        # Wait for completion (Non-blocking wait ideally, but keeping sleep for simplicity)
        # We break sleep into chunks to allow STOP to work during long waits
        wait_time = seq_time * n_runs / 1e9
        start_wait = time.time()
        while time.time() - start_wait < wait_time:
            if stop_flag: break
            GUI.update()
            time.sleep(0.05)

        if stop_flag: break

        # Readout
        scope.write(':STOP')
        yoff = 32767  # As per original override
        ymult = SIGNAL_SCALE / 8192.0
        yzero = float(scope.query(':WAV:YOR?'))
        xincr = float(scope.query(':WAV:XINC?'))
        scope.write(':WAV:BYT LSBF')
        scope.write(':WAV:UNS 0')
        scope.write(':WAV:DATA?')

        raw_data = scope.read_raw()
        data2 = raw_data[10:]  # Header usually starts with #9... check bytes. Original said 32.
        # Safety check for header length:
        if chr(raw_data[0]) == '#':
            digits = int(chr(raw_data[1]))
            header_len = 2 + digits
            data2 = raw_data[header_len:-1]
        else:
            data2 = raw_data[32:-1]  # Fallback to original

        light_wave = np.frombuffer(data2, dtype=np.int16)
        light_wave = (light_wave - yoff) * ymult + yzero

        # --- DATA PROCESSING ---
        light_wave = light_wave - np.min(light_wave)
        noise = 0.2 * light_wave[-1]  # Using last point as reference for noise level
        measure_span = 50

        # SAFER PEAK FINDING
        i = 0
        try:
            while i < len(light_wave) and light_wave[i] < noise:
                i += 1
            if i >= len(light_wave) - measure_span:
                print("Warning: Signal trigger not found, using default index 0")
                i = 0
        except IndexError:
            i = 0

        in1_start = i
        in1 = np.sum(light_wave[in1_start: in1_start + measure_span])

        in2_start = len(light_wave) - 1 - measure_span
        in2 = np.sum(light_wave[in2_start: in2_start + measure_span])

        # AVOID DIV BY ZERO
        if in2 == 0: in2 = 1e-9

        val = in1 / in2

        # T1 Handling (Differential)
        if prog == progs.index("T1"):
            if probe % 2 == 0:
                dif = val
            else:
                current_y = dif - val
                dif1.append(current_y)
                arg1.append(arg)
                if write and file_handle:
                    file_handle.write(str(arg) + " " + str(current_y) + "\n")

                # Update Real-time Plot
                line.set_data(arg1, dif1)
                ax.relim()
                ax.autoscale_view()
                canvas.draw()
        else:
            arg1.append(arg)
            dif1.append(val)
            if write and file_handle:
                file_handle.write(str(arg) + " " + str(val) + "\n")

            # Update Real-time Plot
            line.set_data(arg1, dif1)
            ax.relim()
            ax.autoscale_view()
            canvas.draw()

        print(f"Progress: {round(probe * 100 / STEPS, 2)}%")

    # End of Loop
    if write and file_handle:
        file_handle.close()

    scope.close()
    pulser.constant(OutputState.ZERO())
    print("Measurement Finished or Stopped.")


# -----------------------------------------------------
# GUI LAYOUT (Preserved Original Logic)
# -----------------------------------------------------
style = ttk.Style()
style.theme_create("MyStyle", parent="alt", settings={
    "TNotebook": {"configure": {"tabmargins": [2, 5, 2, 0]}},
    "TNotebook.Tab": {"configure": {"padding": [5, 5]}, }})
style.theme_use("MyStyle")

tab_parent = ttk.Notebook(GUI)

names = ["SIGNAL_SCALE", "POWER", "PRECISION", "FREQ", "FREQ1", "FREQ2", "ODMRSTEPS", "RABI1", "RABI2", "RABISTEPS",
         "PIPULSE",
         "T11", "T12", "T1STEPS", "PI2PULSE", "MWDELAY1", "MWDELAY2", "PHASE1", "PHASE2", "ELONG2", "ECHOSTEPS",
         "RAMSEYSTEPS", "CPMG_N", "CPMGSTEPS",
         "UR_N", "URSTEPS"]
progs = ["GENERAL OPTIONS", "ODMR", "RABI", "T1", "RAMSEY", "ECHO", "CPMG", "UR"]
prog_options = [["SIGNAL_SCALE", "POWER", "PRECISION", "FREQ", "PIPULSE", "PI2PULSE"], ["FREQ1", "FREQ2", "ODMRSTEPS"],
                ["RABI1", "RABI2", "RABISTEPS"], ["T11", "T12", "T1STEPS"], ["MWDELAY1", "MWDELAY2", "RAMSEYSTEPS"],
                ["MWDELAY1", "MWDELAY2", "PHASE1", "PHASE2", "ELONG2", "ECHOSTEPS"],
                ["CPMG_N", "MWDELAY1", "MWDELAY2", "CPMGSTEPS"],
                ["UR_N", "MWDELAY1", "MWDELAY2", "URSTEPS"]]
prog_tips = ["Maximal signal voltage", "Amplification of MW generator", "Log_2 of number of averages",
             "Frequency od MW in frequency-constant "
             "experiments", "Starting MW frequency in frequency-changing experiments", "Final MW frequency in "
                                                                                       "frequency-changing experiments",
             "Number of measurement points in ODMR", "Starting pulse duration in Rabi "
                                                     "oscillations", "Final pulse duration in Rabi oscillations",
             "Number of measurement points in Rabi oscillations",
             "Duration of pi pulse in pulse-constant experiments", "Starting dark time duration in T1 measurement",
             "Final dark time duration in T1 measurement", "Number of measurement points in T1 measurement",
             "Duration of "
             "pi-half pulse in pulse-constant experiments", "Starting time between next pulses", "Final time between "
                                                                                                 "next pulses",
             "Phase shift of the first pi-half pulse", "Phase shift of the second pi-half pulse",
             "Elongation of the second pi-half pulse in comparation to the first one",
             "Number of measurement points in Hahn echo experiment", "Number of measurement points in Ramsey "
                                                                     "experiment",
             "Number of pi pulses in CPMG sequence", "Number of measurement points in CPMG experiment",
             "Type of UR(N) sequence from set {4, 6, 8, 10, 12, 14, 16}",
             "Number of measurement points in UR experiment"]
units = ["mV", "dBm", " ", "MHz", "MHz", "MHz", " ", "ns", "ns", " ", "ns", "ns", "ns", " ", "ns", "ns", "ns", "deg",
         "deg", "ns", " ", " ", " ", " ", " ", " "]

# Initialize Lists
unit_labels = [[] for _ in progs]
tab = [[] for _ in progs]
tips = [[] for _ in progs]
entries = [[] for _ in progs]
labels = [[] for _ in progs]

# Load Parameters
values = []
try:
    # RESTORED PATH: Relative path for reading as in original file (or absolute if needed, but original used relative here)
    with open("PARAMETERS.txt", 'r') as param:
        istream = param.readlines()
        for x in range(len(names)):
            # Crude parsing based on original code assumption of format
            line = istream[x]
            parts = line.split('\t')
            values.append(int(float(parts[-1].strip())))
except:
    print("Parameter file not found or corrupted, using zeros.")
    values = [0] * len(names)

draw = BooleanVar()
write = BooleanVar()

# Build Tabs
for y in range(len(progs)):
    xx = 0
    tab[y] = ttk.Frame(tab_parent)
    tab_parent.add(tab[y], text=progs[y])

    for x in range(0, len(names)):
        entries[y].append(Entry(tab[y], width=20))
        entries[y][x].insert(0, str(values[x]))
        labels[y].append(Label(tab[y], text=names[x]))
        unit_labels[y].append(Label(tab[y], text=units[x]))

        if prog_options[y].count(names[x]):
            entries[y][x].grid(row=xx, column=1, padx=3, pady=3)
            labels[y][x].grid(row=xx, column=0, padx=3, pady=3, sticky=W)

            try:
                tips[y].append(Balloon(tab[y]))
                tips[y][xx].bind_widget(labels[y][x], balloonmsg=prog_tips[x])
            except:
                pass

            unit_labels[y][x].grid(row=xx, column=2, padx=3, pady=3, sticky=W)
            xx += 1

    if progs[y] != "GENERAL OPTIONS":
        # Control Buttons
        btn_frame = Frame(tab[y])
        btn_frame.grid(row=xx + 2, column=0, columnspan=3, pady=10)

        Draw = Checkbutton(tab[y], text="Show Plot (Realtime)", variable=draw)
        Draw.grid(row=xx, column=0, padx=3, pady=3)
        Draw.select()  # Default ON

        Checkbutton(tab[y], text="Save to file", variable=write).grid(row=xx, column=1, padx=3, pady=3)

        # RUN BUTTON
        Run = Button(btn_frame, text="RUN", width=10, height=2, bg="#ddffdd",
                     command=lambda idx=y: [save(idx), run(idx, draw.get(), write.get())])
        Run.pack(side=LEFT, padx=5)

        # STOP BUTTON (NEW)
        Stop = Button(btn_frame, text="STOP", width=10, height=2, bg="#ffdddd",
                      command=stop_measurement)
        Stop.pack(side=LEFT, padx=5)

        # QUIT BUTTON
        Button(btn_frame, text="QUIT", width=10, height=2, command=q).pack(side=LEFT, padx=5)

tab_parent.pack(side=TOP, expand=1, fill="both")

GUI.mainloop()