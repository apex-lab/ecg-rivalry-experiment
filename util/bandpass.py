from scipy.signal import butter
from collections import deque
import numpy as np
import asyncio

from typing import Deque

from ._messages import SampleMessage, FloatMessage
import labgraph as lg

class BandPassState(lg.State):
    # data buffers
    xs: Deque[float] = None
    ys: Deque[float] = None

class BandPassConfig(lg.Config):
    # filter specifications
    low_cutoff: float = .1
    high_cutoff: float = 15.
    sfreq: float = 100.
    order: int = 1
    # index from which to pull data from SampleMessage
    ch_idx: int = 0
    convert_microV_to_mV: bool = False

class BandPass(lg.Node):
    '''
    an online butterworth filter
    '''
    INPUT = lg.Topic(SampleMessage)
    OUTPUT = lg.Topic(FloatMessage)

    state: BandPassState
    config: BandPassConfig

    def setup(self) -> None:
        b, a = butter(
            self.config.order,
            [self.config.low_cutoff, self.config.high_cutoff],
            btype = 'bandpass',
            output = 'ba',
            fs = self.config.sfreq
            )
        self.state.xs = deque([0] * len(b), maxlen = len(b))
        self.state.ys = deque([0] * (len(a) - 1), maxlen = len(a) - 1)
        self.b = b
        self.a = a

    @lg.subscriber(INPUT)
    @lg.publisher(OUTPUT)
    async def filter(self, message: SampleMessage) -> lg.AsyncPublisher:
        '''
        Receives a new observation of raw time series, and yields an
        observation of the bandpass filtered time series.
        '''
        t = message.timestamp
        x = message.data[self.config.ch_idx] # pull out data channel
        if not np.isfinite(x):
            x = self.state.xs[-1] # handle NaNs
        if self.config.convert_microV_to_mV:
            x *= 1e3
        a = self.a
        b = self.b
        self.state.xs.appendleft(x)
        y = np.dot(b, self.state.xs) - np.dot(a[1:], self.state.ys)
        y = y / a[0]
        self.state.ys.appendleft(y)
        yield self.OUTPUT, FloatMessage(timestamp = t, data = y)
