from dataclasses import field
from itertools import product
from typing import List, Tuple
import numpy as np
import asyncio
import time
from pylsl import local_clock

from psychopy import monitors, visual, core
from ._gratings import make_gratings
from ._instructions import show_opening_instructions
from ._input import get_keyboard

from .._messages import DisplayMessage, ExperimentEventMessage
import labgraph as lg

class DisplayState(lg.State):
    sync_side: str = ''
    left_step: int = 0
    right_step: int = 0
    autoDraw_rivalry: bool = False
    autoDraw_disc: bool = False
    key_list: List[str] = field(default_factory = list)
    ev_list: List[str] = field(default_factory = list)

class DisplayConfig(lg.Config):
    # controls granularity of stimuli
    n_steps: int = 10
    duration: float = 30. # seconds
    trials: int = 5
    trial_dur: float = 10.
    kb_name: str = 'Dell Dell USB Keyboard'

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
        self.state.sync_side = np.random.choice(['left', 'right'])
        self.kb = get_keyboard(self.config.kb_name)

    def cleanup(self) -> None:
        """
        This function is called when a NormalTermination is raised, so we set
        relevant shutdown flags here. We can use this to break out of infinite
        loops.
        """
        self._shutdown = True

    def _setup_stims(self, win: visual.Window) -> np.ndarray:
        """
        Pre-generate rivalry stimuli, since making the custom gratings is slow.

        This cannot be done in the `setup` function because the window needs to
        be available, and psychopy needs the window to be created in the
        "main" thread.
        """
        self._fixation = visual.TextStim(
            win, text = '+', color = "white", pos = (0, 0)
            )
        n_steps = self.config.n_steps

        # draw gratings for each step size
        self._stims = np.empty((n_steps, n_steps), dtype = object)
        steps = np.linspace(10, 5, n_steps)
        for i, j in product(range(n_steps), range(n_steps)):
            self._stims[i,j] = make_gratings(
                win, red_cycles = steps[i], blue_cycles = steps[j]
            )

        # draw circles on each side of screen for each step size
        quarter_width = win.size[0]//4
        left_pos = (0 - 2*quarter_width//3, 0)
        right_pos = (0 + 2*quarter_width//3, 0)
        min_radius = quarter_width//8
        max_radius = quarter_width//4
        steps = np.linspace(min_radius, max_radius, n_steps)
        self._left_circle = np.empty(n_steps, dtype = object)
        self._right_circle = np.empty(n_steps, dtype = object)
        for i, radius in enumerate(steps):
            self._left_circle[i] = visual.Circle(
                win,
                radius = radius,
                pos = left_pos,
                fillColor = 'black'
                )
            self._right_circle[i] = visual.Circle(
                win,
                radius = radius,
                pos = right_pos,
                fillColor = 'black'
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
        if self.state.sync_side == 'left': # red is on the left eye
            left_step = self._val_to_steps(message.sz_sync)
            right_step = self._val_to_steps(message.sz_async)
        else:
            left_step = self._val_to_steps(message.sz_async)
            right_step = self._val_to_steps(message.sz_sync)
        try: # turn off autodraw for old stim
            self._stims[self.state.left_step, self.state.right_step].autoDraw = False
            self._fixation.autoDraw = False
            self._left_circle[self.state.left_step].autoDraw = False
            self._right_circle[self.state.right_step].autoDraw = False
        except: # _setup_stims hasn't run yet
            None
        # and turn it on for new stim
        self.state.left_step = left_step
        self.state.right_step = right_step
        try:
            # if currently doing rivalry task, autodraw rivalry gratings
            self._stims[self.state.left_step, self.state.right_step].autoDraw = \
                                                    self.state.autoDraw_rivalry
            self._fixation.autoDraw = self.state.autoDraw_rivalry
            # but if doing the discrimination task, autodraw circle stim
            self._left_circle[self.state.left_step].autoDraw = \
                                                self.state.autoDraw_disc
            self._right_circle[self.state.right_step].autoDraw = \
                                                self.state.autoDraw_disc
        except: # this is just for right at startup when some of these
            None # state vars don't exist yet


    @lg.publisher(EXPERIMENT_EVENTS)
    async def event_listener(self):
        while not self._shutdown:

            ## handle start and finish events
            if self.state.ev_list:
                ev_name = self.state.ev_list.pop(0)
                yield self.EXPERIMENT_EVENTS, ExperimentEventMessage(
                                            timestamp = local_clock(),
                                            key = ev_name,
                                            key_t = float(core.getAbsTime()),
                                            sync_side = self.state.sync_side
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
                                            timestamp = local_clock(),
                                            key = key_pressed[0].name,
                                            key_t = key_pressed[0].tDown,
                                            sync_side = self.state.sync_side
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
            size = [1920, 1080],
            fullscr = False,
            allowGUI = False,
            screen = -1,
            units = 'pix',
        )

        # orient the subject
        show_opening_instructions(win, self.kb)

        # start main experiment
        self._setup_stims(win)
        timeout = False
        clock = core.Clock()
        self.state.key_list = ['left', 'right']
        self.state.ev_list.append('start_rivalry')
        self.state.autoDraw_rivalry = True
        clock.reset(0.)
        while not timeout:
            self._fixation.draw()
            win.flip()
            timeout = clock.getTime() > self.config.duration
        self.state.key_list = [] # stop listening for keys in event loop
        self.state.ev_list.append('end_rivalry')
        self.state.autoDraw_rivalry = False
        core.wait(.05)

        # introduce heartbeat discrimination task
        #show_midpoint_instructions(win, self.kb)

        for trial in range(1, self.config.trials + 1):
            self._fixation.draw()
            win.flip()
            core.wait(1.)
            self.state.autoDraw_disc = True
            self.state.sync_side = np.random.choice(['left', 'right'])
            self.state.ev_list.append('start_trial%d'%trial)
            clock.reset()
            while not (clock.getTime() > self.config.trial_dur):
                win.flip()
            self.state.ev_list.append('end_trial%d'%trial)
            self.state.autoDraw_disc = False
            core.wait(.05)
            #resp = get_2AFC(win, self.kb) # ask which side was syncronous
            #self.state.ev_list.append('resp_%s'%resp) # and record response


        #show_closing_instructions(win)
        win.close()
        raise lg.NormalTermination()
