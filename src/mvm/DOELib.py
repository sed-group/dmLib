from typing import List, Union

import numpy as np
from pyDOE import lhs

"""DOE Library for generating a design"""


def gridsamp(bounds: np.ndarray, q: Union[int, np.ndarray, List[int]]) -> np.ndarray:
    """
    GRIDSAMP  n-dimensional grid over given range

    Parameters
    ----------
    bounds : np.ndarray
        2*n matrix with lower and upper limits
    q : np.ndarray
        n-vector, q(j) is the number of points
        in the j'th direction.
        If q is a scalar, then all q(j) = q

    Returns
    -------
    S : np.ndarray
        m*n array with points, m = prod(q)
    """

    [mr, n] = np.shape(bounds)
    dr = np.diff(bounds, axis=0)[0]  # difference across rows
    if mr != 2 or any([item < 0 for item in dr]):
        raise Exception('bounds must be an array with two rows and bounds(1,:) <= bounds(2,:)')

    if q.ndim > 1 or any([item <= 0 for item in q]):
        raise Exception('q must be a vector with non-negative elements')

    p = len(q)
    if p == 1:
        q = np.tile(q, (1, n))[0]
    elif p != n:
        raise Exception('length of q must be either 1 or %d' % n)

    # Check for degenerate intervals
    i = np.where(dr == 0)[0]
    if i.size > 0:
        q[i] = 0 * q[i]

    # Recursive computation
    if n > 1:
        a = gridsamp(bounds[:, 1::], q[1::])  # Recursive call
        [m, _] = np.shape(a)
        q = int(q[0])
        s = np.concatenate((np.zeros((m * q, 1)), np.tile(a, (q, 1))), axis=1)
        y = np.linspace(bounds[0, 0], bounds[1, 0], q)

        k = range(m)
        for i in range(q):
            aug = np.tile(y[i], (m, 1))
            aug = np.reshape(aug, s[k, 0].shape)

            s[k, 0] = aug
            k = [item + m for item in k]
    else:
        s = np.linspace(bounds[0, 0], bounds[1, 0], int(q[-1]))
        s = np.transpose([s])

    return s


def scaling(x: np.ndarray, lb: np.ndarray, ub: np.ndarray, operation: int) -> np.ndarray:
    """
    Scaling by a range

    Parameters
    ----------
    x : np.ndarray
        2d array of size n * nsamples of datapoints
    lb : np.ndarray
        1d array of length n specifying lower range of features
    ub : np.ndarray
        1d array of length n = len(l) specifying upper range of features
    operation : int
        The flag type indicates whether to scale (1) or unscale (2)

    Returns
    -------
    x_out : np.ndarray
        2d array of size n * nsamples of unscaled datapoints
    """

    if operation == 1:
        # scale
        x_out = (x - lb) / (ub - lb)
        return x_out
    elif operation == 2:
        # unscale
        x_out = lb + x * (ub - lb)
        return x_out


class Design:

    def __init__(self, lb: np.ndarray, ub: np.ndarray, nsamples: Union[int, List[int], np.ndarray], doe_type: str):
        """
        Contains the experimental design limits, 
        samples and other relevant statistics

        Parameters
        ----------
        lb : np.ndarray
            1d array of length n specifying lower range of features
        ub : np.ndarray
            1d array of length n = len(lb) specifying upper range of features
        nsamples : Union[int,List[int],np.ndarray]
            The number of samples to generate for each factor, 
            if array_like and type specificed is 'fullfact' then samples each variable according to its sampling vector
        doe_type : str, optional
            Allowable values are "LHS" and "fullfact". If no value 
            given, the design is simply randomized.
        
        # TODO: return error if len(lb) != len(ub)
        """

        self.lb = lb
        self.ub = ub

        self.nsamples = nsamples
        self.type = doe_type

        # Generate latin hypercube design and store it

        if self.type == 'LHS':
            assert type(self.nsamples) == int
            self.design = lhs(len(self.lb), samples=self.nsamples)
        elif self.type == 'fullfact':
            bounds = np.array([[0.0] * len(self.lb), [1.0] * len(self.ub)])
            if type(self.nsamples) == list:
                assert len(self.nsamples) == len(self.lb)
                self.design = gridsamp(bounds, np.array(self.nsamples))
            if type(self.nsamples) == np.ndarray:
                assert self.nsamples.ndim == 1
                assert len(self.nsamples) == len(self.lb)
                self.design = gridsamp(bounds, self.nsamples)
            elif type(self.nsamples) == int:
                self.design = gridsamp(bounds, np.array([self.nsamples]))

    def unscale(self) -> np.ndarray:
        """
        Unscale latin hypercube by ub and lb

        Returns
        -------
        unscaled_LH : np.array
            numpy array of size n * nsamples of LH values unscaled by lb and ub
        """

        unscaled_lh = scaling(self.design, self.lb, self.ub, 2)

        return unscaled_lh

    def scale(self) -> np.ndarray:
        """
        return scaled latin hypercube between 0 and 1

        Returns
        -------
        scaled_LH : np.array
            numpy array of size n * nsamples of LH values between 0 and 1
        """

        return self.design
