from typing import List
import logging
from copy import copy

import numpy as np
import scipy.ndimage as ndimage

from bulldozer.utils.bulldozer_logger import BulldozerLogger
import bulldozer.eoscale.manager as eom
import bulldozer.eoscale.eo_executors as eoexe
import bulldozer.springforce as sf


def fill_pits_filter(inputBuffers: list,
                     input_profiles: list,
                     params: dict) -> List[np.ndarray]:
    """
    Perform pits removal and create pits detection mask.

    :param inputBuffers: DTM buffer
    :return: a List composed of the processed dtm without pits and the pits mask
    """
    dtm = inputBuffers[0][0, :, :]
    pits_mask = np.zeros(dtm.shape, dtype=np.ubyte)

    border_mask = inputBuffers[1][0, :, :]

    dtm[border_mask==1] = params["nodata"]

    nb_rows = dtm.shape[0]
    nb_cols = dtm.shape[1]
    bfilters = sf.PyBulldozerFilters()

    # dtm_LF = ndimage.uniform_filter(dtm, size=params["filter_size"])
    dtm_LF = bfilters.run(dtm, nb_rows, nb_cols, round(params["filter_size"]), params["nodata"])
    
    # Retrieves the high frequencies in the input DTM
    dtm_HF = dtm - dtm_LF

    # Tags the pits
    pits_mask[dtm_HF < 0.] = 1
    pits_mask[border_mask==1] = 0

    # fill pits
    dtm = np.where( (pits_mask) & (dtm != params["nodata"]), dtm_LF, dtm)

    return [dtm, pits_mask]


def fill_pits_profile(input_profiles: list,
                      params: dict) -> dict:
    """
    Defines filter outputs profiles
    """
    msk_profile = copy(input_profiles[0])
    msk_profile['dtype'] = np.uint8
    msk_profile['nodata'] = None
    return [input_profiles[0], msk_profile]


def run(dtm_key: str,
        border_nodata_key: str,
        eomanager: eom.EOContextManager):
    """
    Performs the pit removal process using EOScale.

    :param dtm_key: the dtm to process key in the eo manager
    :param border_nodata_key: Border no data
    :return : The processed dtm and the pits mask keys
    """
    resolution = eomanager.get_profile(dtm_key)['transform'][0]
    filter_size = 35.5 / resolution

    fill_pits_parameters: dict = {
        "filter_size": filter_size,
        "nodata": eomanager.get_profile(dtm_key)['nodata']
    }

    [filled_dtm_key, pits_mask_key] = \
        eoexe.n_images_to_m_images_filter(inputs=[dtm_key, border_nodata_key],
                                          image_filter=fill_pits_filter,
                                          filter_parameters=fill_pits_parameters,
                                          generate_output_profiles=fill_pits_profile,
                                          context_manager=eomanager,
                                          stable_margin=int(filter_size/2),
                                          filter_desc="Pits removal processing...")

    eomanager.release(key=dtm_key)
    dtm_key = filled_dtm_key

    return dtm_key, pits_mask_key
