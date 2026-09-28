# Five-bar-monoped-optimization

## Pre-requisites
The Following libraries are required: \
`numpy, scipy, matplotlib, cma, pandas`


## Quick Start Guide

## 1. Installation: 
Install the following packages:
```
pip install numpy scipy matplotlib cma pandas
```
## 2. Stage 1: Actuator Optimization: 
All commands below are run from the `actuator_optimization` directory.

### Optimal gearbox for a single motor + gear ratio
```
python actOpt.py <motor> <gearbox> <ratio>
```
* `<motor>`: `U8`, `U10`, `U12`, `MN8014`, `VT8020`, `MAD_M6C12`
* `<gearbox>`: `sspg`, `cpg`, `wpg`, `dspg`
* `<ratio>`: gear ratio, must be > 2

Example:
```
python actOpt.py U8 sspg 6.5
```
Prints the optimal teeth counts, module, and planet count for that motor/gearbox/ratio combination.

### Optimal gearbox across a range of gear ratios
```
python actOpt.py <motor> <gearbox> <ratio_min> <ratio_max> <step>
```
Example:
```
python actOpt.py U8 sspg 4 35 0.1
```
Runs the optimization for every ratio in the range and prints the result for each.

### Best gearbox topology across all motors
Run the python script in the actuator optimization directory to obtain the best gearbox (across SSPG/CPG/WPG/DSPG) for every motor and gear ratio, using the precomputed brute-force results in `results/`:
```
python best_gearbox.py
```
Output is saved to `optimal_gearbox_selection2.csv`.

## 3. Stage 2: Co-Design Optimization: 
Run the corresponding python script in the `components` directory. Each script runs the same CMA-ES trajectory/controller optimization loop, but over a different subset of design variables:

| Script | Case | Optimizes | Fixed |
| --- | --- | --- | --- |
| `cmaes_baseline.py` | Nominal | Jump trajectory + controller gains | Leg link lengths, motor, gear ratio |
| `cmaes_ll.py` | Case A | Leg link lengths + trajectory + controller gains | Motor, gear ratio |
| `cmaes_gear.py` | Case B | Motor + gear ratio + trajectory + controller gains | Leg link lengths |
| `cmaes.py` | Case C | Leg link lengths + motor + gear ratio + trajectory + controller gains (full co-design) | — |
| `cmaes_ctrlfixed.py` | ablation | Leg link lengths + motor + gear ratio | Controller gains |

```
python cmaes.py
```
