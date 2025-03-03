import time
import csv
import os
import pygaze
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

        self.ag_video_list = ['balloons_5', 'bouncyballs_5', 'galaxies_5', 'kangaroo_5']
        self.current_ag_index = 0  # Keep track of which AG video to play next

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

        # Now that we have validated the subject code, initialize all output files
        self.initialize_output_files()

    def initialize_output_files(self):
        """
        Initialize all output files for the experiment, including:
        1. Training data log
        2. Traditional tracking data file (compatible with existing code)
        3. Gaze-triggered selection data
        4. Selection sequence data (for next child in chain)

        Creates appropriate directories if they don't exist.
        """
        # Define file paths
        data_dir = os.path.join("data")
        training_dir = os.path.join(data_dir, "training")
        selections_dir = os.path.join(data_dir, "selections")
        sequence_dir = os.path.join(data_dir, "sequences")
        active_test_dir = os.path.join(data_dir, "activeTest")

        # Create directories if they don't exist
        for directory in [data_dir, training_dir, selections_dir, sequence_dir, active_test_dir]:
            os.makedirs(directory, exist_ok=True)

        # 1. Initialize legacy files for backward compatibility
        training_filepath = os.path.join(training_dir, f"tracking_data_{self.subjVariables['subjCode']}.txt")
        self.trainingOutputFile = open(training_filepath, 'w')

        self.results_filepath = os.path.join(active_test_dir, f"tracking_data_{self.subjVariables['subjCode']}.txt")
        # self.results_file = open(self.results_filepath, 'w')  # Uncomment if needed

        # 2. Training data log - contains trial information and timestamps
        self.training_log_path = os.path.join(training_dir, f"training_log_{self.subjVariables['subjCode']}.csv")
        with open(self.training_log_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'trial_num', 'phase', 'timestamp', 'event_type',
                'shape', 'position', 'additional_info'
            ])

        # 3. Gaze-triggered selection data - contains detailed information about each selection
        self.selection_data_path = os.path.join(selections_dir, f"selections_{self.subjVariables['subjCode']}.csv")
        with open(self.selection_data_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'trial_num', 'selection_num', 'timestamp', 'shape', 'position',
                'fixation_duration_ms', 'rt_from_trial_start_ms', 'rt_from_previous_selection_ms',
                'queued_selection', 'was_executed'
            ])

        # 4. Sequence data - simplified format containing just the sequence of selections
        #    This is what will be used for the next child in the chain
        self.sequence_data_path = os.path.join(sequence_dir, f"sequence_{self.subjVariables['subjCode']}.csv")
        with open(self.sequence_data_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'trial_num', 'selection_order', 'shape_sequence', 'position_sequence',
                'timing_sequence_ms'
            ])

        self.logger.info(f"Output files initialized:")
        self.logger.info(f"  Training file: {training_filepath}")
        self.logger.info(f"  Training log: {self.training_log_path}")
        self.logger.info(f"  Selection data: {self.selection_data_path}")
        self.logger.info(f"  Sequence data: {self.sequence_data_path}")

        # Initialize tracking variables
        self.current_trial = 0
        self.last_selection_time = 0
        self.trial_selections = []  # Will store selections for current trial

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
        self.current_trial = 0
        self.last_selection_time = 0


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

    def log_training_events(self, trial_num, current_shape, event_type):
        """
        Log events during the training phase to the eyetracker.

        Parameters:
        -----------
        trial_num : int
            Current trial number
        current_shape : str
            The shape being presented/animated (e.g., "circle", "cross")
        event_type : str
            The type of event (e.g., "trial_start", "animation_start", "animation_end")
        """
        if self.subjVariables.get('eyetracker') == "yes" and hasattr(self, 'tracker'):
            timestamp = core.getTime()
            log_message = f"training_trial_{trial_num}_{current_shape}_{event_type}_{timestamp}"
            self.logger.info(f"Logging eyetracker event: {log_message}")
            self.tracker.log(log_message)

    def log_trial_event(self, trial_num, phase, event_type, shape="all", position="", additional_info=""):
        """
        Log an event during a trial to the training log file and eyetracker.

        Parameters:
        -----------
        trial_num : int
            Current trial number
        phase : str
            "training" or "gaze_triggered"
        event_type : str
            Type of event (e.g., "trial_start", "animation_begin", "fixation")
        shape : str
            The shape involved (or "all" for events involving all shapes)
        position : str
            Position of the shape (if applicable)
        additional_info : str
            Any additional information to log

        Returns:
        --------
        float
            Timestamp when the event was logged
        """
        timestamp = core.getTime()

        # Log to training CSV file
        with open(self.training_log_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                trial_num, phase, timestamp, event_type,
                shape, position, additional_info
            ])

        # Also log to eyetracker if available
        if self.subjVariables.get('eyetracker') == "yes" and hasattr(self, 'tracker'):
            log_message = f"{phase}_trial{trial_num}_{event_type}"
            if shape != "all":
                log_message += f"_{shape}"
            if position:
                log_message += f"_{position}"

            self.tracker.log(log_message)

        return timestamp  # Return time for convenience in calling functions

    def log_selection(self, trial_num, selection_num, shape, position, fixation_duration,
                      queued=False, was_executed=True, selection_time=None):
        """
        Log a selection event to both eyetracker and CSV files.

        Parameters:
        -----------
        trial_num : int
            Current trial number
        selection_num : int
            Current selection number within the trial
        shape : str
            Selected shape name
        position : str or tuple
            Position of the selected shape
        fixation_duration : float
            Duration of fixation before selection (in seconds)
        queued : bool
            Whether this selection was queued (not immediately executed)
        was_executed : bool
            Whether the selection was actually shown to the infant
            - If queued=True, this should typically be False when initially logged
            - Later, when the queued selection is actually shown, this should be True
        selection_time : float, optional
            Timestamp when selection occurred. If None, uses current time.
        """
        # Get current time if not provided
        if selection_time is None:
            selection_time = core.getTime()

        # Format position as string if it's a tuple
        position_str = str(position) if isinstance(position, (list, tuple)) else position

        # Calculate relative timestamps (in milliseconds)
        rt_from_trial_start = (selection_time - self.trial_start_time) * 1000  # Convert to ms

        if self.last_selection_time > 0:
            rt_from_previous = (selection_time - self.last_selection_time) * 1000  # Convert to ms
        else:
            rt_from_previous = rt_from_trial_start

        # Update last selection time and record in trial_selections ONLY if
        # this selection was actually shown to the infant (was_executed=True)
        if was_executed:
            self.last_selection_time = selection_time

            # Only add to trial_selections if it was actually shown to the infant
            self.trial_selections.append({
                'shape': shape,
                'position': position_str,
                'timestamp': selection_time,
                'rt_from_trial_start': rt_from_trial_start
            })

        # Log to selection data CSV
        with open(self.selection_data_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                trial_num,
                selection_num,
                selection_time,
                shape,
                position_str,
                fixation_duration * 1000,  # Convert to ms
                rt_from_trial_start,
                rt_from_previous,
                queued,
                was_executed  # This should be False for queued selections until they're shown
            ])

        # Log to eyetracker
        if self.subjVariables.get('eyetracker') == "yes" and hasattr(self, 'tracker'):
            # Create a descriptive event message
            event_type = "queued" if queued else "direct"
            execution = "executed" if was_executed else "discarded"

            log_message = (f"selection_trial{trial_num}_num{selection_num}_{shape}_"
                           f"{event_type}_{execution}_duration{int(fixation_duration * 1000)}ms")

            self.logger.info(f"Logging to eyetracker: {log_message}")
            self.tracker.log(log_message)

        # Also log to training log CSV for comprehensive record
        event_type = "queued_selection" if queued else "selection"
        additional_info = (f"executed={was_executed}, fixation_duration={int(fixation_duration * 1000)}ms, "
                           f"rt={int(rt_from_trial_start)}ms")

        self.log_trial_event(
            trial_num,
            "gaze_triggered",
            event_type,
            shape,
            position_str,
            additional_info
        )

        self.logger.info(
            f"Selection logged: Trial {trial_num}, Selection {selection_num}, Shape {shape}, Queued={queued}")
        return selection_time  # Return time for convenience in calling functions

    def run_training_trial(self):
        # --- Phase 0: Setup eyetracking ---
        # Increment trial counter
        self.current_trial += 1

        # Record trial start time
        self.trial_start_time = core.getTime()

        # Start eyetracking recording for this trial
        if self.subjVariables.get('eyetracker') == "yes":
            self.tracker.start_recording()

        # Log trial start
        self.log_trial_event(
            trial_num=self.current_trial,
            phase="training",
            event_type="trial_start",
            additional_info=f"shape_order={'-'.join(self.shape_order)}"
        )

        # Log trial start
        self.log_training_events(self.current_trial, "all", "trial_start")

        # --- Phase 1: Show preloaded static shapes with a spinning wheel ---
        spin_duration = 1 #second
        spin_start = core.getTime()

        while core.getTime() - spin_start < spin_duration:
            draw_static_shapes(self.preloaded_static_stimuli)
            elapsed = core.getTime() - spin_start
            self.fixator_stim.ori = (elapsed * 360) % 360
            self.fixator_stim.draw()
            self.win.flip()

        self.log_trial_event(
            trial_num=self.current_trial,
            phase="training",
            event_type="fixator_end"
        )

        draw_static_shapes(self.preloaded_static_stimuli)
        self.win.flip()

        # --- Phase 2: Animate each shape ---
        # Sequentially animate each shape in order.
        for shape_index, shape in enumerate(self.shape_order):
            self.logger.info(f"Animating shape: {shape}")
            animation_start_time = self.log_trial_event(
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

            self.log_trial_event(
                trial_num=self.current_trial,
                phase="training",
                event_type="animation_end",
                shape=shape,
                position=str(self.shape_positions[shape]),
                additional_info=f"duration={(current_time - animation_start_time) * 1000:.0f}ms"
            )

            draw_static_shapes(self.preloaded_static_stimuli)
            self.win.flip()

        self.log_trial_event(
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

        self.log_trial_event(
            trial_num=self.current_trial,
            phase="gaze_triggered",
            event_type="trial_start",
            additional_info=f"shape_order={'-'.join(self.shape_order)}"
        )

        self.trial_start_time = core.getTime()
        max_trial_time = 15  # seconds
        required_fixation = 0.33  # seconds
        selection_count = 0

        # Setup dictionaries.
        gaze_histories = {shape: [] for shape in self.shape_order}
        triggered_flags = {shape: False for shape in self.shape_order}
        last_triggered = {shape: 0 for shape in self.shape_order}
        cooldown = 0.5  # seconds cooldown

        active_animation = None    # Currently running animation.
        queued_animation = None    # Candidate for the next animation.

        # Main loop: run until max_trial_time OR we've reached 4 selections and no animation is active.
        while (core.getTime() - self.trial_start_time) < max_trial_time:

            # If we've already reached 4 selections and no animation is playing, end the trial.
            if selection_count >= 4 and active_animation is None:
                break

            current_time = core.getTime()

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

                    # Log that the queued selection is now being executed
                    self.log_selection(
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

            # Get a gaze sample.
            if self.subjVariables.get('eyetracker') == "yes":
                gaze_sample = self.tracker.sample()
            else:
                gaze_sample = None  # Optionally simulate gaze input.

            if gaze_sample is None:
                if (current_time - self.trial_start_time) > 5:
                    self.logger.info("No gaze detected for 5 seconds; displaying re-cue.")
                continue

            self.logger.info(gaze_sample)
            # Process gaze sample for each shape.
            for shape in self.shape_order:
                if self.shapeAOIs[shape].contains(gaze_sample):
                    gaze_histories[shape].append((gaze_sample, current_time))
                    fixation_duration = self._fixation_duration(gaze_histories[shape])

                    if fixation_duration >= required_fixation:
                        # Enforce cooldown.
                        if current_time - last_triggered[shape] < cooldown:
                            continue

                        # Immediate trigger only if no animation is active and we haven't reached 4.
                        if active_animation is None and selection_count < 4:
                            selection_count += 1
                            self.logger.info(f"Shape {shape} triggered via fixation (immediate).")

                            # Log the selection event
                            self.log_selection(
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

                        # If an animation is active, allow queuing only if selection_count is less than 3.
                        elif active_animation is not None and selection_count < 3:
                            if queued_animation is None or queued_animation.current_shape != shape:
                                self.logger.info(f"Shape {shape} queued as next candidate (N+1)")

                                # Log the queued selection - note was_executed=False because it's not shown yet
                                self.log_selection(
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
                                last_triggered[shape] = current_time
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
                self.log_selection(
                    trial_num=self.current_trial,
                    selection_num=selection_count + 1,
                    shape=queued_animation.current_shape,
                    position=self.shape_positions[queued_animation.current_shape],
                    fixation_duration=0,  # Unknown at this point
                    queued=True,
                    was_executed=False
                )

            # 2. Record trial summary
            self.end_trial(self.current_trial)

            # 3. Stop eyetracker recording

            if self.subjVariables.get('eyetracker') == "yes":
                self.tracker.stop_recording()

            self.logger.info(f"Gaze-triggered trial {self.current_trial} completed with {selection_count} selections")

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
        current_time = self.log_trial_event(
            trial_num=self.current_trial,
            phase="attention_getter",
            event_type="video_start",
            shape="all",
            position="center",
            additional_info=f"video={video_name}"
        )

        # Find the video in our loaded movies
        if video_name in self.AGmovieMatrix:
            video = self.AGmovieMatrix[video_name]

            # Set the video to loop if it's too short
            video.loop = False  # Only play once
            video.play()

            # Keep track of starting time
            start_time = core.getTime()

            # Continue displaying until the movie is finished
            while not video.isFinished:
                video.draw()
                self.win.flip()

            # Stop the video
            video.stop()

            # Log duration
            elapsed = core.getTime() - start_time
            self.log_trial_event(
                trial_num=self.current_trial,
                phase="attention_getter",
                event_type="video_end",
                shape="all",
                position="center",
                additional_info=f"video={video_name}, duration={elapsed:.2f}s"
            )
        else:
            self.logger.error(f"Attention-getter video {video_name} not found in loaded videos")
            # Display a fallback animation if video is not available
            self.display_fallback_ag()

        # Stop eyetracking recording
        if self.subjVariables.get('eyetracker') == "yes":
            self.tracker.stop_recording()

        # Short pause after the video
        core.wait(0.5)

    def display_fallback_ag(self):
        """
        Display a fallback attention-getter animation if the video is not available.
        This uses a pulsing colorful circle as a simple alternative.
        """
        self.logger.info("Displaying fallback attention-getter animation")

        # Create a simple colorful circle
        circle = visual.Circle(
            self.win,
            radius=300,
            fillColor="red",
            lineColor=None,
            pos=(0, 0)
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

    def end_trial(self, trial_num):
        """
        End a trial and record the sequence of selections to the sequence file.
        This function summarizes the trial data and writes it to the sequence file.

        Parameters:
        -----------
        trial_num : int
            The trial number that is ending
        """
        # Only process if we have selections
        if not self.trial_selections:
            self.logger.info(f"Trial {trial_num} ended with no selections")
            return

        # Extract sequences
        shapes = [s['shape'] for s in self.trial_selections]
        positions = [s['position'] for s in self.trial_selections]

        # Calculate timing sequence (time between selections)
        timestamps = [s['timestamp'] for s in self.trial_selections]
        timing_ms = []
        for i in range(1, len(timestamps)):
            timing_ms.append(int((timestamps[i] - timestamps[i - 1]) * 1000))  # Convert to ms

        # Add first timing (from trial start)
        first_timing = int((timestamps[0] - self.trial_start_time) * 1000)  # Convert to ms
        timing_ms = [first_timing] + timing_ms

        # Format sequences as comma-separated strings
        shape_sequence = ",".join(shapes)
        position_sequence = ",".join([str(p) for p in positions])
        timing_sequence = ",".join([str(t) for t in timing_ms])

        # Write to sequence file
        with open(self.sequence_data_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                trial_num,
                len(shapes),
                shape_sequence,
                position_sequence,
                timing_sequence
            ])

        # Log trial summary information
        summary_info = (f"shapes={shape_sequence}, positions={position_sequence}, "
                        f"timings={timing_sequence}")

        self.log_trial_event(
            trial_num=trial_num,
            phase="gaze_triggered",
            event_type="trial_end",
            additional_info=f"selections={len(shapes)}, {summary_info}"
        )

        self.logger.info(f"Trial {trial_num} ended with {len(shapes)} selections: {shape_sequence}")

        # Reset trial selections for next trial
        self.trial_selections = []

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
        n_training_blocks = 2
        n_training_trials = 2
        # Loop through each training block
        for block in range(1, n_training_blocks + 1):
            self.logger.info(f"Starting training block {block} of {n_training_blocks}")

            # 1. Play an attention-getter video
            ag_video = self.get_next_ag_video()
            if ag_video:
                self.run_ag_trial(ag_video)
            for trial in range(1, n_training_trials + 1):
                # 2. Run the training trial
                self.run_training_trial()

        self.logger.info("Training phase completed.")

    def run_gaze_triggered_phase(self):
        self.logger.info("Starting gaze-triggered phase.")
        n_trials = 3  # You can adjust this or retrieve from self.config, e.g., self.config.get('n_training_trials', 5)
        for trial in range(1, n_trials + 1):
            self.logger.info(f"Starting test trial {trial} of {n_trials}.")
            self.run_gt_trial()
            core.wait(0.5)
        self.logger.info("Gaze-triggered phase completed.")
