# OpenVSP Hydrofoil Python API

This repository contains Python scripts for parametric hydrofoil modeling and aerodynamic-style analysis in OpenVSP using the Python API. The project focuses on three main tasks:

- generating a hydrofoil geometry model
- running a single VSPAERO analysis case
- performing iterative span-based studies and exporting results

The hydrofoil is modeled as a wing-like lifting surface with a main foil and winglet, using NACA 4-series section parameters. The analysis workflow is designed for fully submerged hydrofoil studies within the assumptions of OpenVSP/VSPAERO.

## Repository Structure

- `hydrofoilgenis_model.py`  
  Creates the parametric hydrofoil geometry and saves it as a `.vsp3` file.

- `hydrofoilgenis_analysis.py`  
  Runs a single-point VSPAERO analysis and extracts aerodynamic results such as lift coefficient, drag terms, and estimated lift/drag forces.

- `hydrofoilgenis_iterativeanalysis.py`  
  Runs an iterative study over multiple span values, compares the results, and exports them to CSV.

## Features

- Parametric hydrofoil geometry generation
- NACA-based section definition
- Main foil + winglet configuration
- Single-case VSPAERO analysis
- Iterative span sweep studies
- CSV export of computed results
- Debug-friendly result extraction workflow

## Notes

This repository treats the hydrofoil as a fully submerged lifting surface and uses OpenVSP/VSPAERO as the main analysis environment. The scripts are intended for conceptual and parametric studies rather than high-fidelity CFD or free-surface simulation.
