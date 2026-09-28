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
Run the python script in the actuator optimization directory to obtain optimal gearbox parameters for all motors:
```
python best_gearbox.py
```
## 3. Stage 2: Co-Design Optimization: 
Run the python script in the components directory:

```
python cmaes.py
```
