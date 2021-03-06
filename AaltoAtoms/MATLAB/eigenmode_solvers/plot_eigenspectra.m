function plot_eigenspectra(r_min_nm, r_max_nm, r_step_nm)
arguments
    r_min_nm = 4
    r_max_nm = 5
    r_step_nm = 0.5
end

InitializeGlobals('Ag');
global E0;
global ms;
global hbar;

radii = r_min_nm:r_step_nm:r_max_nm;
hmax_vals = 0.1:0.1/(size(radii,2)-1):0.1;
eigs = {};
i = 1;
for r = radii
    disp(r);
    [res_vac, model_vac] = ComputeEigenmodes(r, r, ...
    'plotAll', 1,...
    'HMax', 0.15,...
    'energyRange',100e-3, ...
    'atomPotential', 1, ... 
    'atomRadius', 0.6);
    eigs = [eigs; {r res_vac.Eigenvalues} ];
    i = i+1;
end
writecell(eigs);

end
