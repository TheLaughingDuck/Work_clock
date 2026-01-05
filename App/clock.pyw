'''
The main script of the Work Clock. Run this script at the beginning of the day to begin
tracking work sessions.
'''

# DEPENDENCIES
import tkinter as tk
import time
from datetime import datetime
import sqlite3
from manage import save_data, create_database
import sys
import math
from datetime import datetime

#### MAIN PROGRAM
class WorkClockApp:
    '''A class that manages the running of the clock.'''

    # CONSTANTS
    GUI_WIDTH = 200
    GUI_HEIGHT = 60
    INTERVAL_SECONDS = 3600 # Adjustable mostly for debugging reasons. The program behaves kind of weird if this is not 3600.

    def __init__(self, root):
        '''Initialize the WorkClockApp.'''

        # Load customizeable constants from the database
        create_database()
        conn = sqlite3.connect("data.sqlite3", isolation_level=None)
        self.WORKDAY_HOURS = conn.execute("SELECT value FROM 'constants' WHERE variable = 'WORKDAY_HOURS'").fetchall()[0][0]

        self.WORKDAY_SECONDS = self.WORKDAY_HOURS * self.INTERVAL_SECONDS

        # Set up widget window
        self.root = root
        self.root.title("WorkClock")
        self.root.geometry(f"{self.GUI_WIDTH}x{self.GUI_HEIGHT+30+23+23}") # Extra room for additional info.
        self.root.attributes('-topmost', True)
        self.root.resizable(True, True)#(False, False)

        self.canvas = tk.Canvas(root, width=self.GUI_WIDTH, height=self.GUI_HEIGHT, bg="white", highlightthickness=0)
        self.canvas.pack()

        # Configure progress bar size
        self.padding = 10
        self.bar_width = 45
        self.bar_height = self.GUI_WIDTH - 2 * self.padding

        # Set up labels
        self.completion_label = tk.Label(root, text="Workday completion: 0 %", font=("Helvetica", 12))
        self.completion_label.pack()

        self.remaining_time_label = tk.Label(root, text="Est. rem. time: 300 min.", font=("Helvetica", 12))
        self.remaining_time_label.pack()

        self.finish_time_label = tk.Label(root, text="Between 00:00 and 00:00", font=("Helvetica", 12))
        self.finish_time_label.pack()

        # Create a label with a little list of the variable values
        variables = conn.execute("SELECT * FROM 'constants'").fetchall()
        variables = [f"{var}: {val}" for var, val in variables]
        variables = "\n\nVariables:\n" + "\n".join(variables)
        self.variable_label = tk.Label(root, text=variables, font=("Helvetica", 12))
        self.variable_label.pack()

        # START RUNNING the Clock
        self.running = True
        self.start_time_unix = time.time()
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
        # Remove current progress bar
        self.canvas.delete("progress")
        
        # Compute time information
        elapsed = (time.time() - self.start_time) + self.elapsed_time if self.running else self.elapsed_time
        self.remaining = max(self.INTERVAL_SECONDS - elapsed, 0)  # 1500 seconds = 25 minutes, 3600 seconds = 60 minutes
        proportion_left = 1-(elapsed / self.INTERVAL_SECONDS)

        # If still running, update the progress bar
        if self.remaining > 0:
            self.canvas.create_rectangle(self.padding, self.padding, self.padding + (1-proportion_left) * self.bar_height, self.padding + self.bar_width, fill="darkred", width=2, tags="progress")
            
            # Show completion percentage
            completion_percentage = math.floor(100 * (self.session_count * self.INTERVAL_SECONDS + elapsed) / (self.WORKDAY_SECONDS))
            self.completion_label.config(text=f"Workday completion: {completion_percentage} %")

            # Estimate remaining time
            elapsed_study_seconds = (self.session_count * self.INTERVAL_SECONDS + elapsed)            
            estimated_remaining_seconds = (self.WORKDAY_SECONDS - elapsed_study_seconds) * (time.time() - self.start_time_unix) / (0.0000001+elapsed_study_seconds)
            estimated_remaining_minutes = math.ceil(estimated_remaining_seconds/60)
            self.remaining_time_label.config(text=f"Est. rem. time: {estimated_remaining_minutes} min.")

            # Estimate time of completion
            best_possible_finish_time = datetime.fromtimestamp(time.time() + (self.WORKDAY_SECONDS - elapsed_study_seconds)).strftime("%H:%M")
            estimated_finish_time = datetime.fromtimestamp(time.time() + estimated_remaining_seconds).strftime("%H:%M")
            self.finish_time_label.config(text=f"Between {best_possible_finish_time} and {estimated_finish_time}")


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
            hours = str(round((time.time() - self.workblock_start) / 3600, 2)) # For compatibility reasons, keep this as hours, even if an interval length other than hour is used above.
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
            hours = str(round((time.time() - self.workblock_start) / 3600, 2)) # For compatibility reasons, keep this as hours, even if an interval length other than hour is used above.
            save_workblock_data(self.workblock_start_str, time.strftime('%H:%M'), hours)

        # Save todays data in the database file
        self.end_time_HH_MM = time.strftime('%H:%M')
        hours = str(round(self.session_count + (1-self.remaining / 3600), 1))
        save_workday_data(self.start_time_HH_MM, self.end_time_HH_MM, hours)

        # Save data as img and .csv files
        save_data(frmt="img")
        save_data(frmt="csv")

        # Destroy window
        self.root.destroy()
        sys.exit()


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


#### MAIN PROGRAM INITIATOR (i.e. start the loop when the script is run)
if __name__ == "__main__":
    root = tk.Tk()
    app = WorkClockApp(root)
    root.mainloop()
