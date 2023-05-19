import numpy as np
from collections import deque
import asyncio
from typing import Deque
from scipy.signal import find_peaks

from ._messages import FloatMessage
import labgraph as lg


class QRSDetectorState(lg.State):
    xs: Deque[float] = None
    samples_since_qrs: int = 0
    qrs_peak_value: float = .0
    noise_peak_value: float = .0
    threshold_value: float = .0

class QRSDetectorConfig(lg.Config):
    sfreq: float = 100
    findpeaks_limit: float = 0.35
    qrs_peak_filtering_factor: float = 0.125
    noise_peak_filtering_factor: float = 0.125
    qrs_noise_diff_weight: float = 0.25

class QRSDetector(lg.Node):
    '''
    An ECG QRS Detector using the Pan-Tomkins algorithm. Based on
    Michał Sznajder and Marta Łukowska's implementation, which can
    be found at https://doi.org/10.5281/zenodo.583770
    '''

    INPUT = lg.Topic(FloatMessage)
    OUTPUT = lg.Topic(FloatMessage)

    state: QRSDetectorState
    config: QRSDetectorConfig

    @property
    def buffer_size(self):
        '''
        parameters that scale with sample size are set as properties,
        proportionally matching the params in this implementation:
        https://doi.org/10.5281/zenodo.583770
        '''
        return int(.8 * self.config.sfreq)

    @property
    def integration_win(self):
        return int(.06 * self.config.sfreq)

    @property
    def findpeaks_spacing(self):
        return int(.2 * self.config.sfreq)

    @property
    def detection_window(self):
        return int((40/250) * self.config.sfreq)

    @property
    def refractory_period(self):
        return (120/250) * self.config.sfreq

    @property
    def t_since_qrs(self):
        return self.state.samples_since_qrs / self.config.sfreq

    def setup(self) -> None:
        self.state.xs = deque([0], self.buffer_size)

    def detect_qrs(self):
        '''
        Implements Pan-Tomkins algorithm:
        (1) Detects peaks in the data stored in buffer,
        (2) classifies peak as QRS or noise by comparing to adaptive threshold,
        (3) and adjusts adaptive threshold based on classification in (2).
        '''
        self.state.samples_since_qrs += 1
        if self.state.samples_since_qrs <= self.refractory_period:
            return

        ## peak detection:

        # Derivative - provides QRS slope information.
        ecg_deriv = np.ediff1d(self.state.xs)
        # Squaring - intensifies values received in derivative.
        ecg_deriv_sqr = ecg_deriv ** 2
        # Moving-window integration.
        integ_ecg = np.convolve(ecg_deriv_sqr, np.ones(self.integration_win))
        peak_idxs, _ = find_peaks(
            x = integ_ecg,
            height = self.config.findpeaks_limit,
            distance = self.findpeaks_spacing

        )
        peak_idxs = peak_idxs[peak_idxs > self.buffer_size - self.detection_window]
        peak_vals = integ_ecg[peak_idxs]

        if peak_vals.size == 0:
            return

        ## classify last peak as a real R-peak or as noise:

        last_peak = peak_vals[-1]
        if last_peak > self.state.threshold_value: # classify as real QRS
            self.state.samples_since_qrs = 0
            # keep running average of QRS peak height
            weight = self.config.qrs_peak_filtering_factor
            self.state.qrs_peak_value = weight * last_peak + \
                                    (1 - weight) * self.state.qrs_peak_value
        else:
            # keep running average of the noise peak heights
            weight = self.config.noise_peak_filtering_factor
            self.state.noise_peak_value = weight * last_peak + \
                                    (1 - weight) * self.state.noise_peak_value

        ## Adjust QRS detection threshold:

        self.state.threshold_value = self.state.noise_peak_value + \
                               self.config.qrs_noise_diff_weight * \
                               (self.state.qrs_peak_value - self.state.noise_peak_value)


    @lg.subscriber(INPUT)
    @lg.publisher(OUTPUT)
    async def process(self, message: FloatMessage) -> lg.AsyncPublisher:
        '''
        Receives a new observation of filtered ECG time series, and yields the
        time since the last detected R-peak.
        '''
        x = message.data
        t = message.timestamp
        self.state.xs.append(x)
        self.detect_qrs() # updates self.t_since_qrs
        yield self.OUTPUT, FloatMessage(timestamp = t, data = self.t_since_qrs)
