import neurokit2 as nk
import numpy as np
import asyncio
from pylsl import local_clock

from ._messages import SampleMessage
from ._rate import Rate
import labgraph as lg

class ECGState(lg.State):
    idx: int = 0
    ecg: np.array = None

class ECGConfig(lg.Config):
    sfreq: float = 100.
    heart_rate: float = 60.

class ECGSimulator(lg.Node):
    '''
    Simulates a live ECG recording timestamped with the LSL local clock.
    '''
    OUTPUT = lg.Topic(SampleMessage)

    state: ECGState
    config: ECGConfig

    def setup(self) -> None:
        self.state.ecg = nk.ecg_simulate(
            duration = int(5),
            sampling_rate = int(self.config.sfreq),
            heart_rate = int(self.config.heart_rate)
            )
        self._shutdown = False

    def cleanup(self) -> None:
        #self._shutdown = True
        return

    def get_ecg(self, idx):
        i = idx % (self.state.ecg.shape[0] - 1)
        return np.array([self.state.ecg[i]])

    @lg.publisher(OUTPUT)
    async def simulate(self) -> lg.AsyncPublisher:
        rate = Rate(self.config.sfreq)
        while not self._shutdown:
            self.state.idx += 1
            ecg = self.get_ecg(self.state.idx)
            t = local_clock()
            yield self.OUTPUT, SampleMessage(timestamp = t, data = ecg)
            await rate.sleep()
