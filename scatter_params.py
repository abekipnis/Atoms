# %% codecell
# option-shift-enter to Hydrogen - run cell
import os, scipy
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import optimize
import matplotlib
from AaltoAtoms import CircCorralData, Spec, analyze_data, get_old_Ag_Co_corrals, fit_and_plot_functional_curve
from AaltoAtoms.Kondo_data_analysis.analyze_data import show_current_param_fit_result, plot_radial_width_dependence
from AaltoAtoms import show_waterfall, imshow_dIdV_vs_r
from AaltoAtoms.utils import labellines
from AaltoAtoms.Kondo_data_analysis.analyze_data import basepath
from multiprocessing import Pool
import pickle
from importlib import reload
from scipy.signal import decimate
from matplotlib.colors import LogNorm
from scipy.interpolate import interp2d
from itertools import combinations, repeat
# .dat file and corresponding .VERT file for central Co atom fitting
import data_array
reload(data_array)
from data_array import Co_Co_corrals, Co_Ag_corrals
import pandas as pd

import matplotlib
from AaltoAtoms.utils.particle_in_a_box import get_modes, mstar
# %%

c = Co_Co_corrals[6]

def show_current_param_fit_result(c: corralspectrum) -> None:
    """
    See how current setup for single corralspectrum works for fit.

    Parameters:
        c: corralspectrum
    Returns:
        None
    """

    matplotlib.rcParams.update({'font.size': 10})
    S = Spec(os.path.join(basepath, c.vertfile))
    S.clip_data(c.dataclipmin, c.dataclipmax)

    C = CircCorralData(os.path.join(basepath, c.datfile), c.datfile, c.chan)
    C.occupied = True
    C.corral = True
    C.subtract_plane()
    C.get_region_centroids(percentile=c.height_percentile, edge_cutoff=c.edge_cutoff)
    radius = C.get_corral_radius(1.5, savefig=False, showfig=False)

    S.remove_background(c.fit_order)
    type_fit = c.type_fit if c.type_fit is not None else "default"
    r = S.fit_fano(marker1=c.marker1, marker2=c.marker2,
                   type_fit=type_fit,
                   showfig=True,
                   q_fixed_val=np.nan,
                   actual_radius=radius)
    return r

res = show_current_param_fit_result(c)
# %%
C = CircCorralData(os.path.join(basepath, c.datfile), c.datfile)
C.occupied = True
C.corral = True
C.subtract_plane()
C.get_region_centroids(percentile=97, edge_cutoff=0.01)
radius = C.get_corral_radius(1.5, savefig=False)
2*np.pi*radius/len(C.centroids)
plt.imshow(C.im)
# %%

#
# c = Co_Ag_corrals[6]
#
# S = Spec(os.path.join(basepath, c.vertfile))
# S.clip_data(-25,50)
# S.remove_background(3)
# r = S.fit_fano(marker1=-12, marker2=35, type_fit="default")
#
# C = CircCorralData(os.path.join(basepath, c.datfile), c.datfile, chan=0)
# C.occupied = True
# C.corral = True
# C.subtract_plane()
# C.get_region_centroids(percentile=98, edge_cutoff=0.01)
# radius = C.get_corral_radius(1.5, savefig=False)

# %%
def create_waterfall() -> list:
    """
        Create array with information to plot dIdv for Ag corrals
    """
    dir = r"Y:\labdata\Createc\STMDATA\Ag(111)\2022-03 Co Kondo corrals\04-11 Ag Co"
    wfall = {"A220411.133438.dat": "A220411.134351.L0013.VERT",
            "A220411.141241.dat": "A220411.141923.L0017.VERT",
            "A220411.145437.dat": "A220411.145852.VERT",
            "A220411.153007.dat": "A220411.153513.VERT",
            "A220411.161126.dat": "A220411.161806.L0017.VERT",
            "A220411.165133.dat": "A220411.165336.VERT",
            "A220411.173719.dat": "A220411.174011.VERT",
            "A220411.183528.dat": "A220411.183838.VERT",
            "A220411.193017.dat": "A220411.193232.VERT",
            "A220411.200858.dat": "A220411.201104.VERT",
            "A220411.204552.dat": "A220411.204741.VERT",
            "A220411.215004.dat": "A220411.215940.L0016.VERT",
            #"A220411.222442.dat": "A220411.222845.L0017.VERT",
            #"A220411.233446.dat": "A220411.233625.VERT",
            "A220412.010237.dat": "A220412.010418.VERT"}
    cache = []
    colors = plt.cm.copper(np.linspace(0, 1, len(wfall)))

    for n, dat in enumerate(list(wfall.keys())):
        C = CircCorralData(os.path.join(dir, dat),"")
        C.occupied = True
        C.corral = True
        C.subtract_plane()
        C.get_region_centroids(percentile=99)
        radius = C.get_corral_radius(1.5, savefig=False, showfig=False)

        S = Spec(os.path.join(dir,wfall[dat]))
        norm_val = S.dIdV[0]
        norm_val = S.dIdV[np.argmin(np.abs(7.5-S.bias_mv))]

        #print(wfall[dat])
        #plt.plot(S.dIdV); plt.show()

        cache.append([S.bias_mv, S.dIdV/norm_val + len(wfall.keys())-n*1.05, colors[n], radius])
    return cache

def show_waterfall(cache: list, bias_idx: int=3, dIdV_idx: int =2) -> None:
    """
        Plot the data created by create_waterfall

    Parameters:
        cache: list of [bias, dIdV + offset, color, radius]
        bias_idx:
        dIdV_ idx:

    Returns:
        None
    """
    plt.figure(figsize=(8,8))

    colors = plt.cm.copper(np.linspace(0, 1, len(cache)))

    for n, c in enumerate(cache):
        r = c[3] #c[5].pix_to_nm(c[5].r)
        plt.plot(c[bias_idx], c[dIdV_idx], color=colors[n], linewidth=4.5, label="%1.1lf nm" %r)

    # plt.text(47, cache[0][1][0] + 0.2,"%1.1lf nm" %(np.round(cache[0][3],1))) # 11 nm
    # plt.text(47, cache[len(cache)//2][1][0] - 0.6,"%1.1lf nm" %(np.round(cache[len(cache)//2][3],1)))
    # plt.text(47, cache[-1][1][0] - 0.9,"%1.1lf nm" %(np.round(cache[-1][3],1))) # 3.6 nm
    plt.yticks([])
    plt.xlabel("Bias (mV)")
    plt.ylabel(r"$dI/dV$ (a.u.)")
    plt.gcf().axes[0].tick_params(direction="in")

    xvals = [50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50 ]
    labellines.labelLines(plt.gca().get_lines(), align=False,fontsize=12, xvals=xvals)

    plt.xlim(-80,80)
    plt.xticks([-80, -60, -40, -20, 0, 20, 40, 60, 80])

    # plt.legend()
    plt.savefig(r"C:\Users\kipnisa1\Dropbox\papers-in-progress\Small Kondo corrals\Co-Ag-spectrum-waterfall.pdf")
    plt.savefig(r"C:\Users\kipnisa1\Dropbox\papers-in-progress\Small Kondo corrals\Co-Ag-spectrum-waterfall.png")
    plt.savefig(r"C:\Users\kipnisa1\Dropbox\papers-in-progress\Small Kondo corrals\Co-Ag-spectrum-waterfall.svg")

    plt.show()
# %%
cache = create_waterfall()
matplotlib.rcParams.update({'font.size': 22})
show_waterfall(cache, 0, 1)

if __name__=="__main__":
    matplotlib.rcParams.update({'font.size': 12})


    Co_Co_data_loc = r'C:\Users\kipnisa1\Dropbox\papers-in-progress\Small Kondo corrals\Kondo corrals fit data\Co_Co_data.pickle'
    Co_Ag_data_loc = r'C:\Users\kipnisa1\Dropbox\papers-in-progress\Small Kondo corrals\Kondo corrals fit data\Co_Ag_data.pickle'

    Co_Co_data_loc = r'data\Co_Co_data.pickle'
    Co_Ag_data_loc = r'data\Co_Co_data.pickle'

    def save_data():
        """
        Analyze data defined by corraspectrum arrays in data_array
        Save to location defined in Co_Co_data_loc and Co_Ag_data_loc
        """
        global Co_Co_data
        Co_Co_data = np.array(analyze_data(Co_Co_corrals, showfig=True))
        global Co_Ag_data
        Co_Ag_data = np.array(analyze_data(Co_Ag_corrals, showfig=True))
        Co_Ag_data = list(sorted(Co_Ag_data, key=lambda x: -x[0]))
        Co_Co_data = list(sorted(Co_Co_data, key=lambda x: -x[0]))

        with open(Co_Co_data_loc, "wb") as handle:
            pickle.dump(Co_Co_data, handle, protocol=pickle.HIGHEST_PROTOCOL)

        with open(Co_Ag_data_loc, "wb") as handle:
            pickle.dump(Co_Ag_data, handle, protocol=pickle.HIGHEST_PROTOCOL)

    save_data()
‚‚    def load_data():
        """
        Load data saved in Co_Co_data_loc
        """

        global Co_Co_data
        with open(Co_Co_data_loc, "rb") as handle:
            Co_Co_data = pickle.load(handle)

        global Co_Ag_data
        with open(Co_Ag_data_loc, "rb") as handle:
            Co_Ag_data = pickle.load(handle)

    load_data()


    [plt.plot(c[3], c[2]/c[2][-1]+c[0]) for c in Co_Co_data if len(c[3]) ==502 and c[3][0]==80]
    plt.scatter([c[0] for c in Co_Co_data],  [c[1] for c in Co_Co_data])
    plt.ylim(0, 20)

    atol = 0.2
    radius = 4.5‚
    dataset = Co_Ag_data

    def show_eigenval_and_kondo_spectrum(data: str, interpolate:bool=False):
        imshow_dIdV_vs_r(data, downsample=False,
                        interpolate=interpolate, nm_step=0.1, mV_step=0.1,  norm_mV=-67, norm_to_one=True)
        r = [c[0] for c in data]
        r_range = np.arange(min(r), max(r), 0.1)

        # to get particle in a box eigenmodes analytically
        e0, e1, e2, e3 = get_modes(mstar, 0.067, r_range*1e-9, 4).T

        # or pull them from MATLAB code
        f = r"\\home.org.aalto.fi\kipnisa1\data\Documents\AaltoAtoms\AaltoAtoms\MATLAB_eigenmode_solvers\eigs-0.6nm-20potential.txt"
        data = []
        with open(f, "r") as handle:
            lines = handle.readlines()
            for line in lines:
                ld = line.split(',')
                #ld = [fl(l) for l in ld]
                data.append(ld)

        def convert_float(val):
            try:
                return float(val)
            except ValueError:
                return np.nan

        data = pd.DataFrame(pd.to_numeric(data, errors ='coerce'))
        # plt.plot( data[1].apply(lambda x: convert_float(x))*1e3-67, data[0].astype(float))
        # plt.plot( data[3].apply(lambda x: convert_float(x))*1e3-67, data[0].astype(float))
        # plt.plot( data[4].apply(lambda x: convert_float(x))*1e3-67, data[0].astype(float))
        #
        # plt.plot(e0*1e3, r_range, color="red")
        # plt.plot(e1*1e3, r_range, color="red")
        # plt.plot(e2*1e3, r_range, color="red")
        # plt.plot(e3*1e3, r_range, color="red")

        plt.xlim(-80,80)

        #plt.legend(["Particle-in-a-box eigenmodes"])
    show_eigenval_and_kondo_spectrum(Co_Ag_data, interpolate=True)

    # show_eigenval_and_kondo_spectrum(np.append(Co_Co_data, Co_Ag_data, axis=0), interpolate=False)
    #plt.ylim(2.8,8)
    plt.savefig(r"C:\Users\kipnisa1\Dropbox\papers-in-progress\Small Kondo corrals\interpolated_Co-Ag_corral_spectra.png")
    plt.savefig(r"C:\Users\kipnisa1\Dropbox\papers-in-progress\Small Kondo corrals\interpolated_Co-Ag_corral_spectra.svg")
    plt.savefig(r"C:\Users\kipnisa1\Dropbox\papers-in-progress\Small Kondo corrals\interpolated_Co-Ag_corral_spectra.pdf")

    command = '''start matlab -nosplash -nodesktop -r "cd('Z:\Documents\AaltoAtoms\AaltoAtoms\MATLAB_eigenmode_solvers'); plot_eigenspectra(2,10,1)" -logfile log.txt'''
    os.system(command)

    # investigate_radius_range(5.5, 0.2, Co_Ag_data)
    def investigate_radius_range(radius: float, atol: float, dataset: list):
        # get all the corral data with radius within tol of radius
        d = [c for c in dataset if np.isclose([c[0]], [radius], atol=atol)]

        # show the spectra for these corrals
        [plt.plot(c[3], c[2], label="%d atoms, w=%1.1lf mV" %(len(c[5].centroids), c[1])) for c in d]
        plt.legend()

        lockinampl = [c[4].LockinAmpl for c in d]
        biasvoltage = [c[4].biasVoltage for c in d]
        setpoint_current = [c[4].FBLogiset for c in d]

        return d

    investigate_radius_range(5,0.2, Co_Co_data)
plt.xlim(-20, 20)

    plt.xticks([2,3,4,5,6,7,8])

    AaltoAtoms.utils.visualizations.create_waterfall()
    plt.plot(Co_Co_data[0][3],Co_Co_data[0][2])
    show_waterfall(Co_Co_data, )

    matplotlib.rcParams.update({'font.size': 12})

    plt.scatter([c[0] for c in Co_Ag_data],  [c[1] for c in Co_Ag_data])

    bounds = {
        'Js': (0,2),
        'Jd': (0,2),
        'd1': (-np.pi, np.pi),
        'd2': (-np.pi, np.pi),
        'alpha': (0, 2),
        'A': (0, 20),
        'k': (0,2)
    }

    p0 = {
        'Js': 0.5,
        'Jd': 0.1,
        'd1': -0.27,
        'd2': -0.24,
        'alpha': 0.88,
        'A': 3.2,
        'k': 0.83
    }


    p0 = [p0[l] for l in list(p0.keys())]
    bounds = np.array([bounds[b] for b in list(bounds.keys())]).T

    d = get_old_Ag_Co_corrals(dist_cutoff_nm=0.1)
    all_Co_Ag_data = np.concatenate([np.array(Co_Ag_data)[:,0:2].T, np.array([d.radius, d.w])], axis=-1)

    fig = plt.figure(figsize=(6,6))

    plt.scatter(*all_Co_Ag_data, label="Ag walls")
    plt.scatter(*np.array([c[0:2] for c in Co_Co_data]).T, label="Co walls")
#    all_Co_Ag_data = plot_radial_width_dependence(Co_Ag_data)
    plt.legend()
    kwargs = {"bounds": bounds, "p0": p0, "show_Li_fit": False, "show_isolated_Co": False}


    f = np.concatenate([np.array([c[0:2] for c in Co_Co_data]).T, all_Co_Ag_data], axis=1)
    fit_and_plot_functional_curve(*f,**kwargs)

    plt.gcf().axes[0].tick_params(direction="in")
    plt.xlabel("Corral radius (nm)")
    plt.ylabel("Central Co atom Kondo resonance width (mV)")
    plt.legend(fontsize="small")

    # plt.savefig(r"C:\Users\kipnisa1\Dropbox\papers-in-progress\Small Kondo corrals\Co-Ag-w-r-fit.svg")
    # plt.savefig(r"C:\Users\kipnisa1\Dropbox\papers-in-progress\Small Kondo corrals\Co-Ag-w-r-fit.pdf")
    # plt.savefig(r"C:\Users\kipnisa1\Dropbox\papers-in-progress\Small Kondo corrals\Co-Ag-w-r-fit.png")
    fit_and_plot_functional_curve(*np.array(Co_Ag_data)[:,0:2].T)
