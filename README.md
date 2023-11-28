This experiment implements a realtime R-peak detector to entrain binocular rivalry stimuli to sytolic and diastolic phases of participants' cardiac cycles, followed by a modified heartbeat discrimination task (to meausure interoceptive accuracy as it pertains to the experimental manipulation in the rivalry task). It uses [labgraph](https://github.com/facebookresearch/labgraph) and [Lab Streaming Layer](https://labstreaminglayer.org) (LSL) for realtime ECG processing. We recorded ECG with a TMSi SAGA, but you can use whatever LSL-compatible hardware you'd like with minimal modification.

1. `environment.yml` contains the conda environment specification used to run the experiment. Before running, create this environment using conda. (We provided the specification with the exact package versions used on our Ubuntu 20.4 machine, since the labgraph depdendencies ended up being somewhat tricky. You might need to use different package versions for your own hardware if you intend to run this code. I apologize in advance that will probably require some troubleshooting on your end.)
2. `graph.py` is the main experiment code. Most of the settings you'd need to change for your own setup (e.g. ECG sampling rate) can be found there, and you can toggle between using real and simulated ECG with a hardcoded variable. If you're using real ECG, the ECG data needs to be streaming over LSL before you run the script.
3. `bidsify.py` converts the log files produced by `graph.py` to [BIDS format](https://bids-specification.readthedocs.io/en/stable/) for posterity. **Note:** Before saving the ECG data, this script compensates for the known hardware delay of our ECG amplifier, **which we have hardcoded in! You'd need to change that for you own system's delay.** (Incidentally, the delay we compensate for is the same as the delay recorded in the `'offset_mean'` parameter of the LSL stream produced by the TMSi SDK, but that's only the case because I was the one that contributed the [LSL functionality](https://gitlab.com/tmsi/tmsi-python-interface/-/blob/8babeb7b73460d9cdd7912dde3c10597f2729e31/TMSiFileFormats/file_formats/lsl_stream_writer.py) to that codebase -- so that estimate was actually measured with our hardware. I recommend measuring this delay yourself.) 
