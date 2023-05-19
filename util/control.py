from scipy.stats import norm
from collections import deque
import numpy as np
import asyncio

from typing import Deque

from ._messages import DisplayMessage, FloatMessage
import labgraph as lg

class ControlState(lg.State):
    # data buffer
    buffer: Deque[float] = None

class ControlConfig(lg.Config):
    sfreq: float = 100
    delay1: float = .210 # seconds, meant to be syncronous with systole
    delay2: float = .600 # meant to come after systole
    scale: float = 0.25/4 # roughly 4x intended stimulus duration

class Control(lg.Node):
    '''
    controls state of rivalry stimuli based on time since last detected R-peak
    '''
    INPUT = lg.Topic(FloatMessage)
    OUTPUT = lg.Topic(DisplayMessage)

    state: ControlState
    config: ControlConfig

    def setup(self) -> None:
        lag = self.config.delay2 - self.config.delay1
        lag *= self.config.sfreq
        lag = int(lag)
        self.state.buffer = deque([0.] * lag, maxlen = lag)

    def size_func(self, t):
        '''
        determines stimulus size as a function of time since R-peak
        '''
        m = self.config.delay1
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
        sz = self.size_func(time_since_rpeak)
        self.state.buffer.append(sz)
        lag_sz = self.state.buffer[0]
        yield self.OUTPUT, DisplayMessage(timestamp = t, red = sz, blue = lag_sz)
