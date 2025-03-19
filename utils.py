import logging
import os
import pyo as pyo
from psychopy import prefs

prefs.hardware['audioLib'] = ['pyo']

from psychopy import sound, core, visual
import math
import random

print('Using %s(with %s) for sounds' % (sound.audioLib, sound.audioDriver))

from psychopy import core, event, visual, data, gui, misc
import glob, os, random, sys, gc, time, hashlib, subprocess
from math import *
from pygaze import libtime, libscreen
from pygaze.plugins import aoi


def setup_logging(log_file):
    # If a log file exists, remove it to start fresh.
    if os.path.exists(log_file):
        os.remove(log_file)

    # Create a logger for the experiment
    logger = logging.getLogger("InfantEyetracking")
    logger.setLevel(logging.INFO)

    # Configure logging to file
    fh = logging.FileHandler(log_file)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Also log to console for real-time feedback.
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger


def enterSubjInfo(expName, optionList):
    """ Brings up a GUI in which to enter all the subject info."""

    def inputsOK(optionList, expInfo):
        for curOption in sorted(optionList.items()):
            if curOption[1]['options'] != 'any' and expInfo[curOption[1]['name']] not in curOption[1]['options']:
                return [False, "The option you entered for " + curOption[1][
                    'name'] + " is not in the allowable list of options: " + str(curOption[1]['options'])]
        print("inputsOK passed")
        return [True, '']

    try:
        expInfo = misc.fromFile(expName + '_lastParams.pickle')
    except:
        expInfo = {}  # make the kind of dictionary that this gui can understand
        for curOption in sorted(optionList.items()):
            expInfo[curOption[1]['name']] = curOption[1]['default']
    # load the tips
    tips = {}
    for curOption in sorted(optionList.items()):
        tips[curOption[1]['name']] = curOption[1]['prompt']
    expInfo['dateStr'] = data.getDateStr()
    expInfo['expName'] = expName
    dlg = gui.DlgFromDict(expInfo, title=expName, fixed=['dateStr', 'expName'],
                          tip=tips)
    if dlg.OK:
        misc.toFile(expName + '_lastParams.pickle', expInfo)
        [success, error] = inputsOK(optionList, expInfo)
        if success:
            return [True, expInfo]
        else:
            return [False, error]
    else:
        core.quit()


def popupError(text):
    errorDlg = gui.Dlg(title="Error", pos=(200, 400))
    errorDlg.addText('Error: ' + text, color='Red')
    errorDlg.show()


def loadFilesMovie(directory, extension, fileType, win='', whichFiles='*', stimList=[]):
    """ Load all the pics and sounds"""
    path = os.getcwd()  # set path to current directory
    if isinstance(extension, list):
        fileList = []
        for curExtension in extension:
            fileList.extend(glob.glob(os.path.join(path, directory, whichFiles + curExtension)))
    else:
        fileList = glob.glob(os.path.join(path, directory, whichFiles + extension))
    fileMatrix = {}  # initialize fileMatrix  as a dict because it'll be accessed by picture names, cound names, whatver
    for num, curFile in enumerate(fileList):
        fullPath = curFile
        fullFileName = os.path.basename(fullPath)
        stimFile = os.path.splitext(fullFileName)[0]
        if fileType == "image":
            try:
                surface = pygame.image.load(fullPath)  # gets height/width of the image
                stim = visual.ImageStim(win, image=fullPath, mask=None, interpolate=True)
                fileMatrix[stimFile] = ((stim, fullFileName, num, surface.get_width(), surface.get_height(), stimFile))
            except:  # no pygame, so don't store the image dims
                stim = visual.ImageStim(win, image=fullPath, mask=None, interpolate=True)
                fileMatrix[stimFile] = ((stim, fullFileName, num, '', '', stimFile))
        elif fileType == "sound":
            soundRef = sound.Sound(fullPath)
            fileMatrix[stimFile] = ((soundRef))
        elif fileType == "winSound":
            soundRef = open(fullPath, "rb").read()
            fileMatrix[stimFile] = ((soundRef))
            fileMatrix[stimFile + '-path'] = fullPath  # this allows asynchronous playing in winSound.
        elif fileType == "movie":
            movie = visual.MovieStim(win, fullPath, noAudio=True)
            fileMatrix[stimFile] = ((movie))

    # check
    if stimList and set(fileMatrix.keys()).intersection(stimList) != set(stimList):
        popupError(str(set(stimList).difference(fileMatrix.keys())) + " does not exist in " + path + '\\' + directory)
    return fileMatrix


def loadFiles(directory, extension, fileType, win='', whichFiles='*', stimList=[]):
    """ Load all the pics and sounds"""
    path = os.getcwd()  # set path to current directory
    if isinstance(extension, list):
        fileList = []
        for curExtension in extension:
            fileList.extend(glob.glob(os.path.join(path, directory, whichFiles + curExtension)))
    else:
        fileList = glob.glob(os.path.join(path, directory, whichFiles + extension))
    fileMatrix = {}  # initialize fileMatrix  as a dict because it'll be accessed by picture names, cound names, whatver
    for num, curFile in enumerate(fileList):
        fullPath = curFile
        fullFileName = os.path.basename(fullPath)
        stimFile = os.path.splitext(fullFileName)[0]
        if fileType == "image":
            try:
                surface = pygame.image.load(fullPath)  # gets height/width of the image
                stim = visual.ImageStim(win, image=fullPath, mask=None, interpolate=True)
                fileMatrix[stimFile] = ((stim, fullFileName, num, surface.get_width(), surface.get_height(), stimFile))
            except:  # no pygame, so don't store the image dims
                stim = visual.ImageStim(win, image=fullPath, mask=None, interpolate=True)
                fileMatrix[stimFile] = ((stim, fullFileName, num, '', '', stimFile))
        elif fileType == "sound":
            soundRef = sound.Sound(fullPath)
            fileMatrix[stimFile] = ((soundRef))
        elif fileType == "winSound":
            soundRef = open(fullPath, "rb").read()
            fileMatrix[stimFile] = ((soundRef))
            fileMatrix[stimFile + '-path'] = fullPath  # this allows asynchronous playing in winSound.

    # check
    if stimList and set(fileMatrix.keys()).intersection(stimList) != set(stimList):
        popupError(str(set(stimList).difference(fileMatrix.keys())) + " does not exist in " + path + '\\' + directory)
    return fileMatrix


def buildScreenPsychoPy(screen, stimuli):
    """Adds psychopy stimuli to a screen"""
    """Stimuli can be a list or a single draw-able stimulus"""
    if type(stimuli).__name__ == "list":
        for curStim in stimuli:
            screen.screen.append(curStim)
    else:
        screen.screen.append
    return


def setAndPresentScreen(display, screen, duration=0):
    """Sets display with a given screen and displays that screen"""
    """duration can be set to a specific time to display screen for"""
    """otherwise, the function returns immediately (duration=0)"""
    display.fill(screen)
    if duration == 0:  # single frame
        display.show()
    else:
        display.show()
        # relies on pygaze's libtime module
        libtime.pause(duration)

def assign_shape_positions(shapes, possible_locations):
    """
    Randomly assigns each shape a location from the available list.
    The order of shapes is fixed, but their locations are randomized.
    
    Parameters:
      shapes: list of shape names (e.g., ['circle', 'cross', 'star', 't'])
      possible_locations: list of location dictionaries or tuples
      
    Returns:
      dict: Mapping of shape name to its assigned location.
    """
    if len(shapes) > len(possible_locations):
        raise ValueError("Not enough locations for the number of shapes.")
    locations_copy = possible_locations.copy()
    random.shuffle(locations_copy)
    shape_positions = {}
    for i, shape in enumerate(shapes):
        shape_positions[shape] = locations_copy[i]

    # also convert to AOIs for pygaze

    return shape_positions


def draw_static_shapes(preloaded_stimuli):
    """
    Draws preloaded static shape stimuli.
    """
    for stim in preloaded_stimuli.values():
        stim.draw()


def check_fixation(gaze_history, required_duration=0.5):
    """
    Given a list of gaze samples (with timestamps), return True if the fixation
    duration exceeds the required_duration.
    
    This is a stub: you may implement more robust fixation detection.
    """
    if not gaze_history:
        return False
    start_time = gaze_history[0][1]
    end_time = gaze_history[-1][1]
    return (end_time - start_time) >= required_duration


def psychopy_to_pygaze(psychopy_coord, screen_width=1920, screen_height=1080, y_offset=0, x_offset = 0):
    """
    Converts a position from PsychoPy (origin at center) to pygaze (origin at top left)
    
    Parameters:
      psychopy_coord: Tuple (x, y) in PsychoPy coordinates.
      screen_width: Width of the screen (default 1920).
      screen_height: Height of the screen (default 1080).
    
    Returns:
      Tuple (x', y') representing the center coordinate for pygaze.
    """
    x, y = psychopy_coord
    # Convert from center origin to top-left origin
    pyg_x = x + (screen_width / 2) - x_offset
    pyg_y = (screen_height / 2) - y - y_offset  # Flip y-axis (in psychopy, +y is up; in pygaze, +y is down)
    return (pyg_x, pyg_y)


class LoomAnimation:
    """
    Animation class that handles the looming, jiggling, and fade-back phases
    of shape animations.

    Parameters:
    -----------
    stim : psychopy.visual.ImageStim
        The stimulus to animate
    win : psychopy.visual.Window
        The window to display the animation in
    pos : tuple (x, y)
        The position of the stimulus in window coordinates
    current_shape : str
        The name/identifier of the shape being animated
    background_stimuli : dict
        Dictionary of {shape_name: stimulus} for all background shapes
    init_size : int
        Initial size of the stimulus (default: 300)
    target_size : int
        Target size for looming phase (default: 450)
    init_opacity : float
        Initial opacity of the stimulus (default: 0.3)
    target_opacity : float
        Target opacity for looming phase (default: 1.0)
    loom_duration : float
        Duration of the looming phase in seconds (default: 1.0)
    jiggle_duration : float
        Duration of the jiggling phase in seconds (default: 0.5)
    fade_duration : float
        Duration of the fade-back phase in seconds (default: 0.5)
    jiggle_amplitude : float
        Maximum rotation angle in degrees (default: 5)
    jiggle_frequency : float
        Frequency of oscillation in Hz (default: 2)
    loom_sound : psychopy.sound.Sound
        Sound to play during looming phase (default: None)
    selection_sound : psychopy.sound.Sound
        Sound to play during jiggling phase (default: None)
    """
    # Define explicit states
    LOOMING = "looming"
    JIGGLING = "jiggling"
    FADE_BACK = "fade-back"
    COMPLETE = "complete"

    def __init__(self, stim, win, pos, current_shape, background_stimuli,
                 init_size=300, target_size=450,
                 init_opacity=0.3, target_opacity=1.0,
                 loom_duration=1.0, jiggle_duration=0.5, fade_duration=0.5,
                 jiggle_amplitude=5, jiggle_frequency=2,
                 loom_sound=None, selection_sound=None):

        self.stim = stim
        self.win = win
        self.pos = pos
        self.current_shape = current_shape
        self.background_stimuli = background_stimuli  # dictionary of preloaded stimuli
        self.init_size = init_size
        self.target_size = target_size
        self.init_opacity = init_opacity
        self.target_opacity = target_opacity
        self.loom_duration = loom_duration
        self.jiggle_duration = jiggle_duration
        self.fade_duration = fade_duration
        self.jiggle_amplitude = jiggle_amplitude
        self.jiggle_frequency = jiggle_frequency

        # Store the original stimulus properties to restore later
        self.original_size = stim.size
        self.original_opacity = stim.opacity
        self.original_ori = stim.ori

        # Sound effects
        self.loom_sound = loom_sound
        self.selection_sound = selection_sound
        self.loom_sound_played = False
        self.selection_sound_played = False

        # Animation state
        from psychopy import core
        self.start_time = core.getTime()
        self.state = self.LOOMING
        self.current_angle = 0

        # Save original stimulus properties
        self.initial_stim_props = {
            'size': stim.size,
            'opacity': stim.opacity,
            'ori': stim.ori,
            'pos': stim.pos
        }

    def update(self, current_time=None):
        """
        Update the animation state based on elapsed time.

        Parameters:
        -----------
        current_time : float, optional
            Current time in seconds. If None, gets current time.

        Returns:
        --------
        bool
            True if the animation is complete, False otherwise
        """
        from psychopy import core
        import math

        if current_time is None:
            current_time = core.getTime()

        elapsed = current_time - self.start_time

        if self.state == self.LOOMING:
            if not self.loom_sound_played and self.loom_sound is not None:
                self.loom_sound.play()
                self.loom_sound_played = True

            if elapsed < self.loom_duration:
                t = elapsed / self.loom_duration
                self.stim.size = self.init_size + t * (self.target_size - self.init_size)
                self.stim.opacity = self.init_opacity + t * (self.target_opacity - self.init_opacity)
            else:
                self.state = self.JIGGLING
                self.start_time = current_time

        elif self.state == self.JIGGLING:
            if not self.selection_sound_played and self.selection_sound is not None:
                self.selection_sound.play()
                self.selection_sound_played = True

            if elapsed < self.jiggle_duration:
                t = elapsed
                self.current_angle = self.jiggle_amplitude * math.sin(2 * math.pi * self.jiggle_frequency * t)
                self.stim.ori = self.current_angle
            else:
                self.state = self.FADE_BACK
                self.start_time = current_time

        elif self.state == self.FADE_BACK:
            if elapsed < self.fade_duration:
                t = elapsed / self.fade_duration
                self.stim.size = self.target_size - t * (self.target_size - self.init_size)
                self.stim.opacity = self.target_opacity - t * (self.target_opacity - self.init_opacity)
                self.stim.ori = self.current_angle * (1 - t)
            else:
                self.state = self.COMPLETE
                self.reset_stimulus()

        self.draw()

        return self.state == self.COMPLETE

    def draw(self):
        """Draw the current animation frame to the window"""
        # Draw the background stimuli if available
        if self.background_stimuli:
            for shape, bg_stim in self.background_stimuli.items():
                if shape != self.current_shape:
                    bg_stim.draw()

        # Draw the animated stimulus
        self.stim.draw()
        self.win.flip()

    def reset_stimulus(self):
        """Reset the stimulus to its initial state"""
        self.stim.size = self.init_size
        self.stim.opacity = self.init_opacity
        self.stim.ori = 0
        self.stim.pos = self.pos

    def run_to_completion(self):
        """
        Run the full animation sequence from start to finish
        without requiring manual updates.
        """
        from psychopy import core

        # Run the looming phase
        looming_end = core.getTime() + self.loom_duration
        while core.getTime() < looming_end:
            self.update()

        # Run the jiggling phase
        jiggling_end = core.getTime() + self.jiggle_duration
        while core.getTime() < jiggling_end:
            self.update()

        # Run the fade-back phase
        fade_end = core.getTime() + self.fade_duration
        while core.getTime() < fade_end:
            self.update()

        # Ensure we're fully complete
        self.state = self.COMPLETE
        self.reset_stimulus()
        self.draw()
