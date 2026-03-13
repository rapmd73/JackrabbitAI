# Section 1 - Non-Technical Description

This program reads a set of files from a specified folder and, for each file that is not an image or text-type file and that does not already have a corresponding ".md" file, sends the file contents together with a provided role/instruction to an AI agent, receives the agent's reply, and writes that reply into a new ".md" file alongside the original file.

# Section 2 - Technical Analysis

The script begins by adding a specific directory to the Python module search path and importing several standard modules (sys, os, select, copy, json) and three local modules (CoreFunctions as CF, FileFunctions as FF, AIFunctions as AI). It defines a set SKIP_EXT containing common image and text file extensions that the script will ignore.

When executed, main() copies the command-line arguments into args and initializes several flags and numeric variables: ResetMemory=True, SaveMemory=False, NoMemory=True, and maxresp=0. It checks that at least two additional command-line arguments were supplied; if not, it prints an error message and exits. It then reads three environment variables (JRAIengine, JRAImodel, JRAItokens) into engine, model, and mt respectively, converting mt to an integer. persona is set to None.

The script interprets the first command-line argument after the program name as role and the second as dirname. It verifies that the dirname argument points to a directory; if not, it prints an error message and exits.

For the role argument the code checks whether it starts with '@' or '/'. If so, it treats role as a filename. If it starts with '@', the leading '@' is stripped before using the remainder as the filename. If that file exists, it reads its contents using FF.ReadFile, then replaces newline characters with the literal two-character sequence backslash-n and similarly replaces single quotes with the two-character sequence '' (two single quotes). The transformed file contents become the role string. If the role filename does not exist, the program prints "Role file not found" and exits. If the role argument did not start with '@' or '/', the role variable remains whatever text was passed on the command line.

An AI agent object is created by calling AI.Agent with parameters engine, model, maxtokens=mt, persona, reset=ResetMemory, save=SaveMemory, isolation=NoMemory, and maxrespsize=maxresp. The code comments note a difference between a model and an agent being a loop, but otherwise simply instantiates the agent.

The program then iterates over entries in the specified directory using os.listdir(dirname). For each entry name, it builds the full path and continues to the next entry if the path is not a regular file. It determines the file extension by splitting on the last dot; if there is no dot the extension is the empty string. If the extension (in lowercase) is in SKIP_EXT, the file is skipped.

For files that pass these checks, the script constructs a new filename mdfile by appending ".md" to the original path. If that .md file already exists, the original file is skipped. Otherwise, the script prints the path of the file being processed.

It reads the original file contents via FF.ReadFile(path), then replaces newline characters with the literal backslash-n sequence and replaces single quotes with two single quotes, storing the result in a variable named input. It then calls agent.Response with a string composed of the role, two line breaks, and the transformed input. It collects the returned response.

If response is None or the agent's AIError attribute is True, the script checks if a non-None response exists and, if so, prints an error message using agent.stop and the response; then it continues to the next file without writing output. If the response is valid (non-None and AIError is False), the script strips leading and trailing whitespace from the response and passes it to CF.DecodeUnicode, storing the decoded result in decoded.

Finally, the decoded string is written to the mdfile path using FF.WriteFile(mdfile, decoded). The process repeats for every file in the directory that meets the selection criteria.

When the script is run directly as a program (if __name__ == '__main__'), it calls main() to execute the described behavior.