# Section 1 - Non-Technical Description

This program takes a selected AI provider and model, some settings, a persona, and instructions, optionally reads additional input and an instruction file, then starts an AI agent with those settings and prints the agent's generated response.

# Section 2 - Technical Analysis

The script begins by extending the module search path and importing standard libraries (sys, os, select, copy, json) plus four project modules: DecoratorFunctions (aliased DF), CoreFunctions (CF), FileFunctions (FF), and AIFunctions (AI). Two functions are defined and wrapped with decorators from DF: CheckArgs and main.

CheckArgs(arg, inlist) lowercases its single argument and then iterates through the items of inlist, lowercasing each item in turn; it returns True if any item lowercased equals the lowercased arg, otherwise False. This helper is used to test for presence of option tokens in an argument list in a case-insensitive way.

main() copies command-line arguments from sys.argv into args and initializes several control variables: ResetMemory (False), SaveMemory (True), NoMemory (False), and maxresp (0). It then inspects args for several option tokens:

- If '-maxrespsize' appears, it removes that token and reads the next element (at the same index) as an integer to set maxresp, then removes that element from args.
- If '-isolation' appears, it sets NoMemory to True and removes the token from args.
- If '-reset' appears, it sets ResetMemory to True and removes the token from args.
- If '-nomemory' appears, it sets SaveMemory to False and removes the token from args.

After processing options, main() checks that args has more than five entries (meaning the script name plus at least five other required arguments). If not present, it prints an error message and exits.

If there are enough arguments, it assigns positional parameters from args:

- engine is taken from args[1]; if engine equals 'default' (case-insensitive), it replaces engine with the environment variable JRAIengine.
- model is taken from args[2]; if model equals 'default', it uses the environment variable JRAImodel.
- mt is taken from args[3]; if mt equals 'default', it obtains JRAItokens from the environment and converts it to an int; otherwise mt is converted to int from the string.
- persona is taken from args[4].
- role is taken from args[5].

The code treats role as the instruction text. If role begins with '@' or with '/', it interprets role as a file reference: it strips the leading '@' if present to form a filename, checks for the file's existence, and if found reads it via FF.ReadFile. The file contents are then transformed by replacing newline characters with the two-character sequence '\n' and by replacing single-quote characters with two single quotes (''), then assigned back to role. If the indicated file does not exist, the script prints "Role file not found" and exits.

The script then prepares an input string. It calls CF.IsSTDIN(); if that returns True, the script reads all text from standard input, replaces actual newline characters with the two-character sequence '\n', replaces single-quote characters with two single quotes, and stores that in input. If CF.IsSTDIN() is False, input remains the empty string.

Next, the script constructs an AI.Agent object by calling AI.Agent with keyword arguments: engine, model, maxtokens (mt), persona, reset (ResetMemory), save (SaveMemory), isolation (NoMemory), and maxrespsize (maxresp). It then calls agent.Response with a single string composed of role, two newline characters, then the input string: role + '\n\n' + input. The returned value from agent.Response is stored in response and printed to standard output.

Finally, the module-level guard calls main() when the script is executed as a program. Overall behavior: parse options and required positional arguments, optionally load role text from a file, optionally read standard-input data, instantiate an AI agent with the provided settings, request a response using the role and input combined, and print the agent's response.
