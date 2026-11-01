"""Application-wide UI timing: direct user actions remain immediate."""
import customtkinter as ctk


def configure_runtime():
    # CTk otherwise wakes every 30 ms even with a fixed theme and every 100 ms
    # to sample monitor DPI. OS-theme changes can wait 1 s; manual ones cannot.
    ctk.AppearanceModeTracker.update_loop_interval = 1000
    ctk.ScalingTracker.update_loop_interval = 500
