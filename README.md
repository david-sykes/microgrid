# microgrid
A tiny repo for simple electricity system modelling. Inspired by Andrej Karpathy's micrograd

# Design decisions to document
1. Minimal libaries
2. Everything as native python objects
3. Timestep treatment
4. Batteries as single net inflow
5. flexible load load windows


To Do
- Handle power -> energy capacities more cleanly (e.g. should we define all capacities in MW or in MWh for that timestep)
- Output to duckdb as well as json