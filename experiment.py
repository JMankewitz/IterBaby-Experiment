import time
import csv
import os
import pygaze
from pygaze import settings, libscreen, eyetracker
from utils import *
from data_logger import *
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
        self.current_trial = 0
        self.last_selection_time = 0
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

        self.ag_video_list = ['balloons_5', 'bouncyballs_5', 'galaxies_5', 'kangaroo_5']
        self.current_ag_index = 0  # Keep track of which AG video to play next

        # Pre-experiment setup: subject info entry and data file initialization.
        self.initialize_subj_info()

        self.data_logger = DataLogger(self)

        self.setup_display()
        self.setup_exp_paths()
        self.setup_input_devices()
        self.setup_stimuli_assignment()
        self.load_stimuli()
        self.display_start_screen()

        self.logger.info("Experiment initialized with configuration.")

    def get_experiment_data(self, key, default=None):
        """Access method for the data logger to get experiment variables"""
        if key == 'subjVariables':
            return self.subjVariables
        elif key == 'tracker':
            return self.tracker if hasattr(self, 'tracker') else None
        # Add other needed variables
        return default

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

            # Check if files already exist to avoid overwriting data
            training_filepath = os.path.join("data", "training", f"tracking_data_{self.subjVariables['subjCode']}.txt")

            if not os.path.isfile(training_filepath):
                # If using an eyetracker, also check for the Tobii output file
                if self.subjVariables.get('eyetracker') == "yes":
                    tobii_filepath = settings.LOGFILE + '_TOBII_output.tsv'
                    if not os.path.isfile(tobii_filepath):
                        fileOpened = True
                        self.logger.info("Subject code verified. No duplicate files found.")
                    else:
                        fileOpened = False
                        popupError(
                            'That subject code for the eyetracking data already exists! The prompt will now close!')
                        self.logger.error("Duplicate eyetracking data file found; exiting.")
                        exit(1)
                else:
                    # If no eyetracker, only check the training file
                    fileOpened = True
                    self.logger.info("Subject code verified. No duplicate files found.")
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
            max_attempts = 20
            self.eyetrackers = tr.find_all_eyetrackers()
            while len(self.eyetrackers) == 0 and attempts < max_attempts:
                self.logger.info(f"Trying to find eyetracker (attempt {attempts + 1}/{max_attempts})...")
                attempts += 1
                self.eyetrackers = tr.find_all_eyetrackers()
                time.sleep(0.1)
            if len(self.eyetrackers) == 0:
                self.logger.error("Failed to find eyetracker after multiple attempts")
                popupError("Could not connect to eyetracker. Please check connections and restart.")
                core.quit()

            self.tracker = pygaze.eyetracker.EyeTracker(self.disp)
            self.logger.info(self.tracker)
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

    def setup_data_recording(self):
        """
        Set up data recording files and headers for both eyetracker logging and CSV output.
        This should be called during experiment initialization.
        """
        # Set up CSV file for recording selections
        self.selection_csv_path = os.path.join("data", "selections",
                                               f"selection_data_{self.subjVariables['subjCode']}.csv")

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.selection_csv_path), exist_ok=True)

        # Create CSV with headers
        with open(self.selection_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'trial', 'timestamp', 'selection_number', 'shape', 'position',
                'fixation_duration', 'rt_from_trial_start', 'rt_from_previous_selection'
            ])

        self.logger.info(f"Selection data will be recorded to {self.selection_csv_path}")

        # Initialize tracking variables for recording

    def load_stimuli(self):
        loadScreen = libscreen.Screen()
        loadScreen.draw_text(text = "Loading Files...", color = "white", fontsize = 48)
        self.disp.fill(loadScreen)
        self.disp.show()
        
        self.movieMatrix = loadFilesMovie(self.moviePath, ['mp4', 'mov'], 'movie', self.win)
        self.AGmovieMatrix = loadFilesMovie(self.AGPath, ['mp4'], 'movie', self.win)
        selectionSoundMatrix = loadFiles(os.path.join(self.soundPath, 'selection'), ['.mp3', '.wav'], 'sound')
        loomSoundMatrix = loadFiles(os.path.join(self.soundPath, 'loom'), ['.mp3', '.wav'], 'sound')
        self.AGsoundMatrix = loadFiles(self.AGPath, ['.mp3', '.wav'], 'sound')
        self.stars = loadFiles(self.AGPath, ['.jpg'], 'image', self.win)

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

        self.loom_sounds = {}
        self.selection_sounds = {}

        loom_sound_keys = list(loomSoundMatrix.keys())
        for i, shape in enumerate(self.shape_order):
            # Cycle through loom sounds if there are fewer sounds than shapes.
            key = loom_sound_keys[i % len(loom_sound_keys)]
            self.loom_sounds[shape] = loomSoundMatrix[key]

        selection_sound_keys = list(selectionSoundMatrix.keys())
        for i, shape in enumerate(self.shape_order):
            # Cycle through loom sounds if there are fewer sounds than shapes.
            key = selection_sound_keys[i % len(selection_sound_keys)]
            self.selection_sounds[shape] = selectionSoundMatrix[key]

        self.logger.info("Loaded Files")

    def get_next_ag_video(self):
        """
        Get the next attention-getter video in the rotation.

        Returns:
        --------
        str
            Name of the next AG video to play
        """
        if not self.ag_video_list:
            return None

        video = self.ag_video_list[self.current_ag_index]
        self.current_ag_index = (self.current_ag_index + 1) % len(self.ag_video_list)
        return video

    def setup_stimuli_assignment(self):
        self.shape_order = ["circle", "cross", "star", "t"]
        
        self.shape_positions = {
            "circle": self.pos["bottomLeft"],
            "cross": self.pos["bottomRight"],
            "star": self.pos["topLeft"],
            "t": self.pos["topRight"]
        }

        self.shapeAOIs = {}
        aoi_width = 500
        aoi_height = 500

        for shape, pos in self.shape_positions.items():
            pygaze_pos = psychopy_to_pygaze(pos, x_offset = aoi_width/2, y_offset = aoi_height/2)
            print(pygaze_pos)
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
        # --- Phase 0: Setup eyetracking ---
        # Increment trial counter
        self.current_trial += 1
        self.trial_start_time = core.getTime()
        # Record trial start time
        self.data_logger.trial_start_time = self.trial_start_time
        self.data_logger.current_trial = self.current_trial

        # Start eyetracking recording for this trial
        if self.subjVariables.get('eyetracker') == "yes":
            self.tracker.start_recording()

        # Log trial start
        self.data_logger.log_trial_event(
            trial_num=self.current_trial,
            phase="training",
            event_type="trial_start",
            additional_info=f"shape_order={'-'.join(self.shape_order)}"
        )

        # --- Phase 1: Show preloaded static shapes with a spinning wheel ---
        spin_duration = 1 #second
        spin_start = core.getTime()

        while core.getTime() - spin_start < spin_duration:
            draw_static_shapes(self.preloaded_static_stimuli)
            elapsed = core.getTime() - spin_start
            self.fixator_stim.ori = (elapsed * 360) % 360
            self.fixator_stim.draw()
            self.win.flip()

        self.data_logger.log_trial_event(
            trial_num=self.current_trial,
            phase="training",
            event_type="fixator_end"
        )

        draw_static_shapes(self.preloaded_static_stimuli)
        self.win.flip()

        # --- Phase 2: Animate each shape ---
        # Sequentially animate each shape in order.
        for shape_index, shape in enumerate(self.shape_order):
            libtime.pause(random.choice([0, 250, 500, 750, 1000]))
            self.logger.info(f"Animating shape: {shape}")
            animation_start_time = self.data_logger.log_trial_event(
                trial_num=self.current_trial,
                phase="training",
                event_type="animation_start",
                shape=shape,
                position=str(self.shape_positions[shape]),
                additional_info=f"sequence_position={shape_index + 1}/{len(self.shape_order)}"
            )

            stim = self.preloaded_static_stimuli[shape]

            animation = LoomAnimation(
                stim=stim,
                win=self.win,
                pos=self.shape_positions[shape],
                current_shape=shape,
                background_stimuli=self.preloaded_static_stimuli,
                init_size=self.init_size,
                target_size=450,
                init_opacity=self.init_opacity,
                target_opacity=1.0,
                loom_duration=1.0,
                jiggle_duration=0.5,
                fade_duration=0.25,
                jiggle_amplitude=5,
                jiggle_frequency=2,
                loom_sound=self.loom_sounds[shape],
                selection_sound=self.selection_sounds[shape]
            )
            animation.run_to_completion()

            current_time = core.getTime()

            self.data_logger.log_trial_event(
                trial_num=self.current_trial,
                phase="training",
                event_type="animation_end",
                shape=shape,
                position=str(self.shape_positions[shape]),
                additional_info=f"duration={(current_time - animation_start_time) * 1000:.0f}ms"
            )

            draw_static_shapes(self.preloaded_static_stimuli)
            self.win.flip()

        self.data_logger.log_trial_event(
            trial_num=self.current_trial,
            phase="training",
            event_type="trial_end",
            additional_info=f"shapes_shown={'-'.join(self.shape_order)}"
        )

        if self.subjVariables.get('eyetracker') == "yes":
            self.tracker.stop_recording()

    def run_gt_trial(self):

        # Increment trial counter
        self.current_trial += 1
        self.data_logger.current_trial = self.current_trial
        # initialize trial in data_logger
        self.data_logger.start_trial(self.current_trial)

        # Reset last selection time for new trial
        self.last_selection_time = 0

        self.logger.info(f"Starting gaze-triggered trial {self.current_trial}")

        # --- Phase 1: Show static shapes with a spinning fixator ---
        spin_duration = 1  # second
        spin_start = core.getTime()
        while core.getTime() - spin_start < spin_duration:
            draw_static_shapes(self.preloaded_static_stimuli)
            elapsed = core.getTime() - spin_start
            self.fixator_stim.ori = (elapsed * 360) % 360
            self.fixator_stim.draw()
            self.win.flip()

        draw_static_shapes(self.preloaded_static_stimuli)
        self.win.flip()

        if self.subjVariables.get('eyetracker') == "yes":
            self.tracker.start_recording()

        self.data_logger.log_trial_event(
            trial_num=self.current_trial,
            phase="gaze_triggered",
            event_type="trial_start",
            additional_info=f"shape_order={'-'.join(self.shape_order)}"
        )

        self.trial_start_time = core.getTime()
        # Record trial start time
        self.data_logger.trial_start_time = self.trial_start_time

        last_selection_time = self.trial_start_time

        max_trial_time = 20  # seconds
        required_fixation = 0.25  # seconds
        selection_count = 0
        selection_timeout = 7 # seconds - max time between selections
        initial_selection_timeout = 5 #seconds - max time to wait for first selection

        # Setup dictionaries.
        gaze_histories = {shape: [] for shape in self.shape_order}
        triggered_flags = {shape: False for shape in self.shape_order}
        last_triggered = {shape: 0 for shape in self.shape_order}
        cooldown = 5.0  # seconds cooldown

        active_animation = None    # Currently running animation.
        queued_animation = None    # Candidate for the next animation.

        # Main loop: run until max_trial_time OR we've reached 4 selections and no animation is active.
        while (core.getTime() - self.trial_start_time) < max_trial_time:

            # If we've already reached 4 selections and no animation is playing, end the trial.
            if selection_count >= 4 and active_animation is None:
                break

            current_time = core.getTime()

            if selection_count == 0 and (current_time - self.trial_start_time) > initial_selection_timeout:
                self.logger.info(
                    f"No initial selection made within {initial_selection_timeout} seconds; terminating trial early.")
                break

            if selection_count > 0 and selection_count < 4 and active_animation is None and (
                    current_time - last_selection_time) > selection_timeout:
                self.logger.info(
                    f"No selection for {selection_timeout} seconds after previous selection; terminating trial early.")
                break

            if self.subjVariables.get('eyetracker') == "yes":
                gaze_sample = self.tracker.sample()
            else:
                gaze_sample = None

            # Update active animation.
            if active_animation is not None:
                if active_animation.update(current_time):
                    last_triggered[active_animation.current_shape] = current_time
                    active_animation = None
                    queued_animation = None  # Clear queued candidate when one finishes.

            # In the run_gt_trial method, when promoting a queued animation:
            if active_animation is None and queued_animation is not None:
                # Only promote if we haven't reached 4 selections
                if selection_count < 4:
                    # At this point, the queued animation is being activated,
                    # so we need to log it as an executed (non-queued) selection
                    selection_count += 1
                    last_selection_time = current_time
                    for other_shape in self.shape_order:
                        if other_shape != active_animation.current_shape:
                            last_triggered[other_shape] = 0

                    # Log that the queued selection is now being executed
                    self.data_logger.log_selection(
                        trial_num=self.current_trial,
                        selection_num=selection_count,  # This is the current selection number
                        shape=queued_animation.current_shape,
                        position=self.shape_positions[queued_animation.current_shape],
                        fixation_duration=0,  # We don't know the original fixation duration here
                        queued=False,  # It's no longer queued
                        was_executed=True  # It's being executed now
                    )

                    active_animation = queued_animation
                    queued_animation = None

            self.logger.info(gaze_sample)
            # Process gaze sample for each shape.
            for shape in self.shape_order:
                if self.shapeAOIs[shape].contains(gaze_sample):
                    gaze_histories[shape].append((gaze_sample, current_time))
                    fixation_duration = self._fixation_duration(gaze_histories[shape])

                    if fixation_duration >= required_fixation:

                        # Immediate trigger only if no animation is active and we haven't reached 4.
                        if active_animation is None and selection_count < 4:
                            # Enforce cooldown.
                            if current_time - last_triggered[shape] < cooldown:
                                continue

                            selection_count += 1
                            last_selection_time = current_time
                            self.logger.info(f"Shape {shape} triggered via fixation (immediate).")

                            # Log the selection event
                            self.data_logger.log_selection(
                                trial_num=self.current_trial,
                                selection_num=selection_count,
                                shape=shape,
                                position=self.shape_positions[shape],
                                fixation_duration=fixation_duration,
                                queued=False,
                                was_executed=True,
                                selection_time=current_time
                            )

                            active_animation = LoomAnimation(
                                stim=self.preloaded_static_stimuli[shape],
                                win=self.win,
                                pos=self.shape_positions[shape],
                                current_shape=shape,
                                background_stimuli=self.preloaded_static_stimuli,
                                init_size=self.init_size,
                                target_size=450,
                                init_opacity=self.init_opacity,
                                target_opacity=1.0,
                                loom_duration=1.0,
                                jiggle_duration=0.5,
                                fade_duration=0.25,
                                jiggle_amplitude=5,
                                jiggle_frequency=2,
                                loom_sound=self.loom_sounds[shape],
                                selection_sound=self.selection_sounds[shape]
                            )

                            triggered_flags[shape] = True
                            gaze_histories[shape] = []
                            last_triggered[shape] = current_time
                            for other_shape in self.shape_order:
                                if other_shape != shape:
                                    last_triggered[other_shape] = 0  # Reset cooldown for others

                        # If an animation is active, allow queuing only if selection_count is less than 3.
                        elif active_animation is not None and selection_count < 3:
                            if queued_animation is None or queued_animation.current_shape != shape:
                                self.logger.info(f"Shape {shape} queued as next candidate (N+1)")

                                # Log the queued selection - note was_executed=False because it's not shown yet
                                self.data_logger.log_selection(
                                    trial_num=self.current_trial,
                                    selection_num=selection_count + 1,  # This will be the next selection number
                                    shape=shape,
                                    position=self.shape_positions[shape],
                                    fixation_duration=fixation_duration,
                                    queued=True,
                                    was_executed=False,  # Not executed yet, just queued
                                    selection_time=current_time
                                )

                                queued_animation = LoomAnimation(
                                    stim=self.preloaded_static_stimuli[shape],
                                    win=self.win,
                                    pos=self.shape_positions[shape],
                                    current_shape=shape,
                                    background_stimuli=self.preloaded_static_stimuli,
                                    init_size=self.init_size,
                                    target_size=450,
                                    init_opacity=self.init_opacity,
                                    target_opacity=1.0,
                                    loom_duration=1.0,
                                    jiggle_duration=0.5,
                                    fade_duration=0.25,
                                    jiggle_amplitude=5,
                                    jiggle_frequency=2,
                                    loom_sound=self.loom_sounds[shape],
                                    selection_sound=self.selection_sounds[shape]
                                )
                                triggered_flags[shape] = True
                                gaze_histories[shape] = []
                                #last_triggered[shape] = current_time
                else:
                    # Clear history if gaze is not on the AOI.
                    gaze_histories[shape] = []

            # If nothing is active, refresh the static display.
            if active_animation is None and queued_animation is None:
                draw_static_shapes(self.preloaded_static_stimuli)
                self.win.flip()

            # End of trial processes
            # 1. Mark any queued selection that wasn't executed
            if queued_animation is not None:
                self.data_logger.log_selection(
                    trial_num=self.current_trial,
                    selection_num=selection_count + 1,
                    shape=queued_animation.current_shape,
                    position=self.shape_positions[queued_animation.current_shape],
                    fixation_duration=0,  # Unknown at this point
                    queued=True,
                    was_executed=False
                )

            # 2. Record trial summary
        self.data_logger.end_trial(self.current_trial)

         # 3. Stop eyetracker recording

        if self.subjVariables.get('eyetracker') == "yes":
            self.tracker.stop_recording()

        return selection_count

    def run_seeded_gt_trial(self):

        # Increment trial counter
        self.current_trial += 1
        self.data_logger.current_trial = self.current_trial
        # initialize trial in data_logger
        self.data_logger.start_trial(self.current_trial)

        # Reset last selection time for new trial
        self.last_selection_time = 0

        self.logger.info(f"Starting gaze-triggered trial {self.current_trial}")

        # --- Phase 1: Show static shapes with a spinning fixator ---
        spin_duration = 1  # second
        spin_start = core.getTime()
        while core.getTime() - spin_start < spin_duration:
            draw_static_shapes(self.preloaded_static_stimuli)
            elapsed = core.getTime() - spin_start
            self.fixator_stim.ori = (elapsed * 360) % 360
            self.fixator_stim.draw()
            self.win.flip()

        draw_static_shapes(self.preloaded_static_stimuli)
        self.win.flip()

        if self.subjVariables.get('eyetracker') == "yes":
            self.tracker.start_recording()

        self.data_logger.log_trial_event(
            trial_num=self.current_trial,
            phase="gaze_triggered",
            event_type="trial_start",
            additional_info=f"shape_order={'-'.join(self.shape_order)}"
        )

        self.trial_start_time = core.getTime()
        self.data_logger.trial_start_time = self.trial_start_time

        # SEED FIRST SHAPE
        first_shape = self.shape_order[0]
        self.logger.info(f"Auto-triggering first shape: {first_shape}")
        animation = self.animate_shape(first_shape)
        while not animation.update(core.getTime()):
            pass  # Wait for animation to complete

        triggered_flags = {shape: False for shape in self.shape_order}
        triggered_flags[first_shape] = True

        selection_count = 1
        last_selection_time = core.getTime()
        last_triggered = {shape: 0 for shape in self.shape_order}
        last_triggered[first_shape] = last_selection_time

        max_trial_time = 20  # seconds
        required_fixation = 0.25  # seconds
        selection_timeout = 7 # seconds - max time between selections
        initial_selection_timeout = 5 #seconds - max time to wait for first selection

        # Setup dictionaries.
        gaze_histories = {shape: [] for shape in self.shape_order}
        cooldown = 5.0  # seconds cooldown

        active_animation = None    # Currently running animation.
        queued_animation = None    # Candidate for the next animation.

        # Main loop: run until max_trial_time OR we've reached 4 selections and no animation is active.
        while (core.getTime() - self.trial_start_time) < max_trial_time:

            # If we've already reached 4 selections and no animation is playing, end the trial.
            if selection_count >= 4 and active_animation is None:
                break

            current_time = core.getTime()

            if selection_count == 0 and (current_time - self.trial_start_time) > initial_selection_timeout:
                self.logger.info(
                    f"No initial selection made within {initial_selection_timeout} seconds; terminating trial early.")
                break

            if selection_count > 0 and selection_count < 4 and active_animation is None and (
                    current_time - last_selection_time) > selection_timeout:
                self.logger.info(
                    f"No selection for {selection_timeout} seconds after previous selection; terminating trial early.")
                break

            if self.subjVariables.get('eyetracker') == "yes":
                gaze_sample = self.tracker.sample()
            else:
                gaze_sample = None

            # Update active animation.
            if active_animation is not None:
                if active_animation.update(current_time):
                    last_triggered[active_animation.current_shape] = current_time
                    active_animation = None
                    queued_animation = None  # Clear queued candidate when one finishes.

            # In the run_gt_trial method, when promoting a queued animation:
            if active_animation is None and queued_animation is not None:
                # Only promote if we haven't reached 4 selections
                if selection_count < 4:
                    # At this point, the queued animation is being activated,
                    # so we need to log it as an executed (non-queued) selection
                    selection_count += 1
                    last_selection_time = current_time
                    for other_shape in self.shape_order:
                        if other_shape != active_animation.current_shape:
                            last_triggered[other_shape] = 0

                    # Log that the queued selection is now being executed
                    self.data_logger.log_selection(
                        trial_num=self.current_trial,
                        selection_num=selection_count,  # This is the current selection number
                        shape=queued_animation.current_shape,
                        position=self.shape_positions[queued_animation.current_shape],
                        fixation_duration=0,  # We don't know the original fixation duration here
                        queued=False,  # It's no longer queued
                        was_executed=True  # It's being executed now
                    )

                    active_animation = queued_animation
                    queued_animation = None

            self.logger.info(gaze_sample)
            # Process gaze sample for each shape.
            for shape in self.shape_order:
                if self.shapeAOIs[shape].contains(gaze_sample):
                    gaze_histories[shape].append((gaze_sample, current_time))
                    fixation_duration = self._fixation_duration(gaze_histories[shape])

                    if fixation_duration >= required_fixation:

                        # Immediate trigger only if no animation is active and we haven't reached 4.
                        if active_animation is None and selection_count < 4:
                            # Enforce cooldown.
                            if current_time - last_triggered[shape] < cooldown:
                                continue

                            selection_count += 1
                            last_selection_time = current_time
                            self.logger.info(f"Shape {shape} triggered via fixation (immediate).")

                            # Log the selection event
                            self.data_logger.log_selection(
                                trial_num=self.current_trial,
                                selection_num=selection_count,
                                shape=shape,
                                position=self.shape_positions[shape],
                                fixation_duration=fixation_duration,
                                queued=False,
                                was_executed=True,
                                selection_time=current_time
                            )

                            active_animation = LoomAnimation(
                                stim=self.preloaded_static_stimuli[shape],
                                win=self.win,
                                pos=self.shape_positions[shape],
                                current_shape=shape,
                                background_stimuli=self.preloaded_static_stimuli,
                                init_size=self.init_size,
                                target_size=450,
                                init_opacity=self.init_opacity,
                                target_opacity=1.0,
                                loom_duration=1.0,
                                jiggle_duration=0.5,
                                fade_duration=0.25,
                                jiggle_amplitude=5,
                                jiggle_frequency=2,
                                loom_sound=self.loom_sounds[shape],
                                selection_sound=self.selection_sounds[shape]
                            )

                            triggered_flags[shape] = True
                            gaze_histories[shape] = []
                            last_triggered[shape] = current_time
                            for other_shape in self.shape_order:
                                if other_shape != shape:
                                    last_triggered[other_shape] = 0  # Reset cooldown for others

                        # If an animation is active, allow queuing only if selection_count is less than 3.
                        elif active_animation is not None and selection_count < 3:
                            if queued_animation is None or queued_animation.current_shape != shape:
                                self.logger.info(f"Shape {shape} queued as next candidate (N+1)")

                                # Log the queued selection - note was_executed=False because it's not shown yet
                                self.data_logger.log_selection(
                                    trial_num=self.current_trial,
                                    selection_num=selection_count + 1,  # This will be the next selection number
                                    shape=shape,
                                    position=self.shape_positions[shape],
                                    fixation_duration=fixation_duration,
                                    queued=True,
                                    was_executed=False,  # Not executed yet, just queued
                                    selection_time=current_time
                                )

                                queued_animation = LoomAnimation(
                                    stim=self.preloaded_static_stimuli[shape],
                                    win=self.win,
                                    pos=self.shape_positions[shape],
                                    current_shape=shape,
                                    background_stimuli=self.preloaded_static_stimuli,
                                    init_size=self.init_size,
                                    target_size=450,
                                    init_opacity=self.init_opacity,
                                    target_opacity=1.0,
                                    loom_duration=1.0,
                                    jiggle_duration=0.5,
                                    fade_duration=0.25,
                                    jiggle_amplitude=5,
                                    jiggle_frequency=2,
                                    loom_sound=self.loom_sounds[shape],
                                    selection_sound=self.selection_sounds[shape]
                                )
                                triggered_flags[shape] = True
                                gaze_histories[shape] = []
                                #last_triggered[shape] = current_time
                else:
                    # Clear history if gaze is not on the AOI.
                    gaze_histories[shape] = []

            # If nothing is active, refresh the static display.
            if active_animation is None and queued_animation is None:
                draw_static_shapes(self.preloaded_static_stimuli)
                self.win.flip()

            # End of trial processes
            # 1. Mark any queued selection that wasn't executed
            if queued_animation is not None:
                self.data_logger.log_selection(
                    trial_num=self.current_trial,
                    selection_num=selection_count + 1,
                    shape=queued_animation.current_shape,
                    position=self.shape_positions[queued_animation.current_shape],
                    fixation_duration=0,  # Unknown at this point
                    queued=True,
                    was_executed=False
                )

            # 2. Record trial summary
        self.data_logger.end_trial(self.current_trial)

         # 3. Stop eyetracker recording

        if self.subjVariables.get('eyetracker') == "yes":
            self.tracker.stop_recording()

        return selection_count

    def run_ag_trial(self, video_name):
        """
        Play an attention-getting video.

        Parameters:
        -----------
        video_name : str
            Name of the video to play (without extension)
        """
        self.logger.info(f"Playing attention-getter video: {video_name}")

        # Start eyetracking recording if enabled
        if self.subjVariables.get('eyetracker') == "yes":
            self.tracker.start_recording()

        # Log trial start
        current_time = self.data_logger.log_trial_event(
            trial_num=self.current_trial,
            phase="AG",
            event_type="videoStart",
            shape="all",
            position="center",
            additional_info=f"video={video_name}"
        )
        audio_played = False
        if video_name in self.AGsoundMatrix:
            audio = self.AGsoundMatrix[video_name]
            audio.play()
            audio_played = True
            self.logger.info(f"Playing audio: {video_name}")
        else:
            self.logger.warning(f"No matching audio found for {video_name}")

        # Find the video in our loaded movies
        if video_name in self.AGmovieMatrix:
            video = self.AGmovieMatrix[video_name]
            video.size = (self.x_length, self.y_length)
            video.pos = (0,0)
            # Set the video to loop if it's too short
            video.loop = False  # Only play once
            video.play()

            # Keep track of starting time
            start_time = core.getTime()
            total_ag_duration = 5.0
            # Continue displaying until the movie is finished
            while not video.isFinished and (core.getTime() - start_time) < total_ag_duration:
                video.draw()
                self.win.flip()

            remaining_time = total_ag_duration - (core.getTime() - start_time)
            if remaining_time > 0:
                # Show black screen but continue playing audio
                self.disp.fill(self.blackScreen)
                self.disp.show()
                core.wait(remaining_time)

            # Stop the video
            video.stop()

            if audio_played:
                audio.stop()
            # Log duration
            elapsed = core.getTime() - start_time
            self.data_logger.log_trial_event(
                trial_num=self.current_trial,
                phase="AG",
                event_type="videoEnd",
                shape="all",
                position="center",
                additional_info=f"video={video_name}, duration={elapsed:.2f}s"
            )
        else:
            self.logger.error(f"Attention-getter video {video_name} not found in loaded videos")
            # Display a fallback animation if video is not available
            self.display_fallback_ag()
            if audio_played:
                audio.stop()

        # Stop eyetracking recording
        if self.subjVariables.get('eyetracker') == "yes":
            self.tracker.stop_recording()

        # Short pause after the video
        self.win.flip()
        core.wait(.5)

    def display_fallback_ag(self):
        """
        Display a fallback attention-getter animation if the video is not available.
        This uses a pulsing colorful circle as a simple alternative.
        """
        self.logger.info("Displaying fallback attention-getter animation")

        # Create a simple colorful circle
        circle = visual.Circle(
            self.win, radius=300, fillColor="red", lineColor=None, pos=(0, 0)
        )

        # Animation duration
        duration = 5.0  # seconds
        start_time = core.getTime()

        # Loop until duration is reached
        while core.getTime() - start_time < duration:
            elapsed = core.getTime() - start_time

            # Pulsing animation
            size_factor = 0.5 + 0.5 * abs(math.sin(elapsed * 3))
            circle.radius = 200 * size_factor

            # Change color
            hue = (elapsed * 30) % 360
            circle.fillColor = [hue, 1, 1]  # HSV color

            # Draw and flip
            circle.draw()
            self.win.flip()

    def _fixation_duration(self, gaze_history):
        if not gaze_history:
            return 0
        start_time = gaze_history[0][1]
        end_time = gaze_history[-1][1]
        return end_time - start_time

    def run_training_phase(self):
        """
        Run the training phase with interleaved attention-getter videos.
        """
        self.logger.info("Starting training phase.")

        n_training_blocks = 4
        n_trials_per_block = 3

        total_trials = n_training_blocks * n_trials_per_block
        trials_between_ag = 4

            # Play initial attention getter before starting
        ag_video = self.get_next_ag_video()
        if ag_video:
            self.run_ag_trial(ag_video)

        # Loop through each training block
        for trial_num in range(1, total_trials + 1):
            # Run the training trial
            self.run_training_trial()
            
            # Play attention getter after every 'trials_between_ag' trials
            # But don't play one after the very last trial
            if trial_num % trials_between_ag == 0 and trial_num < total_trials:
                ag_video = self.get_next_ag_video()
                if ag_video:
                    self.run_ag_trial(ag_video)

        self.logger.info("Training phase completed.")

    def run_gaze_triggered_phase(self):

        """
        Run the gaze-triggered phase with adaptive trial management.
        Initially attempts 3 trials. If poor engagement, plays attention-getter
        and attempts 6 more trials for a maximum of 9 attempts.
        Continues until 3 successful trials (with all 4 shapes selected).
        """

        self.logger.info("Starting gaze-triggered phase.")

        consecutive_failures_for_ag = 2
        max_total_attempts = 9
        required_successful_trials = 3

        trial_attempts = 0
        successful_trials = 0
        consecutive_failures = 0

        while trial_attempts < max_total_attempts and successful_trials < required_successful_trials:
            if consecutive_failures >= consecutive_failures_for_ag:
                self.logger.info(
                    f"Playing attention-getter after {consecutive_failures} consecutive unsuccessful trials")
                ag_video = self.get_next_ag_video()
                if ag_video:
                    self.run_ag_trial(ag_video)
                consecutive_failures = 0

            trial_attempts += 1
            self.logger.info(f"Starting test trial {trial_attempts} of maximum {max_total_attempts}")

            selections_made = self.run_gt_trial()

            if selections_made == 4:
                successful_trials += 1
                consecutive_failures = 0  # Reset consecutive failures counter
                self.logger.info(f"Successful trial completed ({successful_trials} of {required_successful_trials}).")
            else:
                consecutive_failures += 1
                self.logger.info(
                    f"Trial completed with only {selections_made} selections. Consecutive unsuccessful trials: {consecutive_failures}")

            if successful_trials >= required_successful_trials:
                self.logger.info(f"Gaze-triggered phase completed successfully with {successful_trials} valid trials.")
            else:
                self.logger.info(
                    f"Gaze-triggered phase ended after {trial_attempts} attempts with only {successful_trials} valid trials.")

    def EndDisp(self):
		# show the screen with no stars filled in
		# self.stars['0'][0].draw()
		# print(self.stars)
		# win.flip()

        curStar = self.stars['0'][0]
        		# create screen
        endScreen = libscreen.Screen()
		# build screen
        buildScreenPsychoPy(endScreen, [curStar])

		# present screen
        setAndPresentScreen(self.disp, endScreen)

        core.wait(1)

		# iterate to fill in each star
        for i in range(1, 6, 1):
            # self.stars[str(i)][0].draw()
            #  win.flip()
            curStar = self.stars[str(i)][0]
            curStar.size = (self.x_length, self.y_length)
            # build screen
            buildScreenPsychoPy(endScreen, [curStar])
            # present screen
            setAndPresentScreen(self.disp, endScreen)

            self.AGsoundMatrix['ding'].play()
            core.wait(.5)
            self.AGsoundMatrix['ding'].stop()

		# have the stars jiggle
        self.AGsoundMatrix['applause'].play()
        self.AGsoundMatrix['done'].volume = 2
        self.AGsoundMatrix['done'].play()

        for i in range(4):
            # self.stars['5'][0].draw()
            # win.flip()
            curStar = self.stars['5'][0]
            curStar.size = (self.x_length, self.y_length)
            # build screen
            buildScreenPsychoPy(endScreen, [curStar])
            # present screen
            setAndPresentScreen(self.disp, endScreen)

            core.wait(.5)
            # self.stars['5_left'][0].draw()
            # win.flip()

            curStar = self.stars['5_left'][0]
            curStar.size = (self.x_length, self.y_length)
            # build screen
            buildScreenPsychoPy(endScreen, [curStar])
            # present screen
            setAndPresentScreen(self.disp, endScreen)
            core.wait(.5)

            # self.stars['5'][0].draw()
            # win.flip()
            # core.wait(.5)
            # self.stars['5_right'][0].draw()
            # win.flip()
            # core.wait(.5)

            curStar = self.stars['5'][0]
            curStar.size = (self.x_length, self.y_length)
            # build screen
            buildScreenPsychoPy(endScreen, [curStar])
            # present screen
            setAndPresentScreen(self.disp, endScreen)

            core.wait(.5)
            # self.stars['5_left'][0].draw()
            # win.flip()

            curStar = self.stars['5_right'][0]
            curStar.size = (self.x_length, self.y_length)
            # build screen
            buildScreenPsychoPy(endScreen, [curStar])
            # present screen
            setAndPresentScreen(self.disp, endScreen)
            core.wait(.5)
