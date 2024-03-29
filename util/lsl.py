from pylsl import StreamInlet, resolve_stream
import numpy as np
import asyncio

from ._messages import SampleMessage
from ._rate import Rate
import labgraph as lg


class LSLPollerConfig(lg.Config):
    type: str = 'EEG'
    sfreq: float = 500.
    downsample: int = 1

class LSLPollerNode(lg.Node):

    OUTPUT = lg.Topic(SampleMessage)
    config: LSLPollerConfig

    def setup(self) -> None:
        self._shutdown = False

    def setup(self) -> None:
        self.streams = resolve_stream('type', self.config.type)
        self.inlet = StreamInlet(self.streams[0])

    @lg.publisher(OUTPUT)
    async def lsl_subscriber(self) -> lg.AsyncPublisher:
        rate = Rate(self.config.sfreq)
        count = 0
        while True:
            sample, t = self.inlet.pull_sample()
            t += self.inlet.time_correction() # map timestamp to local clock
            if t is not None:
                count += 1
                x = np.array(sample)
                if count % self.config.downsample == 0:
                    yield self.OUTPUT, SampleMessage(timestamp = t, data = x)
                await rate.sleep()
