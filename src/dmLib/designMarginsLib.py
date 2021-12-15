import numpy as np
from typing import Dict, Any, AnyStr, List, Type
import matplotlib.pyplot as plt
from .uncertaintyLib import Distribution
from .utilities import check_folder

"""Design margins library for computing buffer and excess"""
class MarginNode():

    def __init__(self,label='',cutoff=0.9,buffer_limit=0):
        """
        Contains description and implementation 
        of a Margin Node object which is the building block
        of a Margin Analysis Network (MAN)

        Parameters
        ----------
        cutoff : float, optional
            cutoff limit for calculating reliability,
            default = 0.9
        buffer_limit : float, optional
            lower bound for beginning of buffer zone,
            default = 0.0
        label : str, optional
            string to tag instance with, default = ''
        """

        self.label = label
        self.cutoff = 0.9
        self.buffer_limit = 0.0
        self._target = np.empty(0)
        self._decided_value = np.empty(0)
        self._excess = np.empty(0)
        self._excess_dist = None

    @property
    def target(self):
        """
        Target vector getter

        Returns
        -------
        np.1darray
            vector of target observations
        """
        return self._target

    @target.setter
    def target(self,t):
        """
        Appends target observation t to target vector

        Parameters
        ----------
        t : float OR np.1darray
            value to append to target vector
        """
        self._target = np.append(self._target,t)

    @property
    def decided_value(self):
        """
        Response vector getter

        Returns
        -------
        np.1darray
            vector of response observations
        """
        return self._decided_value

    @decided_value.setter
    def decided_value(self,r):
        """
        Appends response observation r to target vector

        Parameters
        ----------
        r : float OR np.1darray
            value to append to response vector
        """
        self._decided_value = np.append(self._decided_value,r)

    @property
    def excess(self):
        """
        Excess vector getter

        Returns
        -------
        np.1darray
            vector of excess observations
        """
        return self._excess

    @excess.setter
    def excess(self,e):
        """
        Appends excess observation e to target vector

        Parameters
        ----------
        e : float OR np.1darray
            value to append to response vector
        """
        self._excess = np.append(self._excess,e)

    @property
    def excess_dist(self) -> Distribution:
        """
        Excess Distribution object

        Returns
        -------
        dmLib.Distribution
            instance of dmLib.Distribution holding excess pdf
        """
        return self._excess_dist

    @excess_dist.setter
    def excess_dist(self,excess):
        """
        Creates excess Distribution object

        Parameters
        ----------
        excess : np.1darray
            Vector of excess values
        """
        self._excess_dist = Distribution(excess, lb=min(excess),ub=max(excess))

    def reset(self):
        """
        Resets accumulated random observations in target, 
        response, and excess attributes
        """
        self._target = np.empty(0)
        self._decided_value = np.empty(0)
        self._excess = np.empty(0)
        self._excess_dist = None

    def compute_cdf(self,bins=500):
        """
        Calculate the cumulative distribution function for the excess margin

        Parameters
        ----------
        bins : int, optional
            number of discrete bins used to 
            construct pdf and pdf curves, by default 500

        Returns
        -------
        bin_centers : np.1darray
            array of len(excess) - 1 containing the x-axis values of CDF
        cdf : np.1darray
            array of len(excess) - 1 containing the y-axis values of CDF
        excess_limit : float
            The value on the x-axis that corresponds to the cutoff probability
        reliability : float
            the probability of excess being >= target
        """
        def moving_average(x, w):
            """
            N-moving average over 1D array

            Parameters
            ----------
            x : np.1darray
                input array to average
            w : int
                number of elements to average

            Returns
            -------
            np.1darray
                avaeraged array
            """
            return np.convolve(x, np.ones(w), 'valid') / w

        excess_hist = np.histogram(self.excess, bins=bins,density=True)
        bin_width = np.mean(np.diff(excess_hist[1]))
        bin_centers = moving_average(excess_hist[1],2)
        cdf = np.cumsum(excess_hist[0] * bin_width)

        excess_limit = bin_centers[cdf >= self.cutoff][0]
        reliability = 1 - cdf[bin_centers >= self.buffer_limit][0]

        return bin_centers, cdf, excess_limit, reliability

    def view(self,xlabel='',savefile=None):
        """
        view 1D or 2D plot of probability distribution of excess
        """

        self.fig, self.ax = plt.subplots(figsize=(8, 3))
        self.ax.hist(self.excess, bins=100, density=True)
        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel('density')

        if savefile is not None:
            # Save figure to image
            check_folder('images/%s' %(self.label))
            self.fig.savefig('images/%s/%s.pdf' %(self.label,savefile), 
                format='pdf', dpi=200, bbox_inches='tight')

        plt.show()

    def view_cdf(self,xlabel='',savefile=None):
        """
        view 1D or 2D plot of cumulative distribution of excess
        """

        # calculate CDF
        bin_centers, cdf, excess_limit, reliability = self.compute_cdf()
        buffer_band = (bin_centers >= self.buffer_limit) & (cdf <= self.cutoff)
        excess_band = cdf >= self.cutoff

        self.figC, self.axC = plt.subplots(figsize=(8, 3))
        self.axC.plot(bin_centers, cdf, '-b')
        self.axC.vlines([self.buffer_limit,excess_limit],[0,0],[1-reliability,self.cutoff],linestyles='dashed')
        self.axC.fill_between(bin_centers[buffer_band], 0, cdf[buffer_band], facecolor='Green', alpha=0.4, label='Buffer')
        self.axC.fill_between(bin_centers[excess_band], 0, cdf[excess_band], facecolor='Red', alpha=0.4, label='Excess')
        
        tb = self.axC.text((excess_limit + self.buffer_limit) / 2 - 0.2, 0.1, 'Buffer', fontsize=14)
        te = self.axC.text((excess_limit + bin_centers[-1]) / 2 - 0.2, 0.1, 'Excess', fontsize=14)
        tb.set_bbox(dict(facecolor='white'))
        te.set_bbox(dict(facecolor='white'))

        self.axC.set_xlabel(xlabel)
        self.axC.set_ylabel('Cumulative density')

        if savefile is not None:
            # Save figure to image
            check_folder('images/%s' %(self.label))
            self.figC.savefig('images/%s/%s.pdf' %(self.label,savefile), 
                format='pdf', dpi=200, bbox_inches='tight')

        plt.show()

    def __call__(self,decided_value,target_threshold):
        """
        Calculate excess given the target threshold and decided value

        Parameters
        ----------
        decided_value : np.1darray
            decided values to the margin node describing the capability of the design.
            The length of this vector equals the number of samples
        target_threshold : np.1darray
            The target threshold parameters that the design needs to achieve
            The length of this vector equals the number of samples
        """
            
        self.decided_value = decided_value # add to list of decided values
        self.target = target_threshold # add to list of targets

        e = decided_value - target_threshold
        self.excess = e # add to list of excesses