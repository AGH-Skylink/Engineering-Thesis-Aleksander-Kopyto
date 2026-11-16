# ------------------------------------------------------
# LIBRARIES
# ------------------------------------------------------
import sys
import time
import math
import datetime
import numpy as np
import pyvisa as visa
from scipy.optimize import curve_fit
from scipy.signal import find_peaks  # Added for peak detection

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
GUI.title("NV pulse program v0.6")
try:
    GUI.iconbitmap("ZF.ico")
except:
    pass  # Ignoruj, jesli plik ikony nie istnieje
GUI.configure(background='black')

# Create a dedicated frame for the plot and fit results
plot_frame = Frame(GUI, bg='white')
plot_frame.pack(side=BOTTOM, fill=BOTH, expand=True, padx=10, pady=10)

# Initialize Matplotlib Figure inside Tkinter
fig = Figure(figsize=(6, 5), dpi=100)
# Adjust layout to make room for fit text below if needed, though we use a separate widget
fig.subplots_adjust(bottom=0.15)
ax = fig.add_subplot(111)
line, = ax.plot([], [], 'r-', label='Data')
fit_line, = ax.plot([], [], 'g--', linewidth=2, label='Fit')  # Line for live fit
ax.set_title("Real-time Measurement")
ax.set_xlabel("Parameter")
ax.set_ylabel("Normalized Signal")
ax.legend()
ax.grid(True)

canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.draw()
canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

toolbar = NavigationToolbar2Tk(canvas, plot_frame)
toolbar.update()
canvas.get_tk_widget().pack(side=TOP, fill=X)

# Fit Results Text Area (Scrollable)
fit_info_frame = Frame(plot_frame, height=100, bg='white')
fit_info_frame.pack(side=BOTTOM, fill=X)
fit_text_label = Label(fit_info_frame, text="Fit Parameters:", bg='white', font=("Arial", 10, "bold"), anchor="w")
fit_text_label.pack(side=TOP, fill=X)
fit_text = Text(fit_info_frame, height=6, font=("Consolas", 9), state='disabled', bg='#f0f0f0')
fit_text.pack(side=LEFT, fill=BOTH, expand=True)
scrollbar = Scrollbar(fit_info_frame, command=fit_text.yview)
scrollbar.pack(side=RIGHT, fill=Y)
fit_text['yscrollcommand'] = scrollbar.set

# Status/ETA Label (Moved to main GUI bottom, above plot frame)
eta_label = Label(GUI, text="Status: Ready", bg="black", fg="#00ff00", font=("Arial", 12, "bold"))
eta_label.pack(side=BOTTOM, pady=5)


# -----------------------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------------------
def gaus(x, a, b, x0, sigma):
    return b + a * np.exp(-(x - x0) ** 2 / (2 * sigma ** 2))


# --- Fitting Functions ---

def multi_lorentz(x, *params):
    """
    Generalized Lorentzian for N peaks.
    params structure: [y0, A1, x01, gamma1, A2, x02, gamma2, ...]
    """
    y0 = params[0]
    y = np.full_like(x, y0)
    # Iterate triplets (A, x0, gamma)
    for i in range(1, len(params), 3):
        if i + 2 < len(params):
            A = params[i]
            x0 = params[i + 1]
            gamma = params[i + 2]
            # Summing dips (ODMR usually dips)
            y -= A * (gamma ** 2) / ((x - x0) ** 2 + gamma ** 2)
    return y


def rabi_osc(x, A, T, omega, phi, y0):
    """ Damped oscillation for Rabi/Ramsey """
    return A * np.exp(-x / T) * np.cos(omega * x + phi) + y0


def exp_decay(x, A, T1, y0):
    """ Exponential decay for T1 """
    return A * np.exp(-x / T1) + y0


def update_fit_text(text_widget, content):
    text_widget.config(state='normal')
    text_widget.delete(1.0, END)
    text_widget.insert(END, content)
    text_widget.config(state='disabled')


def browseFiles():
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
            while prog_options[z].count(names[x]) == 0:
                z -= 1
                if z < 0:
                    z = len(prog_options) - 1

            val = entries[z][x].get()
            if len(names[x]) > 7:
                ostream.append(names[x] + '\t' + val + '\n')
            else:
                ostream.append(names[x] + '\t\t' + val + '\n')
            values[x] = int(float(val))

        with open("C:/Users/NVlab_cxd17a6/Desktop/NV-/PARAMETERS.txt", 'w') as param:
            param.writelines(ostream)
    except Exception as e:
        print(f"Error saving parameters: {e}")


def stop_measurement():
    global stop_flag
    stop_flag = True
    eta_label.config(text="Status: Stopping...", fg="red")
    print(">>> STOP REQUESTED <<<")


def q():
    GUI.quit()
    GUI.destroy()


def convert_sequence_to_plot_data(seq_tuples):
    x = [0]
    y = [0]
    current_time = 0
    if len(seq_tuples) > 0:
        y[0] = seq_tuples[0][1]
        for duration, state in seq_tuples:
            x.append(current_time)
            y.append(state)
            current_time += duration
            x.append(current_time)
            y.append(state)
    return x, y


def preview_sequence(prog):
    save(prog)
    SIGNAL_SCALE = values[names.index("SIGNAL_SCALE")] * 0.001

    # Times (ns)
    laser_time = 2000000
    dark_time = 1600000
    mw_time = 500
    tr_time = 300
    laser_delay = 500

    STEPS = values[names.index(progs[prog] + "STEPS")]

    # Specific Params
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

    # Logic constants
    mw_on, laser_on, tr_on = 1, 1, 1
    mw_off, laser_off, tr_off = 0, 0, 0

    probe = int(STEPS / 2)
    print(f"Generating preview for step {probe}/{STEPS}...")

    # --- CALCULATE TIMINGS ---
    if prog == progs.index("ODMR"):
        mw_time = PIPULSE
    elif prog == progs.index("RABI"):
        mw_time = RABI1 + round(probe * (RABI2 - RABI1) / STEPS)
    elif prog == progs.index("T1"):
        mw_time = PIPULSE * (probe % 2)
        dark_time = round(T11 + (T12 - T11) * (probe - probe % 2) / STEPS)
    elif prog == progs.index("RAMSEY") or prog == progs.index("ECHO"):
        mw_delay = MWDELAY1 + round(probe * (MWDELAY2 - MWDELAY1) / STEPS)
    elif prog == progs.index("CPMG"):
        mw_delay = MWDELAY1 + round(probe * (MWDELAY2 - MWDELAY1) / STEPS)
    elif prog == progs.index("UR"):
        mw_delay = MWDELAY1 + round(probe * (MWDELAY2 - MWDELAY1) / STEPS)

    # --- BUILD SEQUENCES ---
    mw_seq = []

    if prog in [progs.index("ODMR"), progs.index("RABI"), progs.index("T1")]:
        mw_seq = [(laser_time + laser_delay, mw_off), (mw_time, mw_on), (1, mw_off)]

    elif prog == progs.index("RAMSEY"):
        mw_seq = [(laser_time + laser_delay, mw_off), (PI2PULSE, mw_on), (mw_delay, mw_off), (PI2PULSE, mw_on),
                  (1, mw_off)]

    elif prog == progs.index("ECHO"):
        mw_seq = [(laser_time + laser_delay, mw_off), (PI2PULSE, mw_on), (mw_delay, mw_off), (PIPULSE, mw_on),
                  (mw_delay, mw_off), (PI2PULSE, mw_on), (1, mw_off)]

    elif prog == progs.index("CPMG"):
        mw_seq = [(laser_time + laser_delay, mw_off), (PI2PULSE, mw_on), (mw_delay, mw_off)]
        for it in range(CPMG_N - 1):
            mw_seq = np.concatenate((mw_seq, [[PIPULSE, mw_on], [2 * mw_delay, mw_off]]), axis=0)
        mw_seq = np.concatenate((mw_seq, [[PIPULSE, mw_on], [mw_delay, mw_off], [PI2PULSE, mw_on], [1, mw_off]]),
                                axis=0)

    elif prog == progs.index("UR"):
        mw_seq = [(laser_time + laser_delay, mw_off)]
        for it in range(UR_N - 1):
            mw_seq = np.concatenate((mw_seq, [[PI2PULSE, mw_on], [mw_delay, mw_off]]), axis=0)
        mw_seq = np.concatenate((mw_seq, [[PI2PULSE, mw_on], [1, mw_off]]), axis=0)

    sh_seq = [(laser_time, laser_on), (dark_time, laser_off)]
    tr_seq = [(laser_time + dark_time - laser_delay, tr_off), (tr_time, tr_on), (1, tr_off)]

    # --- PLOTTING ---
    preview_window = Toplevel(GUI)
    preview_window.title(f"Sequence Preview: {progs[prog]} (Step {probe})")
    preview_window.geometry("900x600")

    fig_prev = Figure(figsize=(9, 6), dpi=100)
    ax_prev = fig_prev.add_subplot(111)

    lx, ly = convert_sequence_to_plot_data(sh_seq)
    mx, my = convert_sequence_to_plot_data(mw_seq)
    tx, ty = convert_sequence_to_plot_data(tr_seq)

    end_time = lx[-1]
    lx.extend([end_time, end_time + laser_time])
    ly.extend([laser_on, laser_on])

    lx = np.array(lx) / 1000.0
    mx = np.array(mx) / 1000.0
    tx = np.array(tx) / 1000.0

    ax_prev.plot(lx, np.array(ly) + 2.5, 'g-', label="Laser")
    ax_prev.fill_between(lx, 2.5, np.array(ly) + 2.5, color='green', alpha=0.3)
    ax_prev.plot(mx, np.array(my) + 1.25, 'r-', label="MW")
    ax_prev.fill_between(mx, 1.25, np.array(my) + 1.25, color='red', alpha=0.3)
    ax_prev.plot(tx, np.array(ty), 'b-', label="Trigger")
    ax_prev.fill_between(tx, 0, np.array(ty), color='blue', alpha=0.3)

    measure_span = 50
    int_end_vis = (measure_span * 20) / 1000.0
    ref_start_vis = (laser_time / 1000.0) - int_end_vis
    ref_end_vis = (laser_time / 1000.0)

    ax_prev.axvspan(0, int_end_vis, ymin=0.8, ymax=0.9, color='orange', alpha=0.5, label='Signal (Int)')
    ax_prev.axvspan(ref_start_vis, ref_end_vis, ymin=0.8, ymax=0.9, color='purple', alpha=0.5, label='Ref')

    ax_prev.set_yticks([0.5, 1.75, 3.0])
    ax_prev.set_yticklabels(["Trigger", "MW", "Laser"])
    ax_prev.set_xlabel("Time (µs)")
    ax_prev.set_title(f"Pulse Sequence (Center Step: {probe})")
    ax_prev.legend(loc='upper right')
    ax_prev.grid(True)

    focus_end = (laser_time + dark_time) / 1000.0 + (laser_time / 1000.0) * 0.2
    ax_prev.set_xlim(left=-50, right=focus_end)

    canvas_prev = FigureCanvasTkAgg(fig_prev, master=preview_window)
    canvas_prev.draw()
    canvas_prev.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

    toolbar_prev = NavigationToolbar2Tk(canvas_prev, preview_window)
    toolbar_prev.update()
    canvas_prev.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)


# -----------------------------------------------------
# MAIN MEASUREMENT LOGIC
# -----------------------------------------------------

def run(prog, draw, write, fit_on):
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

    # 2. Hardware Connection
    try:
        pulser = PulseStreamer('192.168.0.5')
        pulser.reset()
        rm = visa.ResourceManager()
        scope = rm.open_resource('USB0::0x0957::0x17A4::MY53160630::INSTR')
        scope.timeout = 2000
        srs = rm.open_resource('TCPIP0::192.168.0.6::inst0::INSTR')
    except Exception as e:
        messagebox.showerror("Hardware Error", f"Connection failed: {e}\nRunning in simulation/debug mode might fail.")
        if file_handle: file_handle.close()
        return

    # 3. Parameter Fetching
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
    PRECISION = values[names.index("PRECISION")]

    # --- SET AXIS LABELS BASED ON PROGRAM ---
    x_label_txt = "Parameter"
    if prog == progs.index("ODMR"):
        x_label_txt = "Frequency (GHz)"
    elif prog == progs.index("T1"):
        x_label_txt = "Time (ms)"
    else:
        x_label_txt = "Time (ns)"

    ax.set_xlabel(x_label_txt)
    ax.set_ylabel("Normalized Signal")  # We will normalize to max

    # --- ETA CALCULATION START ---
    n_runs = 2 ** PRECISION + 2
    # Basic estimation for startup
    seq_time_ns = laser_time + dark_time
    # Add overhead constant based on communication speed (~0.1s)
    est_step_duration = (seq_time_ns * n_runs / 1e9) + 0.15
    total_time_sec = (STEPS + 1) * est_step_duration
    start_time = time.time()

    eta_msg = f"Total Est: {round(total_time_sec / 60, 1)} min"
    eta_label.config(text=f"Status: Running... {eta_msg}", fg="#00ff00")
    update_fit_text(fit_text, "Waiting for data...")

    # 4. Instrument Config
    try:
        srs.write("ENBR 1")
        srs.write("MODL 1")
        srs.write("TYPE 6")
        srs.write("QFNC 5")
        srs.write("ampr " + str(POWER * 1.0) + "\n")

        scope.write('*CLS')
        scope.write(':ACQ:TYPE AVER')
        scope.write(':ACQ:COMP NORM')
        scope.write(':ACQ:COUN ' + str(2 ** PRECISION))
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

    if write and file_handle:
        file_handle.write("CONSTANT PARAMETERS OF RUN:\n")
        file_handle.write(f"POWER\t\t{POWER}\n")
        file_handle.write(f"FREQ\t\t{int(FREQ / 10 ** 6)}\n")
        if prog != progs.index("RABI"):
            file_handle.write(f"PIPULSE\t\t{PIPULSE}\nPI2PULSE\t{PI2PULSE}\n")
        file_handle.write("\n")

    # Arrays/Constants
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

    # Initialize Plot
    ax.cla()
    ax.set_xlabel(x_label_txt)
    ax.set_ylabel("Normalized Signal")
    ax.grid(True)
    line, = ax.plot([], [], 'b-o', markersize=3, label='Data')
    fit_line, = ax.plot([], [], 'g--', linewidth=2, label='Fit')
    ax.legend()
    canvas.draw()

    final = OutputState([SHUTTER], 0, 0)

    # -----------------------------------------------------
    # MEASUREMENT LOOP
    # -----------------------------------------------------
    for probe in range(0, STEPS + 1):
        if stop_flag:
            print("Measurement stopped by user.")
            eta_label.config(text="Status: Stopped", fg="red")
            break

        # Refresh GUI
        GUI.update()

        # Update ETA Logic (Dynamic)
        if probe > 0:
            elapsed = time.time() - start_time
            avg_per_step = elapsed / probe
            remaining_sec = avg_per_step * (STEPS - probe)
            eta_str = f"Run: {round(elapsed / 60, 1)}m | Left: {round(remaining_sec / 60, 1)}m"
            eta_label.config(text=f"Status: {round(probe * 100 / STEPS)}% | {eta_str}")

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

        # Sequence Building (Condensed)
        mw_seq = []
        I_seq, Q_seq = [[1, 0]], [[1, 0]]

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
            I_seq = [[laser_time, 0],
                     [laser_delay + PI2PULSE + round(mw_delay / 2.0), math.cos(PHASE1 * math.pi / 180.0) * 0.5],
                     [mw_delay + PIPULSE, 0.5], [round(mw_delay / 2.0) + PI2PULSE + round(ELONG2) + laser_delay,
                                                 math.cos(PHASE2 * math.pi / 180.0) * 0.5], [1, 0]]
            Q_seq = [[laser_time, 0],
                     [laser_delay + PI2PULSE + round(mw_delay / 2.0), math.sin(PHASE1 * math.pi / 180.0) * 0.5],
                     [mw_delay + PIPULSE, 0], [round(mw_delay / 2.0) + PI2PULSE + round(ELONG2) + laser_delay,
                                               math.sin(PHASE2 * math.pi / 180.0) * 0.5], [1, 0]]
        elif prog == progs.index("CPMG"):
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

        # Wait logic (split for responsiveness)
        wait_time = seq_time * n_runs / 1e9
        sw = time.time()
        while time.time() - sw < wait_time:
            if stop_flag: break
            GUI.update()
            time.sleep(0.05)
        if stop_flag: break

        # Readout
        scope.write(':STOP')
        yoff = 32767
        ymult = SIGNAL_SCALE / 8192.0
        yzero = float(scope.query(':WAV:YOR?'))
        xincr = float(scope.query(':WAV:XINC?'))
        scope.write(':WAV:BYT LSBF')
        scope.write(':WAV:UNS 0')
        scope.write(':WAV:DATA?')

        raw_data = scope.read_raw()
        data2 = raw_data[10:]
        if chr(raw_data[0]) == '#':
            digits = int(chr(raw_data[1]))
            header_len = 2 + digits
            data2 = raw_data[header_len:-1]
        else:
            data2 = raw_data[32:-1]

        light_wave = np.frombuffer(data2, dtype=np.int16)
        light_wave = (light_wave - yoff) * ymult + yzero
        light_wave = light_wave - np.min(light_wave)
        noise = 0.2 * light_wave[-1]
        measure_span = 50

        i = 0
        try:
            while i < len(light_wave) and light_wave[i] < noise:
                i += 1
            if i >= len(light_wave) - measure_span:
                i = 0
        except IndexError:
            i = 0

        in1_start = i
        in1 = np.sum(light_wave[in1_start: in1_start + measure_span])
        in2_start = len(light_wave) - 1 - measure_span
        in2 = np.sum(light_wave[in2_start: in2_start + measure_span])
        if in2 == 0: in2 = 1e-9
        val = in1 / in2

        if prog == progs.index("T1"):
            if probe % 2 == 0:
                dif = val
            else:
                current_y = dif - val
                dif1.append(current_y)
                arg1.append(arg)
                if write and file_handle:
                    file_handle.write(str(arg) + " " + str(current_y) + "\n")
        else:
            arg1.append(arg)
            dif1.append(val)
            if write and file_handle:
                file_handle.write(str(arg) + " " + str(val) + "\n")

        # --- UPDATE PLOT ---
        # Normalize Y to max so plot scale is 0 to 1
        y_data_raw = np.array(dif1)
        max_val = np.max(y_data_raw) if len(y_data_raw) > 0 else 1.0
        if max_val == 0: max_val = 1.0

        y_data_norm = y_data_raw / max_val
        x_data = np.array(arg1)

        line.set_data(x_data, y_data_norm)
        ax.relim()
        ax.autoscale_view()

        # --- LIVE FITTING (Automatic Multi-Peak) ---
        if len(arg1) > 10 and fit_on:  # Check if fitting enabled
            try:
                fit_msg = ""

                if prog == progs.index("ODMR"):
                    # Find peaks in Normalized inverted data (dips)
                    # Contrast threshold > 0.5% means dip depth > 0.005 (in norm scale)
                    y_inv = -y_data_norm
                    peaks, properties = find_peaks(y_inv, prominence=0.01)  # 1% threshold

                    if len(peaks) > 0:
                        prominences = properties["prominences"]
                        sorted_indices = np.argsort(prominences)[::-1]
                        top_peaks = peaks[sorted_indices[:8]]  # Max 8 peaks

                        y0_guess = 1.0  # Normalized baseline is approx 1
                        p0 = [y0_guess]

                        for pk in top_peaks:
                            A_guess = (y0_guess - y_data_norm[pk])
                            x0_guess = x_data[pk]
                            gamma_guess = 0.005  # Default width guess
                            p0.extend([A_guess, x0_guess, gamma_guess])

                        try:
                            popt, _ = curve_fit(multi_lorentz, x_data, y_data_norm, p0=p0)
                            fit_y = multi_lorentz(x_data, *popt)
                            fit_line.set_data(x_data, fit_y)

                            fit_msg += f"Base: {round(popt[0], 3)}\n"
                            num_peaks = (len(popt) - 1) // 3
                            for k in range(num_peaks):
                                idx = 1 + k * 3
                                A_fit = popt[idx]
                                x0_fit = popt[idx + 1]
                                gamma_fit = popt[idx + 2]
                                contrast = (A_fit / popt[0]) * 100
                                if contrast > 0.5:  # Only show stronger than 0.5%
                                    width_fwhm = 2 * gamma_fit * 1000  # MHz
                                    fit_msg += f"P{k + 1}: {round(x0_fit, 4)}GHz|W:{round(width_fwhm, 0)}M|C:{round(contrast, 1)}%\n"

                        except Exception as e:
                            fit_msg = "Fit failed"

                elif prog == progs.index("RABI") or prog in [progs.index("RAMSEY"), progs.index("ECHO")]:
                    y0_guess = np.mean(y_data_norm)
                    A_guess = (np.max(y_data_norm) - np.min(y_data_norm)) / 2
                    T_guess = (x_data[-1] - x_data[0]) / 2
                    omega_guess = 0.1
                    try:
                        popt, _ = curve_fit(rabi_osc, x_data, y_data_norm,
                                            p0=[A_guess, T_guess, omega_guess, 0, y0_guess])
                        fit_y = rabi_osc(x_data, *popt)
                        fit_line.set_data(x_data, fit_y)
                        fit_msg += f"T: {round(popt[1], 1)} ns\n"
                        fit_msg += f"Freq: {round(popt[2] / (2 * np.pi) * 1000, 2)} MHz\n"
                    except:
                        pass

                elif prog == progs.index("T1"):
                    # T1 fitting using normalized data
                    y0_guess = y_data_norm[-1]
                    A_guess = y_data_norm[0] - y0_guess
                    T1_guess = (x_data[-1] - x_data[0]) / 3
                    if T1_guess == 0: T1_guess = 1.0  # Avoid div by zero guess

                    try:
                        popt, _ = curve_fit(exp_decay, x_data, y_data_norm, p0=[A_guess, T1_guess, y0_guess])
                        fit_y = exp_decay(x_data, *popt)
                        fit_line.set_data(x_data, fit_y)
                        # x_data is in ms, so popt[1] (T1) is in ms
                        fit_msg += f"T1: {round(popt[1], 3)} ms\n"
                    except:
                        fit_msg = "T1 Fit pending..."

                update_fit_text(fit_text, fit_msg)

            except Exception as e:
                pass
        else:
            fit_line.set_data([], [])  # Clear fit if disabled

        canvas.draw()
        print(f"Progress: {round(probe * 100 / STEPS, 2)}%")

    # End of Loop
    if write and file_handle:
        file_handle.close()

    scope.close()
    pulser.constant(OutputState.ZERO())
    eta_label.config(text="Status: Finished", fg="white")
    print("Measurement Finished or Stopped.")


# -----------------------------------------------------
# GUI LAYOUT
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

values = []
try:
    with open("PARAMETERS.txt", 'r') as param:
        istream = param.readlines()
        for x in range(len(names)):
            line = istream[x]
            parts = line.split('\t')
            values.append(int(float(parts[-1].strip())))
except:
    print("Parameter file not found or corrupted, using zeros.")
    values = [0] * len(names)

draw = BooleanVar()
write = BooleanVar()
fit_enabled = BooleanVar(value=True)  # Default fitting ON

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
        btn_frame = Frame(tab[y])
        btn_frame.grid(row=xx + 2, column=0, columnspan=3, pady=10)

        Draw = Checkbutton(tab[y], text="Show Plot", variable=draw)
        Draw.grid(row=xx, column=0, padx=3, pady=3)
        Draw.select()
        Checkbutton(tab[y], text="Save to file", variable=write).grid(row=xx, column=1, padx=3, pady=3)
        Checkbutton(tab[y], text="Live Fit", variable=fit_enabled).grid(row=xx, column=2, padx=3, pady=3)

        Run = Button(btn_frame, text="RUN", width=10, height=2, bg="#ddffdd",
                     command=lambda idx=y: [save(idx), run(idx, draw.get(), write.get(), fit_enabled.get())])
        Run.pack(side=LEFT, padx=5)
        Preview = Button(btn_frame, text="PREVIEW SEQ", width=12, height=2, bg="#ffffdd",
                         command=lambda idx=y: preview_sequence(idx))
        Preview.pack(side=LEFT, padx=5)
        Stop = Button(btn_frame, text="STOP", width=10, height=2, bg="#ffdddd",
                      command=stop_measurement)
        Stop.pack(side=LEFT, padx=5)
        Button(btn_frame, text="QUIT", width=10, height=2, command=q).pack(side=LEFT, padx=5)

tab_parent.pack(side=TOP, expand=1, fill="both")
GUI.mainloop()