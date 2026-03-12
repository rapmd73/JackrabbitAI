# Section 1 - Non-Technical Description

This program removes files from one or more folders that have not been changed for a user-specified number of days, skipping hidden files and certain protected system locations, and then reports how many files were removed from each folder (optionally listing folders even when nothing was deleted).

# Section 2 - Technical Analysis

The script begins by importing standard modules (sys, os, datetime, time) and two local modules, DecoratorFunctions (as DF) and FileFunctions (as FF). It records the current time in seconds into the global variable current_time.

A function DeleteOldFiles(directory, threshold=31*24*60*60) is defined and wrapped with DF.function_trapper (a decorator from the imported module). When called, DeleteOldFiles first checks whether the provided path is an existing directory; if not, it returns 0. It initializes a counter c to zero. It iterates over the names returned by os.listdir(directory). For each name it skips any that start with a dot. It constructs the full path and checks if that path is a regular file (os.path.isfile). For regular files it obtains the file modification time via os.path.getmtime(file_path). It compares the stored global current_time minus the file's modification time to the threshold argument. If the difference is greater than threshold, it attempts to remove the file with os.remove(file_path); on success it increments c. If os.remove raises any exception, it prints a failure message including the filename and exception text. After processing all entries, DeleteOldFiles returns the count c of successfully deleted files.

A main() function, also decorated with DF.function_trapper, defines a list GuardRail containing a set of system directory path prefixes. It initializes two boolean flags: Override and Verbose to False. It scans the command-line arguments (sys.argv[1:]) and if any argument contains '-override-safety' (case-insensitive) it removes that argument from sys.argv and sets Override to True; similarly, if any argument contains '-verbose' it removes that argument and sets Verbose to True.

main then checks whether at least two command-line arguments remain (the script expects a threshold and at least one directory). If fewer than two arguments are present it prints messages indicating missing threshold and directories and exits with status 1.

It parses the first remaining command-line argument as an integer number of days and converts that to seconds (threshold = int(sys.argv[1]) * 24 * 60 * 60). If conversion fails it prints an error and exits. If threshold is less than 1 (days) it prints a message and exits.

For each remaining command-line argument (treated as a directory path) main sets skip to False and iterates the GuardRail list. For each guard entry g, if Override is False and the guard string g is found anywhere within the directory path string d (g in d), it prints "Skipping <d>", sets skip to True, and breaks out of the guard loop. If skip is True it continues to the next directory. Otherwise, it calls DeleteOldFiles(d, threshold=threshold) and captures the returned count c. If c is greater than zero, or if the Verbose flag is True, main prints a formatted line showing the count and the directory path (f'{c:5} {d}').

When the script is executed as the main program (if __name__ == '__main__'), it calls main(), causing the command-line parsing and deletion behavior to run.

In summary, the program accepts a numeric day threshold and one or more directory paths on the command line, optionally accepts flags to override safety checks and enable verbose output, skips protected directories unless overridden, deletes non-hidden regular files older than the threshold based on file modification time (using a globally captured current_time), and prints counts of deleted files per directory.
