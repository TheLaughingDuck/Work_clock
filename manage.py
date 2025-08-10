'''
This script is here to manage administrative tasks for the Work clock.

This includes changing the workday length and creating data figures.

Just run this file, and interact with the user interface.
'''


#### DEPENDENCIES
import sqlite3
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


#### MAIN UI PROGRAM LOOP
def main():
    # CREATE THE DATABASE file if it does not already exist.
    conn = sqlite3.connect("data.sqlite3", isolation_level=None)
    conn.execute("CREATE TABLE IF NOT EXISTS 'workdays' (date STR DEFAULT NULL, start_time STR NOT NULL, end_time STR NOT NULL, hours REAL NOT NULL);")
    conn.execute("CREATE TABLE IF NOT EXISTS 'workblocks' (date STR DEFAULT NULL, start_time STR NOT NULL, end_time STR NOT NULL, hours REAL NOT NULL);")
    conn.execute("CREATE TABLE IF NOT EXISTS 'constants' (variable STR DEFAULT NULL PRIMARY KEY, value REAL DEFAULT NULL);")
    
    try:
        conn.execute("INSERT INTO 'constants' (variable, value) VALUES ('WORKDAY_HOURS', 5);")
    except: pass

    # Loop while user issues commands
    while True:
        print("\nWhat would you like to do?")
        inp = input(">>")

        if inp in ["save", "data"]:
            #print("In what format do you want the data? As images (.png), or csv (.txt) files?")
            #inp = input("(\"img\" or \"txt\") >>")

            save_data(frmt="img")
            save_data(frmt="csv")

            print("The data was saved into \"./data/\"\n")

            # If I want the program to only save into one format
            # if inp == "img": save_data(frmt="img")
            # if inp == "txt": save_data(frmt="txt")

            continue
        
        if inp == "constant":
            pass
            continue
        
        if inp == "exit":
            exit()

        if inp == "help":
            help()
            continue

        else:
            print("Unknown command.\n")


#### HELPER FUNCTIONS
def help():
    '''Show the available commands to the user.'''
    print("\nThese are the available commands:")
    print("\tsave: Save data as either .png or in .txt files.")
    print("\tconstant: Change the value of a constant.")
    print("\texit: Close the Work Clock manager.")
    print("\thelp: Show this message.\n")


def save_data(frmt:str):
    '''Save the data as either .png or .txt'''
    conn = sqlite3.connect("data.sqlite3", isolation_level=None)
    workdays = conn.execute("SELECT * FROM 'workdays' WHERE date IS NOT NULL").fetchall()
    workblocks = conn.execute("SELECT * FROM 'workblocks'").fetchall()

    WORKDAY_HOURS = conn.execute("SELECT value FROM 'constants' WHERE variable = 'WORKDAY_HOURS'").fetchall()[0]

    if frmt == "img":
        ### Create and save WORKDAYS figure
        dates = [day[0] for day in workdays]
        hours = [day[3] for day in workdays]
        plt.plot(dates, hours)
        plt.xticks(rotation=45)
        plt.title("Total hours worked")
        plt.xlabel("Observation index (corresponds to date)")
        plt.ylabel("Hours")
        plt.hlines(y=WORKDAY_HOURS, xmin=0, xmax=len(hours), colors="grey", linestyles="--")
        plt.savefig("workdays.png")

        
        ### Create and save WORKBLOCKS figure

        # MAKE A DICT with a key for every minute of the day. The value is the number of times a workblock overlaps that specific minute.
        minutes = {}
        start_hour, end_hour = 6, 18
        for h in range(start_hour, end_hour):
            # Change e.g. hour "1" to hour "01".
            if 0 <= h and h <= 9:
                h = "0" + str(h)

            for m in range(0, 60):            
                # Change e.g. minute "1" to minute "01".
                if 0 <= m and m <= 9:
                    m = "0" + str(m)

                minutes[f"{h}:{m}"] = 0
        

        # CYCLE THROUGH THE DATA and extract the information
        for block in workblocks:
            # Take the start and end strings, like "07:03" and "16:56", and
            # create a list of all the minutes from start to stop, i.e. ["07:03", "07:04", "07:05", ..., "16:54", "16:55", "16:56"]
            mins = pd.date_range(block[1], block[2], freq="1min").strftime('%H:%M').tolist()
            
            for m in mins:
                minutes[m] += 1

        plt.plot(minutes.keys(), minutes.values())
        plt.title("Distribution of work throughout the day")
        plt.xlabel("Time")
        plt.ylabel("Frequency")
        plt.xticks([i*60 for i in range(end_hour-start_hour)], pd.date_range(list(minutes.keys())[0], list(minutes.keys())[-1], freq="1h").strftime('%H:%M').tolist(), rotation=45)
        plt.savefig("workblocks.png")

    # Save as .txt or .csv
    elif frmt in ["txt", "csv"]:
        with open("workdays."+frmt, "w") as f:
            f.write("date, start_time, end_time, hours\n")
            for line in workdays: f.write(", ".join(str(s) for s in line) + "\n")
        
        with open("workblocks."+frmt, "w") as f:
            f.write("date, start_time, end_time, hours\n")
            for line in workblocks: f.write(", ".join(str(s) for s in line) + "\n")


#### MAIN PROGRAM LOOP INITIATOR (i.e. start the loop when the script is run)
if __name__ == "__main__":
    main()