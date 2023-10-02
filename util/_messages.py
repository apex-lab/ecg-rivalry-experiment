import numpy as np
import labgraph as lg


class SampleMessage(lg.TimestampedMessage):
    '''
    Raw data samples should be communicated in this
    format for logging.
    '''
    #timestamp: float
    data: np.ndarray

class StringMessage(lg.TimestampedMessage):
    '''
    For timestamped event codes, which can be aligned
    against the raw data samples.
    '''
    # timestamp: float
    data: str

class FloatMessage(lg.TimestampedMessage):
    '''
    Once we isolate the ECG channel for processing, ECG and its
    derivatives can subsequently be passed as a single float
    instead of an array.
    '''
    # timestamp: float
    data: float

class DisplayMessage(lg.TimestampedMessage):
    '''
    Values in [0., 1.] to control the size of the rivalry stimuli
    '''
    # timestamp: float
    sz_sync: float
    sz_async: float
    process_t: float

class ExperimentEventMessage(lg.TimestampedMessage):
    # timestamp: float
    key: str
    key_t: float
    sync_side: str
