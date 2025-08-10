'''
The main script of the Work Clock. Run this script at the beginning of the day to begin
tracking work sessions.
'''

# DEPENDENCIES
import tkinter as tk
import time
from datetime import datetime
import sqlite3


#### MAIN PROGRAM
class WorkClockApp:
    '''A class that manages the running of the clock.'''

    # CONSTANTS
    GUI_WIDTH = 200
    GUI_HEIGHT = 60
    INTERVAL = 3600

    def __init__(self, root):
        '''Initialize the WorkClockApp.'''

        # Load customizeable constants from the database
        create_database()
        conn = sqlite3.connect("data.sqlite3", isolation_level=None)
        WORKDAY_HOURS = conn.execute("SELECT value FROM 'constants' WHERE variable = 'WORKDAY_HOURS'").fetchall()[0]

        # Set up widget window
        self.root = root
        self.root.title("WorkClock")
        self.root.geometry(f"{self.GUI_WIDTH}x{self.GUI_HEIGHT+30}") # Extra room for additional info.
        self.root.attributes('-topmost', True)
        self.root.resizable(True, True)#(False, False)

        self.canvas = tk.Canvas(root, width=self.GUI_WIDTH, height=self.GUI_HEIGHT, bg="white", highlightthickness=0)
        self.canvas.pack()

        # Configure progress bar size
        self.padding = 10
        self.bar_width = 45
        self.bar_height = self.GUI_WIDTH - 2 * self.padding

        # Set up labels
        self.completion_label = tk.Label(root, text="Sessions Completed: 0", font=("Helvetica", 12))
        self.completion_label.pack()

        # Create a label with a little list of the variable values
        variables = conn.execute("SELECT * FROM 'constants'").fetchall()
        variables = [f"{var}: {val}" for var, val in variables]
        variables = "\n\nVariables:\n" + "\n".join(variables)
        self.variable_label = tk.Label(root, text=variables, font=("Helvetica", 12))
        self.variable_label.pack()

        # START RUNNING the Clock
        self.running = True
        self.start_time_HH_MM = time.strftime('%H:%M') # Set up for tracking the start and end times of the working day, e.g. 08:03 and 17:06
        self.start_time = time.time()
        self.elapsed_time = 0
        self.session_count = 0

        # Workblock timekeeping
        self.workblock_start = time.time()
        self.workblock_start_str = time.strftime('%H:%M')

        self.draw_progress_bar()
        self.update_bar()

        self.root.bind("<Button-1>", self.toggle_timer)  # Left-click to pause/resume
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def draw_progress_bar(self):
        '''Draw the progress bar border.'''
        self.canvas.create_rectangle(self.padding, self.padding, self.padding + self.bar_height, self.padding + self.bar_width, outline="black", width=2)

    def update_bar(self):
        # Compute time information
        elapsed = (time.time() - self.start_time) + self.elapsed_time if self.running else self.elapsed_time
        self.remaining = max(self.INTERVAL - elapsed, 0)  # 1500 seconds = 25 minutes, 3600 seconds = 60 minutes
        proportion_left = 1-(elapsed / self.INTERVAL)

        # If still running, update the progress bar
        if self.remaining > 0:
            self.canvas.create_rectangle(self.padding, self.padding, self.padding + (1-proportion_left) * self.bar_height, self.padding + self.bar_width, fill="darkred", width=2, tags="progress")
            completion_percentage = round(100 * (self.session_count * 3600 + elapsed) / (5*3600))
            self.completion_label.config(text=f"Workday completion: {completion_percentage} %")

        # Update timer display
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        self.canvas.delete("time")
        label = f"{self.session_count}:{minutes:02}:{seconds:02}" if self.running else "Paused"
        self.canvas.create_text(self.GUI_WIDTH // 2, self.GUI_HEIGHT // 2 + 3, text=label, font=("Helvetica", int(self.GUI_WIDTH * 0.08)), tags="time")

        # If an hour has been reached, reset progress bar etc
        if self.remaining <= 0 and self.running:
            self.running = True
            self.elapsed_time = 0
            self.session_count += 1

            # Start over the hour
            self.start_time = time.time()

        self.root.after(1000, self.update_bar)

    def toggle_timer(self, event=None):
        # PAUSE the clock!
        if self.running:
            self.running = False
            self.elapsed_time += time.time() - self.start_time

            # Update the workblocks table
            hours = str(round((time.time() - self.workblock_start) / 3600, 2))
            save_workblock_data(self.workblock_start_str, time.strftime('%H:%M'), hours)

        # START the clock again!
        else:
            self.running = True
            self.start_time = time.time()

            # Start over timekeeping for the new workblock
            self.workblock_start = time.time()
            self.workblock_start_str = time.strftime('%H:%M')        

    def on_close(self):
        # If still running, also log the current workblock before submitting the workday and ending the program.
        if self.running:
            hours = str(round((time.time() - self.workblock_start) / 3600, 2))
            save_workblock_data(self.workblock_start_str, time.strftime('%H:%M'), hours)

        # Save todays data in the database file
        self.end_time_HH_MM = time.strftime('%H:%M')
        hours = str(round(self.session_count + (1-self.remaining/self.INTERVAL), 1))
        save_workday_data(self.start_time_HH_MM, self.end_time_HH_MM, hours)

        # Destroy window
        self.root.destroy()


#### HELPER FUNCTIONS
def save_workday_data(start_time, end_time, hours):
    '''Create a new workday record in the datebase file.'''
    
    # Connect and save the new workday record
    conn = sqlite3.connect("data.sqlite3", isolation_level=None)
    conn.execute(f"INSERT INTO 'workdays' (date, start_time, end_time, hours) VALUES ('{datetime.date(datetime.today())}', '{start_time}', '{end_time}', {hours})")

def save_workblock_data(start_time, end_time, hours):
    '''Create a new workblock record in the datebase file.'''
    
    # Connect and save the new workdayblock record
    conn = sqlite3.connect("data.sqlite3", isolation_level=None)
    conn.execute(f"INSERT INTO 'workblocks' (date, start_time, end_time, hours) VALUES ('{datetime.date(datetime.today())}', '{start_time}', '{end_time}', {hours})")

def create_database():
    '''Creates the database file in case it does not already exist.'''

    # Connect and create tables
    conn = sqlite3.connect("data.sqlite3", isolation_level=None)
    conn.execute("CREATE TABLE IF NOT EXISTS 'workdays' (date STR DEFAULT NULL, start_time STR NOT NULL, end_time STR NOT NULL, hours REAL NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS 'workblocks' (date STR DEFAULT NULL, start_time STR NOT NULL, end_time STR NOT NULL, hours REAL NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS 'constants' (variable STR DEFAULT NULL PRIMARY KEY, value REAL DEFAULT NULL);")
    
    # Insert constants into the constants table
    try:
        conn.execute("INSERT INTO 'constants' (variable, value) VALUES ('WORKDAY_HOURS', 5);")
    except: pass


#### MAIN PROGRAM INITIATOR (i.e. start the loop when the script is run)
if __name__ == "__main__":
    root = tk.Tk()
    app = WorkClockApp(root)
    root.mainloop()
