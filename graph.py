from typing import Tuple
from time import strftime
from typing import Dict

from util.ecg import ECGSimulator, ECGConfig
from util.bandpass import BandPass, BandPassConfig
from util.qrs import QRSDetector, QRSDetectorConfig
from util.control import Control, ControlConfig
from util.ui.display import Display
import labgraph as lg

SFREQ = 100.
ECG_CHANNEL = 0

class ProcessECG(lg.Graph):

    GENERATOR: ECGSimulator
    FILTER: BandPass
    DETECTOR: QRSDetector
    CONTROLLER: Control
    DISPLAY: Display

    def setup(self) -> None:

        self.GENERATOR.configure(
            ECGConfig(
                sfreq = SFREQ
            )
        )
        self.FILTER.configure(
            BandPassConfig(
                low_cutoff = .1,
                high_cutoff = 15.,
                sfreq = SFREQ,
                ch_idx = ECG_CHANNEL
            )
        )
        self.DETECTOR.configure(
            QRSDetectorConfig(
                sfreq = SFREQ
            )
        )
        self.CONTROLLER.configure(
            ControlConfig(
                sfreq = SFREQ
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
            't_since_qrs': self.DETECTOR.OUTPUT,
            'stim_size': self.CONTROLLER.OUTPUT
            }

# Entry point: run the Demo graph
if __name__ == "__main__":
    graph = ProcessECG()
    options = lg.RunnerOptions(
        logger_config = lg.LoggerConfig(
            output_directory = "./logs",
            recording_name = "ecg%s"%strftime("%Y%m%d-%H%M%S"),
        ),
    )
    runner = lg.ParallelRunner(graph = graph, options = options)
    runner.run()
