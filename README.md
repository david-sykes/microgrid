# microgrid
A tiny repo for simple electricity system modelling. Inspired by Andrej Karpathy's micrograd

# Design decisions to document
1. Minimal libaries
2. Everything as native python objects
3. Timestep treatment
4. Batteries as single net inflow
5. flexible load load windows


## ToDo
- Add timesteps - DONE
- Two node system - DONE
- Add storage - DONE
- Break out demand into it's own thing - DONE
- Debug storage plot and soc calc - DONE
- Fix SOC to be zero at start - DONE
- Make sure timesteps work and document (beginning, end or both) - DONE
- Finish flexible demand
- Build basic UK example with typical day
- Add json output
- Add json input
- Create better visualisation layer using three.js that renders an html infinite canvas page with time slider and graphs of all generation
- Add multi day
- Add national market and redispatch (needs network modes)
- Natural language interface for setting up networks
- Document everything
- Add ramp up and ramp down
