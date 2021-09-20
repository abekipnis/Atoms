import createc
import matplotlib.pyplot as plt
import numpy as np
import pdb
from skimage import morphology, measure
from numpy import empty, sqrt, square, meshgrid, linspace, dot, argmax, argmin, reshape, array
from numpy.linalg import norm, pinv, lstsq
from scipy.spatial import distance_matrix
from scipy.optimize import leastsq
from scipy.stats import pearsonr
from dataclasses import dataclass
from multiprocessing import Process, Queue, Array
import multiprocessing
from sklearn.preprocessing import normalize
from math import cos, sin


# DEFINING CONSTANTS
a = 0.409 # nm, lattice constant of silver

d = np.sqrt(6)/4*a # height of triangles
b = np.sqrt(2)*a/2 # width of triangles in nm

dpath = "/Users/akipnis/Desktop/Aalto Atomic Scale Physics/Summer 2021 Corrals Exp data/"

#corral with 14 atoms:
c1 = "Ag 2021-07-29 corral built/Createc2_210730.105015.dat"
c2 = "Ag 2021-08-10 2p5 nm radius/2p5 nm radius pm20mV line spectrum/Createc2_210810.090437.dat"
c3 = "Ag 2021-08-13 3p8 nm radius/Createc2_210813.102220.dat"
c4 = "Ag 2021-08-13 2p5 nm radius/2p5nm radius pm 20mV line spectrum/Createc2_210813.161840.dat"
# image_file = createc.DAT_IMG(dpath + )
# image_file = createc.DAT_IMG(dpath + "Ag 2021-08-10 2p5 nm radius/2p5 nm radius pm20mV line spectrum/Createc2_210810.090437.dat")

def worker(c, v, i, queue, lattice_sites, theta_offset, bbox):
    """
    we only care about the lattice sites that are within bounding box
    defined by atoms arranged in the circle
    """
    x0, y0, x1, y1 = bbox
    xn = v[0] + c.nm_to_pix(np.sqrt(2)*a/2*np.cos(i*2*np.pi/6+theta_offset))
    yn = v[1] + c.nm_to_pix(np.sqrt(2)*a/2*np.sin(i*2*np.pi/6+theta_offset))
    #if xn > 0 and yn > 0 and xn < c.xPix and yn < c.yPix:
    if xn > x0 and yn > y0 and xn < x1 and yn < y1:
        new_site = [xn, yn]
        # in lattice? (i.e. has the site been visited? )
        il = np.any([np.allclose(new_site, l, atol=1e-3) for l in lattice_sites])
        if not il:
            lattice_sites.append(new_site)
            queue.put(new_site) # explore next

@dataclass
class Vector:
    x: float
    y: float
    norm: float
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.arr = array([x,y])
        self.norm = norm(self.arr)
        self.normed = self.arr/self.norm

    def __sub__(self, other):
        return Vector(self.x-other.x, self.y-other.y)

    def __add__(self, other):
        return Vector(self.x+other.x, self.y+other.y)

    def rot(self, th):
        rmatrix = array([[np.cos(th), -np.sin(th)],[np.sin(th), np.cos(th)]])
        return Vector(*dot(rmatrix,self.arr))

@dataclass
class CircCorralData:
    file: str
    def __init__(self, file):
        self.file = file
        self.image_file = createc.DAT_IMG(self.file)
        # topography,
        self.im = self.image_file._crop_img(self.image_file.img_array_list[0][:][:])
        self.imshape = self.im.shape
        self.xPix = self.imshape[0]
        self.yPix = self.imshape[1]
        self.ang_ppx_x = self.image_file.nom_size.x / self.image_file.xPixel
        self.ang_ppx_y = self.image_file.nom_size.y / self.image_file.yPixel
        # nchannels = image_file.channels

    def nm_to_pix(self, nm):
        scale = self.ang_ppx_x# if direction=="x" else self.ang_ppx_y
        return nm/scale*10

    def pix_to_nm(self, pix):
        scale = self.ang_ppx_x #if direction=="x" else self.ang_ppx_y
        return pix*scale/10

    def subtract_plane(self):
        X1, X2 = np.mgrid[:self.xPix, :self.yPix]
        nxny = self.xPix*self.yPix
        X = np.hstack((reshape(X1, (nxny, 1)), reshape(X2, (nxny, 1))))
        X = np.hstack((np.ones((nxny, 1)), X))
        YY = np.reshape(self.im, (nxny,1))
        theta = dot(dot(pinv(dot(X.transpose(), X)), X. transpose()), YY)
        plane = np.reshape(dot(X, theta), (self.xPix, self.yPix))
        self.im -= plane
        # return plane

    def get_region_centroids(self, diamond_size=4):
        diamond = morphology.diamond(diamond_size)
        # max = morphology.local_maxima(im, connectivity=50)
        maxima = morphology.h_maxima(self.im, np.std(self.im))
        r = morphology.binary_dilation(maxima, selem=diamond)
        plt.imshow(maxima)
        plt.show()
        xim = morphology.label(r)
        # plt.imshow(xim)
        regions = measure.regionprops(xim)
        regions_areas = [r.area for r in regions]
        regions_area_max = max(regions_areas)

        # all regions might be same size, in which case we're spot on
        allsame = np.all([r==regions_areas[0] for r in regions_areas])

        # if we have the 'background' as a region, remove it
        if not allsame:
            regions = [r for r in regions if (r.area != regions_area_max)]
        self.centroids = [list(reversed(r.centroid)) for r in regions]
        # return centroids

    def remove_central_atom(self):
        # Check two ways
        # 1:
        # get the distance matrix
        distmat = distance_matrix(self.centroids, self.centroids)

        # nearest neighbor distances for every centroid
        dists = np.ma.masked_equal(distmat,0).min(axis=1)

        # centroid w largest nearest neighbor distance is the central atom
        center_idx_1 = np.argmax(dists)

        # # create a copy since we want to save central atom

        r, center = self.nsphere_fit(self.centroids)
        center_idx_2 = argmin([norm(center-o) for o in self.centroids])

        if center_idx_1==center_idx_2:
            ccopy = self.centroids.copy()

            # remove outlier
            ccopy.pop(center_idx_1)
            return ccopy
        else:
            raise Exception("Something went wrong in removing the central atom")

    def get_central_atom(self):
        # get the distance matrix
        distmat = distance_matrix(self.centroids, self.centroids)

        # nearest neighbor distances for every centroid
        dists = np.ma.masked_equal(distmat,0).min(axis=1)
        print(dists)
        # centroid w largest nearest neighbor distance is the central atom
        center_idx_1 = np.argmax(dists)

        r, center = self.nsphere_fit(self.centroids)
        center_idx_2 = argmin([norm(center-o) for o in self.centroids])

        if center_idx_1 ==center_idx_2:
            # remove outlier
            return self.centroids[center_idx_1]
        else:
            raise Exception("Something went wrong ")

    def nsphere_fit(self, x, axis=-1, scaling=False):
        r"""
        Fit an n-sphere to ND data.
        The center and radius of the n-sphere are optimized using the Coope
        method. The sphere is described by
        .. math::
           \left \lVert \vec{x} - \vec{c} \right \rVert_2 = r
        Parameters
        ----------
        x : array-like
            The n-vectors describing the data. Usually this will be a nxm
            array containing m n-dimensional data points.
        axis : int
            The axis that determines the number of dimensions of the
            n-sphere. All other axes are effectively raveled to obtain an
            ``(m, n)`` array.
        scaling : bool
            If `True`, scale and offset the data to a bounding box of -1 to
            +1 during computations for numerical stability. Default is
            `False`.
        Return
        ------
        r : scalar
            The optimal radius of the best-fit n-sphere for `x`.
        c : array
            An array of size `x.shape[axis]` with the optimized center of
            the best-fit n-sphere.
        References
        ----------
        - [Coope]_ "\ :ref:`ref-cfblanls`\ "
        """
        # x = preprocess(x, float=True, axis=axis)
        x = array(x)
        n = x.shape[-1]
        x = x.reshape(-1, n)
        m = x.shape[0]

        B = np.empty((m, n + 1), dtype=x.dtype)
        X = B[:, :-1]
        X[:] = x
        B[:, -1] = 1

        if scaling:
            xmin = X.min()
            xmax = X.max()
            scale = 0.5 * (xmax - xmin)
            offset = 0.5 * (xmax + xmin)
            X -= offset
            X /= scale

        d = square(X).sum(axis=-1)
        # pdb.set_trace()
        y, *_ = lstsq(B, d)#, overwrite_a=True, overwrite_b=True)

        c = 0.5 * y[:-1]
        r = sqrt(y[-1] + square(c).sum())

        if scaling:
            r *= scale
            c *= scale
            c += offset
        self.r, self.c = r, c
        return r, c

    def circle(self, r, c, npoints=100):
        theta = 2*np.pi*np.arange(0,1,1/npoints)
        x = c[0] + r*np.cos(theta)
        y = c[1] + r*np.sin(theta)
        return x, y

    def plot_circle_fit(self, points, radius, center, label):
        xc, yc = self.circle(radius, center, npoints=1000)
        pdb.set_trace()
        plt.scatter(*array(points).T,label=label)
        plt.scatter(xc, yc, alpha=0.5, s=5, label=label)
        # plt.show()

    def bbox(self):
        """
        return (x0, y0, x1, y1) defined by the min and max x, y coords of atoms making up the corral
        """
        xs, ys = array(self.remove_central_atom()).T
        return [min(xs), min(ys), max(xs), max(ys)]

    def make_lattice(self, theta, offset=0):
        theta = -theta
        origin = self.get_central_atom()
        bbox = self.bbox()

        width = 1.5*(bbox[2] - bbox[0])
        height = 1.5*(bbox[3] - bbox [1])

        natoms_per_row = round_to_even(self.pix_to_nm(width)/b)
        nrows = round_to_even(self.pix_to_nm(height)/d)
        offset = [width/2, height/2]

        ls = []
        for n in np.arange(-nrows/2,nrows/2+1, 1):
            for m in np.arange(-natoms_per_row/2,natoms_per_row/2+1, 1):
                if n%2==0:
                    ls.append(array([n*self.nm_to_pix(d), m*self.nm_to_pix(b)]))
                else:
                    ls.append(array([n*self.nm_to_pix(d), (m*self.nm_to_pix(b) + self.nm_to_pix(b/2))]))
        rot = array([[cos(theta), -sin(theta)], [sin(theta), cos(theta)]])
        # plt.triplot(*array(ls).T)

        ls = dot(ls, rot)
        # ls += np.dot(rot, offset)
        ls += array(origin)

        # plt.triplot(*array(ls).T)
        return ls

    def correlate_lattice_to_atom_positions(self, angle, spread):
        #return sum of Gaussians centered @ atoms evaluated at lattice vectors
        # g = meshgrid(linspace(0, self.xPix-1, self.xPix), linspace(0, self.yPix-1, self.yPix))
        # m = np.sum([gaussian(3,*cen,14,14)(*array(g).reshape(2,256*256)) for cen in self.centroids], axis=0)
        # plt.imshow(m.reshape(256,256), alpha=0.4)
        # plt.figure()
        # plt.imshow(self.im)
        # plt.title("image")
        # plt.show()
        lat = self.make_lattice(angle)
        pdb.set_trace()
        g2d = np.sum([gaussian(1, *cen, 23, 23)(*array(lat).T) for cen in self.centroids], axis=0)
        return sum(g2d)

    def get_im_square(self, x, y, sidelen):
        print(x,y, round_to_even(sidelen))
        # return the image around x,y with sides sidelen
        return self.im[int(y)-sidelen//2:int(y)+sidelen//2,int(x)-sidelen//2:int(x)+sidelen//2]

    def fit_lattice(self):
        angs = np.pi/3*np.arange(0,1.01,0.001)
        corrs = [self.correlate_lattice_to_atom_positions(ang,2) for ang in angs]
        plt.plot(corrs)
        plt.show()

        plt.figure(figsize=(6,6))
        plt.imshow(self.im)
        plt.triplot(*array(self.make_lattice(angs[np.argmax(corrs)])).T)

    def fit_atom_pos_gauss(self, box_size=40):
        """
        Given a CircCorralData object with first-guess centroids,
        get square of side length box_size and fit 2D Gaussian to the atom shape
        to get a better guess for atom positions. Return a 'reconstruction'
        of the original image using the Gaussian fit parameters for every atom
        and a list of the atoms and their fit parameters
        """
        full_im = np.zeros(self.im.shape)
        fit_params = []
        for cen in self.centroids:
            # Fit a Gaussian over the atom topopgraphy
            f = self.get_im_square(*cen, box_size)
            params = fitgaussian(f)
            fitc = gaussian(*params)
            # plt.matshow(f);
            # plt.contour(fitc(*np.indices(f.shape)), cmap=plt.cm.copper)
            #
            # plt.scatter([params[2]], [params[1]], )
            # plt.scatter([box_size/2],[box_size/2],c="red")
            # plt.show()

            # add the original 'box' back to the center
            params[1] += cen[1] - box_size/2
            params[2] += cen[0] - box_size/2
            fit_params.append(params)

            # add the Gaussian fit to the 'reconstruction' image
            full_im = full_im + gaussian(*params)(*np.indices(self.im.shape))

        # we only really care about the locations
        fp = array([array(fit_params).T[2],array(fit_params).T[1]])

        #dist (Å) 'max height' guess is off from Gaussian fit
        d = np.mean(norm(self.pix_to_nm(array(self.centroids))-self.pix_to_nm(fp.T),axis=1)*10)
        print("Max height guess different from Gaussian fit on average by: %1.2lf Å" %(d))
        self.gauss_fit_params = np.array(fit_params)
        self.gauss_fit_locs = fp
        return full_im, fp

    def compare_fits(self):
        plt.matshow(self.im)
        self.plot_circle_fit(self.centroids, r_n, c_n, "naive")
        self.plot_circle_fit(self.gauss_fit_locs.T, r_g, c_g, "Gaussian")
        # plt.show()
        # plt.scatter(*c.gauss_fit_locs, label="Gaussian fit points")
        plt.legend()
        plt.show()

def round_to_even(n):
    # return n rounded up to the nearest even integer
    return int(np.ceil(n/2.)*2)

def gaussian(height, center_x, center_y, width_x, width_y):
    """Returns a gaussian function with the given parameters"""
    width_x = float(width_x)
    width_y = float(width_y)
    return lambda x,y: height*np.exp(
                -(((center_x-x)/width_x)**2+((center_y-y)/width_y)**2)/2)

def moments(data):
    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution by calculating its
    moments

    first guess for fit parameters
    """
    total = data.sum()
    X, Y = np.indices(data.shape)
    x = (X*data).sum()/total
    y = (Y*data).sum()/total
    try:
        col = data[:, int(y)]
        width_x = np.sqrt(np.abs((np.arange(col.size)-x)**2*col).sum()/col.sum())
        row = data[int(x), :]
        width_y = np.sqrt(np.abs((np.arange(row.size)-y)**2*row).sum()/row.sum())
    except:
        width_x, width_y = [22,22]
    height = data.max()
    return height, x, y, width_x, width_y

def fitgaussian(data):
    """Returns (height, x, y, width_x, width_y)
    the gaussian parameters of a 2D distribution found by a fit"""
    params = moments(data)
    errorfunction = lambda p: np.ravel(gaussian(*p)(*np.indices(data.shape)) -
                                 data)
    errorfunction = lambda p: np.ravel(gaussian(*p)(*np.indices(data.shape)) -
                                 data)
    p, success = leastsq(errorfunction, params)
    return p

if __name__=="__main__":
    c = CircCorralData(dpath + c4)
    c.subtract_plane()
    c.get_region_centroids()

    # naive fit from maximum pointss
    r_n, c_n = c.nsphere_fit(c.remove_central_atom())

    # better fit from gaussian fits to atoms
    full_im, fit_params = c.fit_atom_pos_gauss()
    r_g, c_g = c.nsphere_fit(c.gauss_fit_locs.T)


    c.compare_fits()
    plt.savefig(c.file+"_circle_fits.png")

    ##TO DO:
    """
    - implement shift and Gaussian atom locs into fitting
    """
    exit(0)
