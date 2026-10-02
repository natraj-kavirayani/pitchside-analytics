"""Pitchside Analytics: explore football matches through StatsBomb open data.

The package is layered so each layer can be tested on its own:

- ``data``: where match data comes from (StatsBomb, or an offline sample),
  behind one ``MatchDataSource`` protocol, plus the column contract the
  rest of the app relies on.
- ``analytics``: pure functions that turn event DataFrames into the
  numbers the app shows. No I/O.
- ``service``: ``MatchService`` composes a data source with the analytics.
- ``viz``: matplotlib charts and HTML tables. No Streamlit dependency.
- ``ui``: the Streamlit front end: theme, motion, sidebar and views.
"""
