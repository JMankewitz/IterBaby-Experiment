import logging
import os
import pyo as pyo
from psychopy import prefs
prefs.hardware['audioLib'] = ['pyo']

from psychopy import sound, core, visual
import math
import random

print('Using %s(with %s) for sounds' %(sound.audioLib, sound.audioDriver))

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
			movie = visual.MovieStim(win, fullPath, noAudio = True)
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

def loom_shape_with_background(stim, win, pos, current_shape,
                               background_positions, image_files,
                               init_size=100, target_size=150, 
                               init_opacity=0.3, target_opacity=1.0, 
                               loom_duration=1.0, jiggle_duration=0.5, fade_duration=0.5,
                               jiggle_amplitude=5, jiggle_frequency=2):
    """
    Animate a looming shape while keeping the other shapes static.
    
    Parameters:
      stim: The ImageStim object for the looming shape.
      win: PsychoPy window.
      pos: Position for the looming shape (in pixels).
      current_shape: Name of the shape that is looming.
      background_positions: Dict mapping shape names to positions (in pixels) for all shapes.
      image_files: Dict mapping shape names to image file paths.
      init_size: Baseline size for all shapes.
      target_size: Peak size for the looming shape.
      init_opacity: Baseline opacity for all shapes.
      target_opacity: Peak opacity for the looming shape.
      loom_duration: Duration for the growing phase.
      jiggle_duration: Duration for the rotation (jiggle) phase.
      fade_duration: Duration for the fade-back phase.
      jiggle_amplitude: Maximum rotation angle (degrees) during jiggle.
      jiggle_frequency: Frequency (Hz) of oscillation during jiggle.
    """
    clock = core.Clock()
    # LOOMING PHASE
    while clock.getTime() < loom_duration:
        t = clock.getTime() / loom_duration
        # Update looming parameters.
        current_size = init_size + t * (target_size - init_size)
        current_opacity = init_opacity + t * (target_opacity - init_opacity)
        stim.size = current_size
        stim.opacity = current_opacity
        # Draw background shapes.
        for shape, bg_pos in background_positions.items():
            if shape != current_shape:
                bg_stim = visual.ImageStim(win, image=image_files[shape], pos=bg_pos,
                                           size=init_size, opacity=init_opacity, units='pix', ori=0)
                bg_stim.draw()
        # Draw the looming shape on top.
        stim.draw()
        win.flip()
    
    # JIGGLE PHASE: Smooth rotation oscillation.
    clock.reset()
    while clock.getTime() < jiggle_duration:
        t = clock.getTime()
        current_angle = jiggle_amplitude * math.sin(2 * math.pi * jiggle_frequency * t)
        stim.ori = current_angle
        # Draw background shapes.
        for shape, bg_pos in background_positions.items():
            if shape != current_shape:
                bg_stim = visual.ImageStim(win, image=image_files[shape], pos=bg_pos,
                                           size=init_size, opacity=init_opacity, units='pix', ori=0)
                bg_stim.draw()
        stim.draw()
        win.flip()
    
    # FADE-BACK PHASE: Return to baseline.
    clock.reset()
    while clock.getTime() < fade_duration:
        t = clock.getTime() / fade_duration
        current_size = target_size - t * (target_size - init_size)
        current_opacity = target_opacity - t * (target_opacity - init_opacity)
        stim.size = current_size
        stim.opacity = current_opacity
        # Gradually return rotation to zero.
        stim.ori = current_angle * (1 - t)
        for shape, bg_pos in background_positions.items():
            if shape != current_shape:
                bg_stim = visual.ImageStim(win, image=image_files[shape], pos=bg_pos,
                                           size=init_size, opacity=init_opacity, units='pix', ori=0)
                bg_stim.draw()
        stim.draw()
        win.flip()
    
    # Reset final state for the looming shape.
    stim.size = init_size
    stim.opacity = init_opacity
    stim.ori = 0
    stim.pos = pos
    # Draw background shapes one last time.
    for shape, bg_pos in background_positions.items():
        if shape != current_shape:
            bg_stim = visual.ImageStim(win, image=image_files[shape], pos=bg_pos,
                                       size=init_size, opacity=init_opacity, units='pix', ori=0)
            bg_stim.draw()
    stim.draw()
    win.flip()
	
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


def draw_static_shapes(win, shape_positions, image_files, init_size=0.5, init_opacity=0.3):
    """
    Draws all shapes in their baseline state.
    
    Parameters:
      win: PsychoPy window.
      shape_positions: dict mapping shape names to positions.
      image_files: dict mapping shape names to their image file paths.
      init_size: The initial size scaling.
      init_opacity: The initial opacity.
      
    Returns:
      dict: Mapping of shape name to its ImageStim.
    """
    stimuli = {}
    for shape, pos in shape_positions.items():
        stim = visual.ImageStim(win, image=image_files[shape], pos=pos, 
                                  size=init_size, opacity=init_opacity, units='pix', ori=0)
        stim.draw()
        stimuli[shape] = stim
    win.flip()
    return stimuli


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

def psychopy_to_pygaze(psychopy_coord, screen_width=1920, screen_height=1080, stim_width=300, stim_height=300):
    """
    Converts a position from PsychoPy (centered) to pygaze (origin at bottom left)
    and adjusts for stimulus size (assuming the PsychoPy coordinate is the center
    of the stimulus and pygaze AOI is defined by the bottom-left corner).
    
    Parameters:
      psychopy_coord: Tuple (x, y) in PsychoPy coordinates.
      screen_width: Width of the pygaze screen (default 1920).
      screen_height: Height of the pygaze screen (default 1080).
      stim_width: Width of the stimulus in pixels (default 300).
      stim_height: Height of the stimulus in pixels (default 300).
    
    Returns:
      Tuple (x', y') representing the bottom-left coordinate for pygaze.
    """
    x, y = psychopy_coord
    pyg_x = x + (screen_width / 2) - (stim_width / 2)
    pyg_y = y + (screen_height / 2) - (stim_height / 2)
    return (pyg_x, pyg_y)
