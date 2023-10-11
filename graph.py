from typing import Tuple
from time import strftime
from typing import Dict

from util.lsl import LSLPollerNode, LSLPollerConfig
from util.ecg import ECGSimulator, ECGConfig
from util.bandpass import BandPass, BandPassConfig
from util.qrs import QRSDetector, QRSDetectorConfig
from util.control import Control, ControlConfig
from util.ui.display import Display
import labgraph as lg

SIMULATE = False
ECG_CHANNEL = 0     # channel of LSL stream to use as ECG
SFREQ = 100.        # desired sampling rate
POLLING_RATE = 500. # lowest hardware rate of TMSi SAGA

if SIMULATE:
    ecg_args = dict(sfreq = SFREQ)
    ECGNode = ECGSimulator
    ECGConfig = ECGConfig
    convert = False
else:
    downsample = POLLING_RATE / SFREQ
    assert(int(downsample) == downsample) # can only downsample by integer
    ecg_args = dict(
        sfreq = POLLING_RATE,
        downsample = int(downsample)
    )
    ECGNode = LSLPollerNode
    ECGConfig = LSLPollerConfig
    convert = True

class Experiment(lg.Graph):

    GENERATOR: ECGNode
    FILTER: BandPass
    DETECTOR: QRSDetector
    CONTROLLER: Control
    DISPLAY: Display

    def setup(self) -> None:

        self.GENERATOR.configure(
            ECGConfig(**ecg_args)
        )
        self.FILTER.configure(
            BandPassConfig(
                low_cutoff = 5.,
                high_cutoff = 15.,
                sfreq = SFREQ,
                ch_idx = ECG_CHANNEL,
                convert_microV_to_mV = convert
            )
        )
        self.DETECTOR.configure(
            QRSDetectorConfig(
                sfreq = SFREQ
            )
        )
        self.CONTROLLER.configure(
            ControlConfig(
                systole_lag = .210 - .035 # minus 35 ms hardware delay
            )
        )

    # Connect outputs to inputs
    def connections(self) -> lg.Connections:
        return (
            (self.GENERATOR.OUTPUT, self.FILTER.INPUT),
            (self.FILTER.OUTPUT, self.DETECTOR.INPUT),
            (self.DETECTOR.OUTPUT, self.CONTROLLER.INPUT),
            (self.CONTROLLER.OUTPUT, self.DISPLAY.DISPLAY_TOPIC)
        )

    # Parallelization: Run nodes in separate processes
    def process_modules(self) -> Tuple[lg.Module, ...]:
        return (self.GENERATOR, self.FILTER, self.DETECTOR, self.CONTROLLER, self.DISPLAY)

    def logging(self) -> Dict[str, lg.Topic]:
        return {
            'ecg_raw': self.GENERATOR.OUTPUT,
            'ecg_filt': self.FILTER.OUTPUT,
            't_since': self.DETECTOR.OUTPUT,
            'stim_size': self.CONTROLLER.OUTPUT,
            'experiment_events': self.DISPLAY.EXPERIMENT_EVENTS,
            }

# Entry point: run the Demo graph
if __name__ == "__main__":
    sub_num = input('Enter subject number: ')
    sub_num = int(sub_num)
    sub = '%02d'%sub_num
    graph = Experiment()
    options = lg.RunnerOptions(
        logger_config = lg.LoggerConfig(
            output_directory = './logs', # label w/ subject number and datetime
            recording_name = 'sub-%s_%s'%(sub, strftime('%Y%m%d-%H%M%S')),
        ),
    )
    runner = lg.ParallelRunner(graph = graph, options = options)
    runner.run()
