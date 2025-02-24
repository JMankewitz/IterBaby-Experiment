import time
import csv
import os
from pygaze import settings, libscreen, eyetracker
from utils import *
import tobii_research as tr
from psychopy.hardware import keyboard


import constants

class InfantEyetrackingExperiment:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.expName = config.get('expName', 'IterBaby')
        self.path = os.getcwd()

        #provide some constants
        self.x_length = constants.DISPSIZE[0]
        self.y_length = constants.DISPSIZE[1]

        self.pos = {'bottomLeft': (-self.x_length/4, -self.y_length/4),
                    'bottomRight': (self.x_length/4,  -self.y_length/4),
                    'centerLeft': (-480, 0), 'centerRight': (480, 0),
                    'topLeft': (-self.x_length/4, self.y_length/4),
                    'topRight': (self.x_length/4, self.y_length/4),
                    'center': (0, 0),
                    'sampleStimLeft': (-600, -150),
                    'sampleStimRight': (600, -150),
                    'stimleft': (-self.x_length/4, -350),
                    'stimright': (self.x_length/4, -350)
                    }
        self.init_size = 300
        self.init_opacity = .3
        # Setup subject info
        self.subjInfo = {
            '1': {'name': 'subjCode',
                  'prompt': 'EXP_XXX',
                  'options': 'any',
                  'default': self.expName + '_001'},
            '2': {'name': 'sex',
                  'prompt': 'Subject sex m/f: ',
                  'options': ("m", "f"),
                  'default': '',
                  'type': str},
            '3': {'name': 'age',
                  'prompt': 'Subject Age: ',
                  'options': 'any',
                  'default': '',
                  'type': str},
            '4': {'name': 'order',
                  'prompt': '(test / 1 / 2 / 3 / 4)',
                  'options': ("test", "1", "2", "3", "4"),
                  'default': "test",
                  'type': str},
            '5': {'name': 'expInitials',
                  'prompt': 'Experimenter Initials: ',
                  'options': 'any',
                  'default': '',
                  'type': str},
            '6': {'name': 'mainMonitor',
                  'prompt': 'Screen Index (0,1,2,3): ',
                  'options': (0, 1, 2, 3),
                  'default': 2,
                  'type': int},
            '7': {'name': 'sideMonitor',
                  'prompt': 'Screen Index (0,1,2,3): ',
                  'options': (0, 1, 2, 3),
                  'default': 1,
                  'type': int},
            '8': {'name': 'eyetracker',
                  'prompt': '(yes / no)',
                  'options': ("yes", "no"),
                  'default': "yes",
                  'type': str},
            '9': {'name': 'activeMode',
                  'prompt': 'input / gaze',
                  'options': ("input", "gaze"),
                  'default': "input",
                  'type': str},
            '10': {'name': 'responseDevice',
                   'prompt': 'keyboard / mouse',
                   'options': ("keyboard", "mouse"),
                   'default': 'keyboard'}
        }
        
        # Pre-experiment setup: subject info entry and data file initialization.
        self.initialize_subj_info()
        self.setup_display()
        self.setup_exp_paths()
        self.setup_input_devices()
        self.setup_stimuli_assignment()
        self.load_stimuli()
        self.display_start_screen()


        self.logger.info("Experiment initialized with configuration.")

    def initialize_subj_info(self):
        """
        Runs the pre-experiment steps:
          - Presents the GUI to collect subject information.
          - Sets the pygaze LOGFILE path for Tobii logging.
          - Checks to ensure that data files do not already exist.
        """

        fileOpened = False
        # Loop until a unique subject code is provided and files do not exist.

        while not fileOpened:
            # enterSubjInfo should return (optionsReceived, subjVariables)
            optionsReceived, self.subjVariables = enterSubjInfo(self.expName, self.subjInfo)
            if not optionsReceived:
                    popupError(self.subjVariables)
            
            # Set up the pygaze logfile path (tobii_research will use this).
            # Assumes that config has a LOGFILEPATH key, e.g., "data/logs/"
            settings.LOGFILE = os.path.join(constants.LOGFILEPATH, self.subjVariables['subjCode'])
            self.logger.info(f"Settings LOGFILE set to: {settings.LOGFILE}")
            
            # Determine the expected training output file path.
            training_filepath = os.path.join("data", "training", f"tracking_data_{self.subjVariables['subjCode']}.txt")
            
            if not os.path.isfile(training_filepath):

                # If using an eyetracker, also check for the Tobii output file.
                if self.subjVariables.get('eyetracker') == "yes":
                    tobii_filepath = settings.LOGFILE + '_TOBII_output.tsv'
                    if not os.path.isfile(tobii_filepath):
                        fileOpened = True
                        # Open additional files for active training and active test as needed.
                        self.trainingOutputFile = open(training_filepath, 'w')
                        self.results_filepath = os.path.join("data", "activeTest", f"tracking_data_{self.subjVariables['subjCode']}.txt")
                        #self.results_file = open(self.results_filepath, 'w')
                        self.logger.info("Data files opened for eyetracker mode.")
                    else:
                        fileOpened = False
                        popupError('That subject code for the eyetracking data already exists! The prompt will now close!')
                        self.logger.error("Duplicate eyetracking data file found; exiting.")
                        exit(1)
                else:
                    # If no eyetracker, only the training file is needed.
                    fileOpened = True
                    self.trainingOutputFile = open(training_filepath, 'w')
                    self.logger.info("Data file opened for non-eyetracker mode.")
            else:
                fileOpened = False
                popupError('That subject code already exists!')
                self.logger.error("Duplicate subject code detected; prompting for new input.")

    def setup_exp_paths(self):
        """
        loads stimulis directories
        """
        # Define stimulus directories.
        self.imagePath = os.path.join(self.path, 'stimuli', 'images')
        self.soundPath = os.path.join(self.path, 'stimuli', 'sounds')
        self.activeSoundPath = os.path.join(self.path, 'stimuli', 'sounds')
        self.moviePath = os.path.join(self.path, 'stimuli', 'movies')
        self.AGPath = os.path.join(self.path, 'stimuli', 'movies', 'AGStims')
        self.imageExt = ['jpg', 'png', 'gif', 'jpeg']
        self.logger.info("Stimuli paths set.")

    def setup_display(self):
        """
        Sets up the display using PsychoPy (via libscreen and pygaze),
        """
        from pygaze.libscreen import Display, Screen
        import pygaze
        import tobii_research as tr
        from pygaze import eyetracker, libinput
        from psychopy.hardware import keyboard  # Assuming a keyboard module is available
        
        # Initialize the main display using PsychoPy.
        self.disp = Display(disptype='psychopy', fgc="black", bgc="black", screennr=self.subjVariables['mainMonitor'])
        self.blackScreen = Screen(fgc="black", bgc="black")

        # Typically, pygaze.expdisplay sets up the experimental window.
        self.win = pygaze.expdisplay  
        self.logger.info(f"Winsize: {self.win.size}, win units: {self.win.units}")
        self.logger.info("Display and screens initialized.")

    def setup_input_devices(self):
        # Eyetracker setup: if enabled, try to locate and connect to the device.
        if self.subjVariables.get('eyetracker') == "yes":
            attempts = 0
            self.eyetrackers = tr.find_all_eyetrackers()
            while len(self.eyetrackers) == 0 and attempts < 50:
                self.logger.info("Trying to find eyetracker...")
                attempts += 1
                self.eyetrackers = tr.find_all_eyetrackers()
            self.tracker = eyetracker.EyeTracker(self.disp)
            self.logger.info(f"Eyetracker connected? {self.tracker.connected()}")
        
        # Input device setup based on subject selection.
        if self.subjVariables.get('responseDevice', 'keyboard') == 'keyboard':
            self.inputDevice = "keyboard"
            self.validResponses = {'1': 'space', '2': 'left', '3': 'right', '4': 'z', '5': 'enter'}
            self.input = keyboard.Keyboard()
            self.logger.info("Keyboard input device initialized.")
        else:
            self.inputDevice = "mouse"
            from pygaze.libinput import Mouse
            self.input = Mouse(mousebuttonlist=[1], timeout=None)
            self.logger.info("Mouse input device initialized.")

    def load_stimuli(self):
        loadScreen = libscreen.Screen()
        loadScreen.draw_text(text = "Loading Files...", color = "white", fontsize = 48)
        self.disp.fill(loadScreen)
        self.disp.show()
        
        self.movieMatrix = loadFilesMovie(self.moviePath, ['mp4', 'mov'], 'movie', self.win)
        self.AGmovieMatrix = loadFilesMovie(self.AGPath, ['mp4'], 'movie', self.win)
        #self.soundMatrix = loadFiles(self.soundPath, ['.mp3', '.wav'], 'sound')
        #self.AGsoundMatrix = loadFiles(self.AGPath, ['.mp3', '.wav'], 'sound')
        self.image_files = {
            "circle": os.path.join(self.imagePath, "circle.png"),
            "cross": os.path.join(self.imagePath, "cross.png"),
            "star": os.path.join(self.imagePath, "star.png"),
            "t": os.path.join(self.imagePath, "t.png"),
            "fixator": os.path.join(self.imagePath, "spinning-wheel.png")
            }
        self.fixator_stim = visual.ImageStim(
                self.win,
                image=self.image_files["fixator"],
                pos=self.pos["center"],
                size=200,          # Use your desired initial size.
                opacity=1,       # Use your desired initial opacity.
                units='pix',
                ori=0
            )
        self.preloaded_static_stimuli = {}
        for shape, pos in self.shape_positions.items():
            self.preloaded_static_stimuli[shape] = visual.ImageStim(
                self.win,
                image=self.image_files[shape],
                pos=pos,
                size=300,          # Use your desired initial size.
                opacity=0.3,       # Use your desired initial opacity.
                units='pix',
                ori=0
            )

        self.logger.info("Loaded Files")

    def setup_stimuli_assignment(self):
        self.shape_order = ["circle", "cross", "star", "t"]
        
        self.shape_positions = {
            "circle": self.pos["bottomLeft"],
            "cross": self.pos["bottomRight"],
            "star": self.pos["topLeft"],
            "t": self.pos["topRight"]
        }

        self.shapeAOIs = {}
        aoi_width = 450
        aoi_height = 450

        for shape, pos in self.shape_positions.items():
            pygaze_pos = psychopy_to_pygaze(pos)
            self.shapeAOIs[shape] = aoi.AOI('rectangle', pos=pygaze_pos, size=(aoi_width, aoi_height))

        self.logger.info(f"Shape positions assigned: {self.shape_positions}")

    def display_start_screen(self):
        self.initialScreen = libscreen.Screen()
        self.initialImageName = self.imagePath + "/bunnies.gif"
        initialImage = visual.ImageStim(self.win, self.initialImageName, mask=None, interpolate=True)
        initialImage.setPos(self.pos['center'])
        buildScreenPsychoPy(self.initialScreen, [initialImage])
        setAndPresentScreen(self.disp, self.initialScreen)
        print("Screen presented, waiting for keypress...")

        key = event.waitKeys(keyList=['space', 'enter', 'left', 'right', 'down'])
        print(f"Key pressed: {key}")
        self.disp.show()

    def run_training_trial(self):
    # --- Phase 1: Show preloaded static shapes with a spinning wheel ---
        spin_duration = 1 #second
        spin_start = core.getTime()

        while core.getTime() - spin_start < spin_duration:
            draw_static_shapes(self.preloaded_static_stimuli)
            elapsed = core.getTime() - spin_start
            self.fixator_stim.ori = (elapsed * 360) % 360
            self.fixator_stim.draw()
            self.win.flip()
        
        draw_static_shapes(self.preloaded_static_stimuli)
        self.win.flip()

        # --- Phase 2: Animate each shape ---
        # Sequentially animate each shape in order.
        for shape in self.shape_order:
            self.logger.info(f"Animating shape: {shape}")
            stim = self.preloaded_static_stimuli[shape]
            pos = self.shape_positions[shape]
            # Animate the shape: it looms and rotates.
            loom_shape_with_background(stim, self.win, pos, current_shape=shape,
                                    background_positions=self.shape_positions,
                                    image_files=self.image_files,
                                    init_size=300, target_size=450,
                                    init_opacity=0.3, target_opacity=1.0,
                                    loom_duration=1.0, jiggle_duration=0.5, fade_duration=0.25,
                                    jiggle_amplitude=5, jiggle_frequency=2)
            # Redraw the static display between animations.
            draw_static_shapes(self.preloaded_static_stimuli)
            self.win.flip()

    def run_gt_trial(self):
        """
        Runs the gaze-triggered phase. Displays the static shapes, then continuously
        checks for fixations on any shape. When a fixation of at least 500ms is detected
        within a shape’s AOI, that shape is triggered (looming animation), and its selection
        is recorded. If no fixation is detected within 5 seconds, a re-cue is displayed.
        The phase ends after 4 selections or 10 seconds, whichever comes first.
        """
        self.logger.info("Starting gaze-triggered phase.")
        # --- Phase 1: Show preloaded static shapes with a spinning wheel ---
        spin_duration = 1 #second
        spin_start = core.getTime()

        while core.getTime() - spin_start < spin_duration:
            draw_static_shapes(self.preloaded_static_stimuli)
            elapsed = core.getTime() - spin_start
            self.fixator_stim.ori = (elapsed * 360) % 360
            self.fixator_stim.draw()
            self.win.flip()
        # Draw the static display.
        draw_static_shapes(self.preloaded_static_stimuli)
        self.win.flip()
        
        # --- Phase 2: Gaze-triggered ---
        # If using eyetracker, start recording.
        if self.subjVariables.get('eyetracker') == "yes":
            self.tracker.start_recording()
            # Log starting information to tobii if needed.
        
        trial_start = core.getTime()
        max_trial_time = 10  # seconds
        required_fixation = 0.33  # seconds
        selections = []
        selection_count = 0
        
        # We'll keep a history of gaze samples per shape AOI.
        gaze_histories = {shape: [] for shape in self.shape_order}
        
        while (core.getTime() - trial_start) < max_trial_time and selection_count < 4:
            # Assume we can get a gaze sample as (x, y, timestamp)
            # This might be a synchronous call or polled from a buffer.
            if self.subjVariables.get('eyetracker') == "yes":
                gaze_sample = self.tracker.sample()  
            else:
                gaze_sample = None
            
            self.logger.info(gaze_sample)

            current_time = core.getTime()
            # If no valid gaze sample, optionally continue.
            if gaze_sample is None:
                # If no gaze for over 5 seconds, display re-cue.
                if (current_time - trial_start) > 5:
                    self.logger.info("No gaze detected for 5 seconds; displaying re-cue.")
                    #self.display_spinning_circle()
                continue
            
            # Otherwise, assume gaze_sample is a tuple: (x, y, timestamp)
            #gx, gy, ts = gaze_sample
            # Check each shape’s AOI.
            for shape in self.shape_order:
                if self.shapeAOIs[shape].contains(gaze_sample):
                    gaze_histories[shape].append((gaze_sample, current_time))
                    if self._fixation_duration(gaze_histories[shape]) >= required_fixation:
                        if shape not in selections:
                            self.logger.info(f"Shape {shape} selected via fixation.")
                            loom_shape_with_background(
                                self.preloaded_static_stimuli[shape], self.win, self.shape_positions[shape],
                                current_shape=shape,
                                background_positions=self.shape_positions,
                                image_files=self.image_files,
                                init_size=self.init_size, target_size=450,
                                init_opacity=self.init_opacity, target_opacity=1.0,
                                loom_duration=1.0, jiggle_duration=0.5, fade_duration=0.25,
                                jiggle_amplitude=5, jiggle_frequency=2)
                            selections.append(shape)
                            selection_count += 1
                            gaze_histories = {s: [] for s in self.shape_order}
                else:
                    gaze_histories[shape] = []  # Clear if gaze leaves the AOI.
            # Refresh the static display (optional, if needed).
            draw_static_shapes(self.preloaded_static_stimuli)
            self.win.flip()

    def _fixation_duration(self, gaze_history):
        if not gaze_history:
            return 0
        start_time = gaze_history[0][1]
        end_time = gaze_history[-1][1]
        return end_time - start_time

    def run_training_phase(self):
        self.logger.info("Starting training phase.")
        n_trials = 5  # You can adjust this or retrieve from self.config, e.g., self.config.get('n_training_trials', 5)
        for trial in range(1, n_trials + 1):
            self.logger.info(f"Starting training trial {trial} of {n_trials}.")
            self.run_training_trial()
            core.wait(0.5)  # Optional: inter-trial interval between training trials.
        self.logger.info("Training phase completed.")

    def run_gaze_triggered_phase(self):
        self.logger.info("Starting gaze-triggered phase.")
        n_trials = 3  # You can adjust this or retrieve from self.config, e.g., self.config.get('n_training_trials', 5)
        for trial in range(1, n_trials + 1):
            self.logger.info(f"Starting test trial {trial} of {n_trials}.")
            self.run_gt_trial()
            core.wait(0.5)
        self.logger.info("Gaze-triggered phase completed.")
