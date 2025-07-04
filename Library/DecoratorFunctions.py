#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit AI
# 2024-2025 Copyright © Robert APM Darin
# All rights reserved unconditionally.

# This Python code is designed to enhance the functionality of other functions
# by adding useful features like logging, timing, and error handling. It
# achieves this through the use of decorators, which are special functions that
# modify the behavior of other functions without changing their code directly.

# The first part of the code defines a class called `PrintRedirector`. This
# class acts as a manager for redirecting the standard output of a program,
# which is typically what you see printed on the screen, to a file instead.
# This is particularly useful for logging messages or results to a file for
# later review. When you use this class, it ensures that any print statements
# within a specific block of code are written to a designated file rather than
# displayed on the console.

# Following this, the code introduces several decorators. The first decorator,
# `function_stdout`, is designed to redirect the output of a function to a log
# file. It can be applied to functions in two ways: either by specifying a log
# file name or by using a default log file named after the script itself. This
# decorator uses the `PrintRedirector` class to manage the redirection of
# output.

# Another decorator, `function_timer`, measures how long a function takes to
# execute and prints the duration. It works for both regular functions and
# asynchronous functions, which are functions that can run concurrently and are
# often used in tasks like network requests or file operations. This decorator
# helps in profiling code to understand its performance.

# The `function_trapper` decorator is focused on error handling. It catches any
# errors that occur within a function, logs the error details, and returns a
# predefined result instead of letting the error crash the program. This is
# crucial for making programs more robust and capable of handling unexpected
# issues gracefully.

# Finally, the code includes a testing function, `TestDecorators`, which is a
# simple function that divides two numbers. This function is decorated with
# `function_stdout`, `function_timer`, and `function_trapper`. When the script
# is run, it tests this function with two sets of inputs: one that works (5
# divided by 3) and one that causes an error (5 divided by 0). This
# demonstrates how the decorators log the output, measure the execution time,
# and handle the error, respectively.

import sys
import functools
import inspect
import traceback
import time

# The `PrintRedirector` class is a context manager that redirects the standard
# output (`sys.stdout`) to a specified file, allowing print statements to be
# logged to a file instead of being displayed on the console. When initialized,
# it sets the output file to either a provided file name or a default log file
# named after the current script with a `.log` extension. Upon entering the
# context, it opens the file in append mode and redirects `sys.stdout` to it,
# and upon exiting the context, it restores the original `sys.stdout` and
# closes the file object, ensuring that print statements within the context are
# written to the log file.

class PrintRedirector:
    def __init__(self, file=None):
        self.file = file if file else sys.argv[0] + ".log"
        self.original_stdout = sys.stdout

    def __enter__(self):
        self.file_obj = open(self.file, "a", encoding="utf-8")
        sys.stdout = self.file_obj
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        self.file_obj.close()

###
### Special functions/Decorators
###

# The `function_stdout` function is a decorator that redirects the standard
# output (stdout) of a given function to a specified log file. It can be used
# in two ways: as a decorator with no arguments (`@function_stdout`), in which
# case it will log output to a file named after the script with a `.log`
# extension, or as a decorator with a file name argument
# (`@function_stdout('logfile.log')`), allowing for custom log file
# specification. In both cases, it utilizes a helper function `stdout_helper`
# to handle the actual redirection of stdout.

def function_stdout(func_or_file=None):
    if callable(func_or_file):  # Case: Used as @function_redirect
        func = func_or_file
        file = sys.argv[0] + ".log"
        return stdout_helper(func, file)
    else:  # Case: Used as @function_redirect('logfile.log')
        file = func_or_file
        def decorator(func):
            return stdout_helper(func, file)
        return decorator

# The `stdout_helper` function is a decorator factory that redirects the
# standard output of a given function to a specified file. It checks if the
# input function is a coroutine using `inspect.iscoroutinefunction`, and
# returns either an asynchronous or synchronous wrapper function accordingly.
# The wrapper functions use the `PrintRedirector` context manager to
# temporarily redirect the standard output to the specified file while
# executing the original function, ensuring that any print statements within
# the function write to the file instead of the console. The `functools.wraps`
# decorator is used to preserve the original function's metadata, such as its
# name and docstring, in the wrapper functions.

def stdout_helper(func, file):
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with PrintRedirector(file):
                return await func(*args, **kwargs)
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with PrintRedirector(file):
                return func(*args, **kwargs)
        return sync_wrapper

# The `function_timer` decorator measures and prints the execution time of
# both synchronous and asynchronous functions. For synchronous functions,
# it records the start and end times, calculates the elapsed duration, and
# outputs the time taken. For asynchronous functions, it uses the same
# approach but accommodates `await` for proper timing. This decorator helps
# in profiling and performance monitoring by providing precise timing
# information for each wrapped function.

def function_timer(func):
    @functools.wraps(func)
    def sync_timer(*args, **kwargs):
        start_time=time.perf_counter()
        result=func(*args, **kwargs)
        end_time=time.perf_counter()
        elapsed_time=end_time - start_time
        print(f"{func.__name__}: {elapsed_time:.6f} seconds")
        return result

    @functools.wraps(func)
    async def async_timer(*args, **kwargs):
        start_time=time.perf_counter()
        result=await func(*args, **kwargs)
        end_time=time.perf_counter()
        elapsed_time=end_time - start_time
        print(f"{func.__name__}: {elapsed_time:.6f} seconds")
        return result

    if inspect.iscoroutinefunction(func):
        return async_timer
    return sync_timer

# The `function_trapper` is a versatile decorator that wraps both
# synchronous and asynchronous functions to handle exceptions gracefully.
# When a wrapped function encounters an error, it logs the error details,
# including the function name and the line number where the error occurred,
# and then returns a predefined fallback result. This decorator ensures
# robust error handling while maintaining flexibility for both async and
# sync functions.

def function_trapper(failed_result=None):
    def decorator(func):
        if inspect.iscoroutinefunction(func):  # Handle async functions
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as err:
                    tb=traceback.extract_tb(err.__traceback__)
                    errline=tb[-1].lineno if tb else 'Unknown'
                    print(f"{func.__name__}/{errline}: {err}")
                    return failed_result
            return async_wrapper
        else:  # Handle sync functions
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as err:
                    tb=traceback.extract_tb(err.__traceback__)
                    errline=tb[-1].lineno if tb else 'Unknown'
                    print(f"{func.__name__}/{errline}: {err}")
                    return failed_result
            return sync_wrapper

    # Handle decorator usage with or without parentheses
    if callable(failed_result):  # Used without parentheses
        return decorator(failed_result)
    return decorator

###
### Testing function
###

# The `TestDecorators` function is a simple division operation that takes two
# parameters, `a` and `b`, and returns their quotient. This function is
# decorated with three decorators: `@function_stdout`, which logs the
# function's output to a file named 'TestDecorators.log'; `@function_timer`,
# which times the execution of the function; and `@function_trapper(0)`, which
# traps and handles exceptions, allowing the program to continue running even
# if an error occurs, such as division by zero. When called from the main
# program, the function is tested with two sets of inputs: (5, 3) and (5, 0),
# demonstrating its ability to handle both valid and invalid division
# operations.

@function_stdout('TestDecorators.log')
@function_timer
@function_trapper(0)
def TestDecorators(a,b):
    return a/b

if __name__=='__main__':
    print(TestDecorators(5,3))
    print(TestDecorators(5,0))
