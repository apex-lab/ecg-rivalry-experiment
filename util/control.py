from scipy.stats import norm
from collections import deque
import numpy as np
import asyncio

from typing import Deque
from pylsl import local_clock

from ._messages import DisplayMessage, FloatMessage
import labgraph as lg

class ControlState(lg.State):
    # data buffer
    last_t_since: float = 0.
    last_ibi: float = 0.

class ControlConfig(lg.Config):
    systole_lag: float = .210 # seconds after R-peak to define as systole
    scale: float = 0.25/4 # roughly 1/4 intended stimulus duration

class Control(lg.Node):
    '''
    controls state of rivalry stimuli based on time since last detected R-peak
    '''
    INPUT = lg.Topic(FloatMessage)
    OUTPUT = lg.Topic(DisplayMessage)

    state: ControlState
    config: ControlConfig

    def size_func(self, t, phase):
        '''
        determines stimulus size as a function of time since R-peak
        '''
        m = phase # in ms relative to R-peak
        w = self.config.scale
        sz = norm.pdf(t, loc = m, scale = w) / norm.pdf(m, loc = m, scale = w)
        return sz

    @lg.subscriber(INPUT)
    @lg.publisher(OUTPUT)
    async def map_to_size(self, message: FloatMessage) -> lg.AsyncPublisher:
        '''
        Receives a new observation of raw time series, and yields an
        observation of the bandpass filtered time series.
        '''
        t = message.timestamp
        time_since_rpeak = message.data
        if time_since_rpeak == 0.:
            self.state.last_ibi = self.state.last_t_since
        self.state.last_t_since = time_since_rpeak

        # compute sizes of syncronous and asyncronous stimulus
        sz_sync = self.size_func(time_since_rpeak, self.config.systole_lag)
        async_lag = self.config.systole_lag + (self.state.last_ibi / 2)
        sz_async = self.size_func(time_since_rpeak, async_lag)

        yield self.OUTPUT, DisplayMessage(
            timestamp = t,
            sz_sync = sz_sync, sz_async = sz_async,
            process_t = local_clock()
            )
