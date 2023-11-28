import numpy as np
import pandas as pd
import h5py
import json
import re
import os
from mne_bids import BIDSPath
from mne_bids.write import (
    _participants_tsv,
    _participants_json,
    make_dataset_description
)
import argparse

SOURCE_DIR = 'logs'
BIDS_ROOT = 'bids_dataset'
DELAY_SAMPLES = 3

_stringify = lambda s: re.findall("'(\w+)'", str(s))[0] # rms weird encoding
stringify = lambda s: s if isinstance(s, str) else _stringify(s)

def read_physio(f, delay_samples = 0):
    '''
    Arguments
    ---------
    f : h5py.File
        The h5 database object containing experiment logs.
    delay_samples : int
        The hardware delay in samples. This is something you have
        to measure on your own hardware. (e.g. Our TMSi SAGA amplifier has
        a delay of ~34 ms, and our sampling rate was 100, so for us this
        will be delay_samples = 3.)
    '''
    ecg_raw = f['ecg_raw'][:]
    t_ecg = np.vectorize(lambda x: x[0])(ecg_raw).astype(float)
    ecg = np.vectorize(lambda x: x[1][0])(ecg_raw).astype(float)
    ecg /= 1e3 # convert units from microV to mV
    ecg = pd.DataFrame({'time': t_ecg, 'ecg': ecg})

    stim_size = f['stim_size'][:]
    t_stim = np.vectorize(lambda x: x[0])(stim_size).astype(float)
    sync_stim = np.vectorize(lambda x: x[1])(stim_size).astype(float)
    async_stim = np.vectorize(lambda x: x[2])(stim_size).astype(float)
    stims = pd.DataFrame({
        'time': t_stim,
        'synchronous': sync_stim,
        'asynchronous': async_stim
    })
    # compensate for hardware delay
    stims['synchronous'] = np.roll(stims.synchronous, delay_samples)
    stims['asynchronous'] = np.roll(stims.asynchronous, delay_samples)

    # merge on timestamp
    physio = pd.merge(ecg, stims, on = 'time')

    # de-jitter timestamps
    idx = np.arange(0, physio.time.size, 1)[:, None]
    X = np.concatenate((np.ones_like(idx), idx), axis = 1)
    y = physio.time
    mapping = np.linalg.lstsq(X, y, rcond = -1)[0]
    time_stamps = mapping[0] + mapping[1] * idx
    time_stamps = time_stamps[:, 0]
    physio.time = time_stamps

    return physio

def read_rivalry_events(f, run = 0):
    '''
    Arguments
    ---------
    f : h5py.File
        The h5 database object containing experiment logs.
    run : int
        Which rivalry block/run to read.
    '''
    evs = f['experiment_events'][:]
    t_event = np.vectorize(lambda x: x[0])(evs).astype(float)
    events = np.vectorize(lambda x: x[1])(evs)
    events = [stringify(ev) for ev in events]
    sync_side = np.vectorize(lambda x: x[-1])(evs)
    sync_side = np.array([stringify(ss) for ss in sync_side])
    events = pd.DataFrame({'onset': t_event, 'sync_side': sync_side, 'key': events})

    events['sync_dominant'] = events.key == sync_side
    events['dominant'] = events.sync_dominant.replace({
        True: 'synchronous',
        False: 'asynchronous'
    })

    # remove double keypresses
    same_as_next = events.key[:-1].to_numpy() == events.key[1:].to_numpy()
    same_as_prev = np.concatenate([[False], same_as_next])
    events = events[~same_as_prev]

    # and then calculate dominance durations
    durations = events.onset.diff()
    durations.iloc[[1, -1]] = np.nan
    durations = pd.concat([durations, pd.Series([np.nan])])
    durations = durations.reset_index(drop = True)
    events.insert(1, 'duration', durations)
    event_types = events.key.replace({'left': 'keypress', 'right': 'keypress'})
    events.insert(0, 'trial_type', event_types)

    # crop to just current run
    events = events.reset_index()
    start_idx = events.index[events.trial_type == 'start_rivalry'][run]
    end_idx = events.index[events.trial_type == 'end_rivalry'][run]
    events = events.iloc[start_idx:(end_idx + 1)]

    # clean up
    events = events[[
        'onset', 'duration', 'trial_type',
        'sync_side', 'key', 'dominant'
        ]]
    events.iloc[0, -2:] = pd.NA
    events.iloc[:2, 1] = pd.NA
    events.iloc[-2, 3] = pd.NA
    events.iloc[-1:, -3:] = pd.NA

    return events

def read_discrimination_events(f):
    evs = f['experiment_events'][:]
    t_event = np.vectorize(lambda x: x[0])(evs).astype(float)
    events = np.vectorize(lambda x: x[1])(evs)
    events = [stringify(ev) for ev in events]
    sync_side = np.vectorize(lambda x: x[-1])(evs)
    sync_side = np.array([stringify(ss) for ss in sync_side])
    events = pd.DataFrame({'onset': t_event, 'sync_side': sync_side, 'key': events})
    start_idx = events.index[events.key == 'start_trial1'][0] # first trial
    events = events.iloc[start_idx:]
    events = events.reset_index()

    assert(events.shape[0] % 3 == 0)
    trial_starts = events[events.index % 3 == 0]
    trial_starts = trial_starts.reset_index()
    trial_ends = events[events.index % 3 == 1]
    trial_ends = trial_ends.reset_index()
    responses = events[events.index % 3 == 2]
    responses = responses.reset_index()
    responses = responses.key.str.split('_', expand = True).iloc[:,1]
    trial_starts['duration'] = trial_ends.onset - trial_starts.onset
    events = trial_starts[['onset', 'duration', 'sync_side']]
    events['response'] = responses
    events['correct'] = events.response == events.sync_side

    return events


def crop(events, physio):
    '''
    crops physio to a task block
    '''
    t_start = events.onset.iloc[0]
    if np.isfinite(events.duration.iloc[-1]):
        t_stop = events.onset.iloc[-1] + events.duration.iloc[-1]
    else:
        t_stop = events.onset.iloc[-1]
    physio = physio[(physio.time >= t_start) & (physio.time <= t_stop)]
    events.onset -= t_start
    physio.time -= t_start
    return events, physio

def save(events, physio, sub, task, run, srate = 100):
    ## save physio data
    chan_names = ['ecg', 'synchronous', 'asynchronous']
    bids_path = BIDSPath(
        root = BIDS_ROOT,
        subject = sub,
        datatype = 'beh',
        task = task,
        run = run,
        suffix = 'physio',
        extension = '.tsv.gz'
    )
    # prepare sidecar file
    info = {
        'Manufacturer': 'TMSi SAGA',
        'PowerLineFrequency': 60.,
        'SamplingFrequency': srate,
        'RecordingDuration': physio.time.iloc[-1],
        'StartTime': physio.time.iloc[0],
        'Columns': chan_names
    }
    for chan in chan_names:
        chan_info = {}
        chan_info['Units'] = 'mV' if chan == 'ecg' else 'n/a'
        chan_info['low_cutoff'] = 'n/a'
        chan_info['high_cutoff'] = 'n/a'
        info[chan] = chan_info
    # create directory structure
    bids_path.mkdir()
    f = str(bids_path.fpath)
    # write data
    physio = physio[chan_names]
    physio.to_csv(f, sep = '\t', index = False, header = False, na_rep = 'n/a')
    # write sidecar file
    json_fpath = f.replace('tsv.gz', 'json')
    json_f = open(json_fpath, "w")
    json.dump(info, json_f, indent = 4)
    json_f.close()

    ## write events file
    events_f = f.replace('_physio.tsv.gz', '_events.tsv')
    events.to_csv(events_f, sep = '\t', index = False, na_rep = 'n/a')

    ## write dataset description files if needed
    # write dataset description files
    readme_fname = os.path.join(bids_path.root, 'README')
    participants_tsv_fname = os.path.join(bids_path.root, 'participants.tsv')
    participants_json_fname = participants_tsv_fname.replace('.tsv', '.json')
    # make a class to trick MNE-BIDS's highly unecessary call to MNE raw object
    class Dumb:
        def get(self, some_string, none):
            return None
    class Dumber:
        def __init__(self):
            self.info = Dumb()
    dummy_raw = Dumber()
    _participants_tsv(dummy_raw, bids_path.subject, participants_tsv_fname)
    _participants_json(participants_json_fname, True)
    make_dataset_description(path = bids_path.root, name = 'ecg-rivalry')

def main(sub):
    # find subject's log file
    fnames = os.listdir(SOURCE_DIR)
    fname = [f for f in fnames if 'sub-%s_'%sub in f]
    assert(len(fname) == 1)
    fname = fname[0]
    fpath = os.path.join(SOURCE_DIR, fname)
    f = h5py.File(fpath, 'r')

    physio = read_physio(f, DELAY_SAMPLES)

    for block in range(2):
        events = read_rivalry_events(f, block)
        events, physio_cropped = crop(events, physio)
        save(events, physio_cropped, sub, 'rivalry', block + 1)

    events = read_discrimination_events(f)
    events, physio_cropped = crop(events, physio)
    save(events, physio_cropped, sub, 'discrimination', 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('sub', type = str)
    args = parser.parse_args()
    main(args.sub)
