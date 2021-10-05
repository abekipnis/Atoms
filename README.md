# Small Kondo Corrals data analysis
Several scripts within: 

animate_grid
- for reading grid spectra and saving movie file

find_atom_positions
- contains CircCorralData class, main function that analyzes all .dat files in data inventory Excel sheet 

fit_lattice
- script for testing CircCorralData functions (fitting Gaussians to atom positions, fitting circle to corral walls, fitting lattice to atom positions) 

play_latfile
- for converting .LAT files into .wav's for fun 

scattering_model 
- *incomplete* 
- for simulating LDOS rho(r, E) given a set of atom positions and a lattice

Kondo data analysis: 
read_vertfile
- TKinter tool to select files
- Read a spectrum (or a series of spectra) from a .VERT file output by the Createc software
- Perform a fit of a Fano function over the Kondo resonance around a user-chosen range of values
- Get extracted parameters for the Fano resonance
    - linewidth w
    - the center of the Fano lineshape E0
    - the Fano asymmetry parameter q, which can be compared with other values from literature. 
