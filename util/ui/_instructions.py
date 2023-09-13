from psychopy import visual

def _display_text(win, txt):
    msg = visual.TextStim(
        win,
        text = txt,
        pos = (0,0)
        )
    msg.draw()
    win.flip()

def _wait_for_spacebar(kb):
    kb.waitKeys(keyList = ['space'], clear = True)

def show_opening_instructions(win, kb):

    msg = '''
    Welcome, and thank you for particpating in our study!

    (Press the spacebar to continue.)
    '''
    _display_text(win, msg)
    _wait_for_spacebar(kb)

    msg = '''
    In this experiment, we will present different images to each of your eyes.

    When this happens, your brain has to resolve the conflict between the two
    competing images. This is called "binocular rivalry."

    (Press the spacebar to continue.)
    '''
    _display_text(win, msg)
    _wait_for_spacebar(kb)

    msg = '''
    The brain usually resolves this conflict by "supressing" one of the images,
    letting the other image be the "dominant" image for a while.

    It will look like one image (the dominant one) is covering the other.

    (Press the spacebar to continue.)
    '''
    _display_text(win, msg)
    _wait_for_spacebar(kb)

    msg = '''
    But which image is dominant switches regularly. We are interested in how
    often your brain switches between images and whether we can predict
    the time of these perceptual switches from your heart rate.

    (Press the spacebar to continue.)
    '''
    _display_text(win, msg)
    _wait_for_spacebar(kb)

    msg = '''
    You will view two such rival stimuli for 20 minutes. Each time the dominant
    image switches, please let us know by pressing a button.

    Please press the LEFT arrow key when the RED image is newly dominant,
    and the RIGHT arrow key when the BLUE image is dominant.

    (Press the spacebar to continue.)
    '''
    _display_text(win, msg)
    _wait_for_spacebar(kb)

    msg = '''
    Sometimes you will see a mixture between both images. This is expected.
    Just keep track of which image is currently covering *more* of the screen,
    and let us know every time it switches.

    (Press the spacebar to continue.)
    '''
    _display_text(win, msg)
    _wait_for_spacebar(kb)

    msg = '''
    If you have any questions, please ask the experimenter now!

    (Press the spacebar to continue.)
    '''
    _display_text(win, msg)
    _wait_for_spacebar(kb)

    msg = '''
    Remember RED = LEFT arrow and BLUE = RIGHT arrow.

    You may now begin the experiment. Please press the space bar to start.
    '''
    _display_text(win, msg) # main script will wait for spacebar
    _wait_for_spacebar(kb)
