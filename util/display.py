from itertools import product
import numpy as np
import asyncio
import time

from psychopy import monitors, visual
from ._gratings import make_gratings

from .._messages import DisplayMessage
import labgraph as lg

class DisplayState(lg.State):
    red_step: int = 0
    blue_step: int = 0
    autoDraw: bool = True

class DisplayConfig(lg.Config):
    # controls granularity of stimuli
    n_steps: int = 10

class Display(lg.Node):
    """
    This node sets up psychopy stims, signals when it is ready and changes displayed
    stims according to events received on the specified topic.
    """
    DISPLAY_TOPIC = lg.Topic(DisplayMessage)
    state: DisplayState

    def setup(self) -> None:
        self._stims = None
        self._shutdown = False
        self._start_t = time.time()

    def cleanup(self) -> None:
        """
        This function is called when a NormalTermination is raised, so we set relevant
        shutdown flags here. We can use this to break out of infinite loops.
        """
        self._shutdown = True

    def _setup_stims(self, window: visual.Window) -> np.ndarray[visual.BaseVisualStim]:
        """
        Pre-generate rivalry stimuli, since making the custom gratings is slow.

        This cannot be done in the `setup` function because the window needs to be
        available, and psychopy needs the window to be created in the "main" thread.
        """
        n_steps = self.config.n_steps
        steps = np.linspace(10, 5, n_steps)
        self._stims = np.empty((n_steps, n_steps), dtype = object)
        for i, j in product(range(n_steps), range(n_steps)):
            self._stims[i,j] = make_gratings(
                win, red_cycles = steps[i], blue_cycles = steps[j]
            )

    def _val_to_steps(self, val: float):
        n_steps = self.config.n_steps
        step = np.floor(val * n_steps).astype(int)
        if step == n_steps:
            step -= 1
        return step

    @lg.subscriber(DISPLAY_TOPIC)
    def update_stims(self, message: DisplayMessage) -> None:
        """
        This function subscribes to the specified topic that receives the "next"
        stimulus state and updates the `autoDraw` status of pre-made stims.
        """
        red_step = self._val_to_steps(message.red)
        blue_step = self._val_to_steps(message.blue)
        # turn off autodraw for old stim
        self._stims[self.state.red_step, self.state.blue_step].autoDraw = False
        # and turn it on for new stim
        self.state.red_step = red_step
        self.state.blue_step = blue_step
        self._stims[self.state.red_step, self.state.blue_step].autoDraw = self.state.autoDraw

    @lg.main
    def display(self):
        """
        This function runs in the main thread and sets up required psychopy objects.

        After initial setup is done, it loops until signaled to shutdown, and flips
        the psychopy frame. At every frame flip, the stims with `autoDraw` set to True
        are displayed.
        - Note that frame flips are inherently throttled by screen refresh rates, so
          this is not a tight loop and does not need to manually sleep between flips.

        You can toggle self.state.autoDraw to control whether the rvialry stimuli
        draw on each flip. This is handy if you want to do some normal psychopy
        stuff (e.g. participant instructions) before/after beginning the main
        loop, during which everything is event-driven.
        """
        win = visual.Window(
            size = [400, 400],
            fullscr = False,
            units = "pix",
            winType = 'pyglet'
        )
        self._setup_stims(win)
        timeout = False
        while (not self._shutdown) and (not timeout):
            win.flip()
            timeout = (time.time() - self._start_t) > self.config.duration
        win.close()
