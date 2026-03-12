# Section 1 - Non-Technical Description

This program looks for running programs whose command lines contain a given word or phrase, counts how many such programs are running, and then repeatedly re-checks until that count is not larger than the number of CPU cores on the machine. It prints a short usage message if you don't give it the single required search term.

---

# Section 2 - Technical Analysis

The script is a command-line Python program that requires exactly one argument: a search term. If the argument count is not exactly one, it prints "Usage: <scriptname> <search_term>" and exits with a nonzero status.

The core work is done by the function CountProcess(search_term). That function converts the search term to lowercase, enumerates all system processes via psutil.process_iter(['cmdline']), and attempts to read each process's command-line information from proc.info['cmdline']. For processes where a command-line list is available and not None, it joins the list into a single space-separated string, converts that string to lowercase, and checks whether the lowercase search term appears as a substring of that lowercase command-line string. Each time the substring test succeeds, the function increments a local counter. If psutil raises NoSuchProcess or AccessDenied while examining a process, those exceptions are caught and the loop continues. Finally, CountProcess returns the total count of matching processes.

When run as the main program, it stores the provided argument into term and calls CountProcess(term) once, storing the result in result. Then the program enters a while loop that continues as long as result is greater than os.cpu_count() (the number of CPUs reported by the operating system). Inside the loop the program calls CountProcess(term) again to refresh result, then sleeps for one second before the next check. The loop terminates when the count of matching processes is less than or equal to the number of CPU cores; at that point the script ends without printing further output or returning an explicit exit code.
