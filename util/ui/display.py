from dataclasses import field
from itertools import product
from typing import List, Tuple
import numpy as np
import asyncio
import time

from psychopy import monitors, visual, core
from ._gratings import make_gratings
from ._instructions import show_opening_instructions
from ._input import get_keyboard

from .._messages import DisplayMessage, ExperimentEventMessage
import labgraph as lg

class DisplayState(lg.State):
    sync_color: str = ''
    red_step: int = 0
    blue_step: int = 0
    autoDraw: bool = True
    key_list: List[str] = field(default_factory = list)
    ev_list: List[str] = field(default_factory = list)

class DisplayConfig(lg.Config):
    # controls granularity of stimuli
    n_steps: int = 10
    duration: float = 30. # seconds
    kb_name: str = 'Dell Dell USB Entry Keyboard'

class Display(lg.Node):
    """
    This node sets up psychopy stims, signals when it is ready and changes displayed
    stims according to events received on the specified topic.
    """
    DISPLAY_TOPIC = lg.Topic(DisplayMessage)
    EXPERIMENT_EVENTS = lg.Topic(ExperimentEventMessage)

    state: DisplayState
    config: DisplayConfig

    def setup(self) -> None:
        self._stims = None
        self._shutdown = False
        self._fixation = None
        self.state.sync_color = np.random.choice(['red', 'blue'])
        self.kb = get_keyboard(self.config.kb_name)

    def cleanup(self) -> None:
        """
        This function is called when a NormalTermination is raised, so we set relevant
        shutdown flags here. We can use this to break out of infinite loops.
        """
        self._shutdown = True

    def _setup_stims(self, win: visual.Window) -> np.ndarray:
        """
        Pre-generate rivalry stimuli, since making the custom gratings is slow.

        This cannot be done in the `setup` function because the window needs to be
        available, and psychopy needs the window to be created in the "main" thread.
        """
        self._fixation = visual.TextStim(win, text = '+', color = "white", pos = (0, 0))
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
        if self.state.sync_color == 'red':
            red_step = self._val_to_steps(message.sz_sync)
            blue_step = self._val_to_steps(message.sz_async)
        else:
            red_step = self._val_to_steps(message.sz_async)
            blue_step = self._val_to_steps(message.sz_sync)
        # turn off autodraw for old stim
        try:
            self._stims[self.state.red_step, self.state.blue_step].autoDraw = False
            self._fixation.autoDraw = False
        except:
            None
        # and turn it on for new stim
        self.state.red_step = red_step
        self.state.blue_step = blue_step
        try:
            self._stims[self.state.red_step, self.state.blue_step].autoDraw = self.state.autoDraw
            self._fixation.autoDraw = self.state.autoDraw
        except: # this is just for right at startup when some of these
            None # state vars don't exist yet


    @lg.publisher(EXPERIMENT_EVENTS)
    async def event_listener(self):
        while not self._shutdown:

            ## handle start and finish events
            if self.state.ev_list:
                ev_name = self.state.ev_list.pop(0)
                yield self.EXPERIMENT_EVENTS, ExperimentEventMessage(
                                            timestamp = time.time(),
                                            key = ev_name,
                                            key_t = float(core.getAbsTime()),
                                            sync_color = self.state.sync_color
                                            )
            # handle user input events
            if self.state.key_list:
                key_pressed = self.kb.getKeys(
                    keyList = self.state.key_list,
                    waitRelease = False,
                    clear  = True
                    )
            else:
                key_pressed = []
            if key_pressed:
                yield self.EXPERIMENT_EVENTS, ExperimentEventMessage(
                                            timestamp = time.time(),
                                            key = key_pressed[0].name,
                                            key_t = key_pressed[0].tDown,
                                            sync_color = self.state.sync_color
                                            )
            await asyncio.sleep(.05)

    @lg.main
    def display(self):
        """
        This function runs in the main thread and sets up required psychopy objects.

        After initial setup is done, it loops until signaled to shutdown, and flips
        the psychopy frame. At every frame flip, the stims with `autoDraw` set to True
        are displayed.
        - Note that frame flips are inherently throttled by screen refresh rates, so
          this is not a tight loop and does not need to manually sleep between flips.

        You can toggle self.state.autoDraw to control whether the rival stimuli
        draw on each flip. This is handy if you want to do some normal psychopy
        stuff (e.g. participant instructions) before/after beginning the main
        loop, during which everything is event-driven.
        """
        win = visual.Window( # must be started here in main thread
            size = [1000, 1000],
            fullscr = False,
            units = 'pix',
            winType = 'pyglet'
        )

        # orient the subject
        show_opening_instructions(win, self.kb)

        # start main experiment
        self._setup_stims(win)
        timeout = False
        clock = core.Clock()
        self.state.key_list = ['left', 'right']
        self.state.ev_list.append('start')
        clock.reset(0.)
        while (not self._shutdown) and (not timeout):
            self._fixation.draw()
            win.flip()
            timeout = clock.getTime() > self.config.duration
        self.state.ev_list.append('end')
        while self.state.ev_list: # flush event list before closing
            time.sleep(.1)  # so that all events are marked in log
        win.close()
        raise lg.NormalTermination()
