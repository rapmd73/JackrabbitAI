# Section 1 - Non-Technical Description

This program checks how much free space is available on a given location (a folder, mount point, or drive) and exits with a status that indicates whether the available space is below a specified minimum amount in gigabytes; it prints a short usage message when run without the required arguments.

# Section 2 - Technical Analysis

The program is a small command-line utility written in Python 3. It imports the standard sys and os modules and defines a function check_drive_space(path, min_gb) that determines whether the available free space at the filesystem containing path is less than a provided threshold in gigabytes.

Inside check_drive_space:
- It calls os.statvfs(path) to retrieve filesystem statistics for the filesystem that contains the given path. That call returns an object with numeric fields describing block counts and sizes.
- It computes available_bytes by multiplying stats.f_bavail (the number of free blocks available to non-superuser) by stats.f_frsize (the fragment size / preferred file system block size). This yields the available space in bytes that ordinary users can use.
- It converts available_bytes to gigabytes by dividing by 1024**3 and stores that in available_gb.
- It returns the integer 1 if available_gb is strictly less than the min_gb argument, otherwise it returns 0.

The main() function handles command-line interaction:
- It checks the length of sys.argv. If fewer than three arguments are present (the script name plus two parameters), it prints the usage string "Usage: CheckFreeSpace <path> <min_gb>" to standard output and exits the process with status code 1.
- If two arguments are provided, it takes the first argument after the script name as path (sys.argv[1]) and converts the second argument (sys.argv[2]) to a floating-point number assigned to min_gb.
- It calls check_drive_space(path, min_gb) and stores the returned value in result.
- It calls sys.exit(result), causing the process to terminate with the integer returned by check_drive_space as the exit code.

When the script is executed directly (if __name__ == '__main__'), main() is invoked. Observable behaviors therefore include printing a usage message and exiting with status 1 when arguments are missing, and otherwise exiting with status 0 when available free space is greater than or equal to the specified minimum in gigabytes or exiting with status 1 when the available free space is less than the specified minimum. The program does not produce other output in the normal code path.
