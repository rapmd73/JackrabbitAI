#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit AI
# 2024 Copyright © Robert APM Darin
# All rights reserved unconditionally.

import sys
import functools
import inspect
import traceback
import time

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

@function_stdout('TestDecorators.log')
@function_timer
@function_trapper(0)
def TestDecorators(a,b):
    return a/b

if __name__=='__main__':
    print(TestDecorators(5,3))
    print(TestDecorators(5,0))
