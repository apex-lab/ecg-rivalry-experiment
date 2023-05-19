from psychopy import visual, event
import numpy as np
from psychopy.visual.filters import makeGrating

def make_gratings(win,
    red_cycles = 10, red_phase = 0.,
    blue_cycles = 3, blue_phase = 0.,
    grating_res = 256):

    red_grating = makeGrating(
        res = grating_res,
        ori = 45.,
        cycles = red_cycles,
        phase = red_phase,
        gratType = 'sqr'
        )
    blue_grating = makeGrating(
        res = grating_res,
        ori = 3*45.,
        cycles = blue_cycles,
        phase = blue_phase,
        gratType = 'sqr'
        )
    grating = np.ones((grating_res, grating_res, 3)) * -1.0 # black background
    grating[..., 0] = red_grating
    grating[..., -1] = blue_grating
    stim = visual.GratingStim(
        win = win,
        tex = grating,
        #mask = "circle",
        size = (grating_res, grating_res),
    )
    return stim
