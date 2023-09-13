from psychopy import visual

def _display_text(win, txt):
    msg = visual.TextStim(
        win,
        text = txt,
        pos = (0,0),
        wrapWidth = win.size[0]
        )
    msg.draw()
    win.flip()

def _wait_for_spacebar(kb):
    kb.waitKeys(keyList = ['space'], clear = True)

def _show_instructions(win, kb, msg):
    msg += '\n\n(Press the spacebar to continue.)'
    _display_text(win, msg)
    _wait_for_spacebar(kb)


def show_opening_instructions(win, kb):

    msg = '''
    Welcome, and thank you for particpating in our study!
    '''
    _show_instructions(win, kb, msg)

    msg = '''
    In this experiment, we will present different images to each of your eyes.

    When this happens, your brain has to resolve the conflict between the two
    competing images. This is called "binocular rivalry."
    '''
    _show_instructions(win, kb, msg)

    msg = '''
    The brain usually resolves this conflict by "supressing" one of the images,
    letting the other image be the "dominant" image for a while.

    It will look like one image (the dominant one) is covering the other.
    '''
    _show_instructions(win, kb, msg)

    msg = '''
    But which image is dominant switches regularly. We are interested in how
    often your brain switches between images and whether we can predict
    the time of these perceptual switches from your heart rate.
    '''
    _show_instructions(win, kb, msg)

    msg = '''
    You will view two such rival stimuli for 20 minutes. Each time the dominant
    image switches, please let us know by pressing a button.

    Please press the LEFT arrow key when the RED image is newly dominant,
    and the RIGHT arrow key when the BLUE image is dominant.
    '''
    _show_instructions(win, kb, msg)

    msg = '''
    Sometimes you will see a mixture between both images. This is expected.
    Just keep track of which image is currently covering *more* of the screen,
    and let us know every time it switches.
    '''
    _show_instructions(win, kb, msg)

    msg = '''
    If you have any questions, please ask the experimenter now!
    '''
    _show_instructions(win, kb, msg)

    msg = '''
    Remember RED = LEFT arrow and BLUE = RIGHT arrow.
    '''
    _show_instructions(win, kb, msg)

def show_midpoint_instructions(win, kb):
    msg = '''
    You have completed the first task!
    '''
    _show_instructions(win, kb, msg)
    msg = '''
    On each trial of the next task, you will see two pulsating circles on the screen.

    One of the circles will pulse in synchrony with your heartbeat,
    and the other will pulse at random times.
    '''
    _show_instructions(win, kb, msg)
    msg = '''
    You will see the circles side-by-side for 10 seconds,
    and then you'll be asked which you thought was in sync with your heart.
    '''
    _show_instructions(win, kb, msg)
    msg = '''
    Please ask the experimenter if you have any questions.

    Otherwise, you may begin by pressing space.
    '''
    _show_instructions(win, kb, msg)

def show_closing_instructions(win, kb):
    msg = '''
    You have completed the experiment!
    '''
    _show_instructions(win, kb, msg)
    msg = '''
    Thank you for participating.

    Please let the experimenter know you're done.
    '''
    _show_instructions(win, kb, msg)

def get_2AFC(win, kb):
    msg = '''
    Which circle was synchronized to your heartbeat?

    Press the left arrow key for "left" and right arrow for "right."
    '''
    _display_text(win, msg)
    keys = kb.waitKeys(keyList = ['left', 'right'], clear = True)
    resp = keys[0].name
    return resp
