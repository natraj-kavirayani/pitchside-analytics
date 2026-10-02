"""Pure functions that turn StatsBomb-shaped frames into what the app shows.

Nothing here fetches data or touches Streamlit: every function takes
DataFrames and returns new ones, without modifying its inputs (sources
may hand the same cached frame to several callers).
"""
