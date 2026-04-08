#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Jackrabit AI
# 2021-2026 Copyright © Robert APM Darin
# All rights reserved unconditionally.

import sys
import os
import signal
import psutil

# Get the original priority of the program at start up.

MasterNice=os.getpriority(os.PRIO_PROCESS,0)

# Signal Interceptor for critical areas

# This is a contorted and twisted hot mess as the multiprocessor package
# parent_process() does NOT funtion properly for identifying the parent
# process. There are MANY other headaches here as well. if the parent is INIT,
# all hell breaks loose and things go south real quick. Extra care MUST BE and
# IS taken to stay away from INIT.

class SignalInterceptor():
    def __init__(self,Log=None,Ignore=False):
        # Signals not to trap, list(signal.Signals)
        noTrap=[signal.SIGCHLD,signal.SIGCONT,signal.SIGTSTP,signal.SIGWINCH]

        self.parent_id=os.getpid()
        self.critical=False
        self.IsParent=True
        self.IsChild=False
        self.original={}
        self.triggered={}
        self.Log=Log

        # Set all signals to myself.

        for sig in signal.valid_signals():
            self.triggered[sig]=False
            try:
                self.original[sig]=signal.getsignal(sig)
                if not Ignore:
                    if sig not in noTrap:
                        signal.signal(sig,self.ProcessSignal)
                else:
                    # Ignore and use SafeExit as alternative
                    signal.signal(sig,signal.SIG_IGN)
            except:
                pass

        # Parent gets task of zombie watch
        signal.signal(signal.SIGCHLD,self.SignalChild)

    # For use with Jackrabbit Relay

    def SetLog(self,Log=None):
        self.Log=Log

    # If a logging has ben set, use it. Otherwise, just print to screen.

    def ShowSignalMessage(self,lm):
        if self.Log!=None:
            self.Log.Write(lm)
        else:
            print(lm)

    # Exit the program. If parent, exit child processes. If Child, signal
    # siblings and parent

    def SignalInterrupt(self,signal_num):
        mypid=os.getpid()
        self.ShowSignalMessage(f'Parent: {self.parent_id} self: {mypid}')

        parent=psutil.Process(self.parent_id)
        nChildren=len(parent.children(recursive=False))

        # Only parent takes to children
        if self.parent_id==mypid and nChildren>0:
            for child in parent.children(recursive=False):
                if child.pid!=mypid:
                    self.ShowSignalMessage(f'Signaling child: {child.pid}')
                    # send signal to children
                    os.kill(child.pid,2)

        # Don't touch INIT. Child tells parent there is a problem
        if self.parent_id!=1 and self.parent_id!=mypid:
            self.ShowSignalMessage(f'Signal parent: {self.parent_id}')
            os.kill(self.parent_id,2)

        # Shut it all down
        if self.parent_id==mypid and self.IsParent and nChildren>0:
            self.ShowSignalMessage(f'Exiting parent: {mypid}')
        elif self.parent_id==mypid and self.IsChild:
            self.ShowSignalMessage(f'Exiting child: {mypid}')
        else:
            self.ShowSignalMessage(f'Exiting self: {mypid}')
        os.kill(mypid,9)

    # Signal handler for child process exit

    def SignalChild(self,signum,frame):
        try:
            # Check if any child processes have exited
            pid, exit_code=os.waitpid(-1,os.WNOHANG)
        except:
            pass

    # We received a signal, process it.

    def ProcessSignal(self,signum,frame):
        self.ShowSignalMessage(f'Interceptor Signal: {signum} In Critical: {self.critical}')
        self.triggered[signum]=True
        if self.critical==False:
            self.SafeExit()

    # Force reset all signal statess

    def ResetSignals(self):
        for sig in signal.valid_signals():
            self.triggered[sig]=False

    # Restore the original signal handlers

    def RestoreOriginalSignals(self):
        for sig in signal.valid_signals():
            try:
                signal.signal(sig,self.original[sig])
            except:
                pass

    # Ignore all signals, for child process

    def IgnoreSignals(self):
        for sig in signal.valid_signals():
            try:
                signal.signal(sig,signal.SIG_IGN)
            except:
                pass

    # Has a single signal been triggered?

    def Triggered(self,signum):
        return self.triggered[signum]

    # Has ANY supported signal been triggered?

    def AnyTriggered(self):
        for sig in signal.valid_signals():
            if self.triggered[sig]==True:
                return True
        return False

    # A safe way to exit the program is it is not in a critical situation.

    def SafeExit(self,now=False):
        self.SignalChild(None,None)
        for sig in signal.valid_signals():
            if (self.triggered[sig]==True and self.critical==False) or now==True:
                if now==True:
                    sig=9
                self.SignalInterrupt(sig)

    # Set whether we are entering a critical area where signals will be ignored, like writing file data.

    def Critical(self,IsCrit=False):
        # Check is there is a trigger. If a signal is triggered, safely exit BEFORE critical event
        if IsCrit==True and self.critical==False and self.AnyTriggered()==True:
            self.SafeExit()
        self.critical=IsCrit

    # Return the number of child processes. Needed for large lists of tasks to be completed.

    def GetChildren(self):
        self.SignalChild(None,None)
        parent=psutil.Process(self.parent_id)
        return len(parent.children(recursive=False))

    # Crude way to tell if this process or function is a child or the parent

    def WhoAmI(self):
        if self.IsParent:
            return "Parent"
        elif self.IsChild:
            return "Child"
        return "Orphan"

    # Very simple multiprocessing methodology.

        if args==None:
            args=[]
        if kwargs==None:
            kwargs={}

        pid=os.fork()
        if pid==0:
            self.IsParent=False
            self.IsChild=True
            self.IgnoreSignals()
            # Child process
            try:
                # Call the function with the provided arguments
                func(*args, **kwargs)
                sys.exit(0)
            except Exception as e:
                # Handle child process error
                sys.exit(1)

        self.SignalChild(None,None)
        return pid

###
### End of module
###

