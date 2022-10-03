import glob
import os

import numpy as np
import torch
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
from sunpy.map import Map

from nf2.data.dataset import BoundaryDataset
from nf2.potential.potential_field import get_potential_boundary


def load_hmi_dataset(hmi_cube, error_cube,
                     height, spatial_norm, b_norm,
                     work_directory, batch_size,
                     potential_boundary=True,
                     plot=False, plot_path=None):
    # load coordinates
    mf_coords = np.stack(np.mgrid[:hmi_cube.shape[0], :hmi_cube.shape[1], :1], -1)
    # flatten data
    mf_coords = mf_coords.reshape((-1, 3))
    mf_values = hmi_cube.reshape((-1, 3))
    mf_err = error_cube.reshape((-1, 3))
    # load potential field
    if potential_boundary:
        pf_coords, pf_err, pf_values = _load_potential_field_data(hmi_cube, height)
        # concatenate pf data points
        coords = np.concatenate([pf_coords, mf_coords])
        values = np.concatenate([pf_values, mf_values])
        err = np.concatenate([pf_err, mf_err])
    else:
        coords = mf_coords
        values = mf_values
        err = mf_err

    # normalize data
    values = Normalize(-b_norm, b_norm, clip=False)(values) * 2 - 1
    err = Normalize(0, b_norm, clip=False)(err)

    # apply spatial normalization
    coords = coords / spatial_norm

    # stack to numpy array
    data = np.stack([coords, values, err], 1)

    # shuffle data
    r = np.random.permutation(data.shape[0])
    data = data[r]
    # adjust to batch size
    pad = batch_size - data.shape[0] % batch_size
    data = np.concatenate([data, data[:pad]])

    # split data into batches
    n_batches = data.shape[0] // batch_size
    batches = np.array(np.split(data, n_batches), dtype=np.float32)

    # store batches to disk
    batches_path = os.path.join(work_directory, 'batches.npy')
    np.save(batches_path, batches)

    # create data loaders
    boundary_ds = BoundaryDataset(batches_path)

    if plot:
        _plot_data(error_cube, hmi_cube, plot_path, b_norm)

    return boundary_ds


def load_hmi_data(data_path):
    if isinstance(data_path, str):
        hmi_p = sorted(glob.glob(os.path.join(data_path, '*Bp.fits')))[0]  # x
        hmi_t = sorted(glob.glob(os.path.join(data_path, '*Bt.fits')))[0]  # y
        hmi_r = sorted(glob.glob(os.path.join(data_path, '*Br.fits')))[0]  # z
        err_p = sorted(glob.glob(os.path.join(data_path, '*Bp_err.fits')))[0]  # x
        err_t = sorted(glob.glob(os.path.join(data_path, '*Bt_err.fits')))[0]  # y
        err_r = sorted(glob.glob(os.path.join(data_path, '*Br_err.fits')))[0]  # z
    else:
        hmi_p, err_p, hmi_r, err_r, hmi_t, err_t = data_path
    # laod maps
    hmi_cube = np.stack([Map(hmi_p).data, -Map(hmi_t).data, Map(hmi_r).data]).transpose()
    error_cube = np.stack([Map(err_p).data, Map(err_t).data, Map(err_r).data]).transpose()
    return hmi_cube, error_cube


def _load_potential_field_data(hmi_cube, height):
    pf_batch_size = int(1024 * 512 ** 2 / np.prod(hmi_cube.shape[:2]))  # adjust batch to AR size
    pf_coords, pf_values = get_potential_boundary(hmi_cube[:, :, 2], height, batch_size=pf_batch_size)
    pf_values = np.array(pf_values, dtype=np.float32)
    pf_err = np.zeros_like(pf_values)
    return pf_coords, pf_err, pf_values


def _plot_data(error_cube, n_hmi_cube, plot_path, b_norm):
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    axs[0].imshow(n_hmi_cube[..., 0].transpose(), vmin=-b_norm, vmax=b_norm, cmap='gray', origin='lower')
    axs[1].imshow(n_hmi_cube[..., 1].transpose(), vmin=-b_norm, vmax=b_norm, cmap='gray', origin='lower')
    axs[2].imshow(n_hmi_cube[..., 2].transpose(), vmin=-b_norm, vmax=b_norm, cmap='gray', origin='lower')
    plt.savefig(os.path.join(plot_path, 'b.jpg'))
    plt.close()
    fig, axs = plt.subplots(1, 3, figsize=(12, 4))
    axs[0].imshow(error_cube[..., 0].transpose(), vmin=0, cmap='gray', origin='lower')
    axs[1].imshow(error_cube[..., 1].transpose(), vmin=0, cmap='gray', origin='lower')
    axs[2].imshow(error_cube[..., 2].transpose(), vmin=0, cmap='gray', origin='lower')
    plt.savefig(os.path.join(plot_path, 'b_err.jpg'))
    plt.close()


class RandomSampler():

    def __init__(self, cube_shape, spatial_norm, batch_size, cuda=True):
        self.cube_shape = cube_shape
        self.spatial_norm = spatial_norm
        self.batch_size = batch_size
        self.float_tensor = torch.cuda.FloatTensor if cuda else torch.FloatTensor

    def load_sample(self):
        random_coords = self.float_tensor(self.batch_size, 3).uniform_()
        random_coords[:, 0] *= self.cube_shape[0] / self.spatial_norm
        random_coords[:, 1] *= self.cube_shape[1] / self.spatial_norm
        random_coords[:, 2] *= self.cube_shape[2] / self.spatial_norm
        return random_coords
