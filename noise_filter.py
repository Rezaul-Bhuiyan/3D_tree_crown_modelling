# Urban_PointCloud_Processing by Amsterdam Intelligence, GPL-3.0 license

"""Noise filter"""

import numpy as np
import logging

from ..abstract_processor import AbstractProcessor
from ..region_growing.label_connected_comp import LabelConnectedComp
from ..labels import Labels

logger = logging.getLogger(__name__)


class NoiseFilter(AbstractProcessor):
    """
    Noise filter based on elevation level and cluster size. Any points below
    ground level, and points that are within clusters with a size below the
    given threshold, will be labelled as noise.

    Parameters
    ----------
    label : int
        Class label to use for this fuser.
    ahn_reader : AHNReader object
        Elevation data reader.
    epsilon : float (default: 0.2)
        Precision of the fuser.
    grid_size : float (default: 0.1)
        Octree grid size for clustering connected components.
    min_component_size : int (default: 100)
        Minimum size of a cluster below which it is regarded as noise.
    """
    def __init__(self, label, ahn_reader, epsilon=0.2,
                 grid_size=0.1, min_component_size=100):
        super().__init__(label)

        self.ahn_reader = ahn_reader
        self.epsilon = epsilon
        self.grid_size = grid_size
        self.min_component_size = min_component_size

    def get_labels(self, points, labels, mask, tilecode):
        """
        Returns the labels for the given pointcloud.

        Parameters
        ----------
        points : array of shape (n_points, 3)
            The point cloud <x, y, z>.
        labels : array of shape (n_points,)
            Ignored by this fuser.
        mask : array of shape (n_points,) with dtype=bool
            Pre-mask used to label only a subset of the points.
        tilecode : str
            The CycloMedia tile-code for the given pointcloud.

        Returns
        -------
        An array of shape (n_points,) with the updated labels.
        """
        logger.info('Noise filter ' +
                    f'(label={self.label}, {Labels.get_str(self.label)}).')
        lcc = LabelConnectedComp(self.label, grid_size=self.grid_size,
                                 min_component_size=self.min_component_size)
        point_components = lcc.get_components(points[mask])
        cc_mask = point_components == -1
        logger.debug(f'Found {np.count_nonzero(cc_mask)} noise points in '
                     + f'clusters <{self.min_component_size} points.')

        # Get the interpolated ground points of the tile
        target_z = self.ahn_reader.interpolate(
                            tilecode, points[mask], mask, 'ground_surface')
        ground_mask = (points[mask, 2] - target_z) < -self.epsilon
        diff = ground_mask & ~cc_mask
        logger.debug(f'Found {np.count_nonzero(diff)} noise points '
                     + 'below ground level.')

        label_mask = np.zeros((len(points),), dtype=bool)
        # Label points below ground and points in small components.
        label_mask[mask] = cc_mask | ground_mask
        labels[label_mask] = self.label

        return labels
