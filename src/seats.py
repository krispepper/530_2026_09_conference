# Purpose: Calculate available seats for a conference.
# Author: Priya Vaghela.
# AI assistance: ChatGPT helped draft this code.

def calculate_remaining_seats(capacity, active_registrations):
    """Return available seats, with zero when full or over capacity."""
    if capacity < 0 or active_registrations < 0:
        raise ValueError("Capacity and registration count cannot be negative.")

    return max(0, capacity - active_registrations)
