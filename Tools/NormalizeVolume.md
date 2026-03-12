# Section 1 - Non-Technical Description

This program takes several audio files, measures how loud each one is, makes every file as loud as the loudest one among them, stitches them together in order, and writes the combined result to a new audio file.

# Section 2 - Technical Analysis

The script is a command-line Python program that expects at least two arguments after the script name: one or more input WAV file paths followed by a single output WAV file path. If fewer than three command-line arguments are provided (script name + at least one input + output), it prints a usage message and exits with status 1.

It verifies that each input file exists using the operating system path check. For any input path that does not exist, the script prints "Input file missing: <path>" and exits with status 1.

For each existing input file, the program loads the file using pydub.AudioSegment.from_wav (via the helper function load_wav). It computes the loudness of each loaded AudioSegment by reading the dBFS attribute (via get_loudness), producing a list of loudness values in decibels relative to full scale.

The program prints a simple loudness report to standard output: for each input file it prints a line with the loudness value formatted to two decimal places followed by the input file path.

It determines the loudest track by taking the maximum value from the list of loudnesses. Using match_volume, it computes a gain for each audio segment as (target_dBFS - source_audio.dBFS) and applies that gain to the segment with AudioSegment.apply_gain, producing a new list of normalized AudioSegment objects. The target_dBFS used for all segments is the loudest file's dBFS value.

After normalization, the program concatenates the normalized AudioSegment objects in the same order as the input list. It starts from an empty AudioSegment and appends each normalized segment sequentially using the += operator, resulting in one combined AudioSegment containing all audio back-to-back.

Finally, the combined AudioSegment is exported to the output path provided on the command line with format='wav' using AudioSegment.export. After exporting, the script prints two messages: one reporting the output file path ("All input files normalized and merged into: <output>") and one reporting the numeric target loudness ("Target loudness: <value> dBFS" formatted to two decimal places).

The script's behavior is driven entirely by the pydub library's AudioSegment class for loading, measuring loudness (dBFS), applying gain, concatenation, and exporting. The main control flow is in main(), which is invoked when the script is run as the main program.
