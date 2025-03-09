import csv
import os
import time
from psychopy import core
class DataLogger:
    def __init__(self, experiment_controller):
        self.controller = experiment_controller
        self.logger = experiment_controller.logger

        # Access needed variables from controller
        self.config = experiment_controller.config
        self.subjVariables = experiment_controller.subjVariables
        self.trial_selections = []
        self.trial_start_time = 0
        self.last_selection_time = 0

        # Initialize output files
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

    def log_to_eyetracker(self, message):
        """Send a log message to the eyetracker if available"""
        if self.subjVariables.get('eyetracker') == "yes" and hasattr(self.controller, 'tracker'):
            self.logger.info(f"Logging to eyetracker: {message}")
            self.controller.tracker.log(message)

    def log_trial_event(self, trial_num, phase, event_type, shape="all", position="", additional_info=""):
        """
        Log an event during a trial to the log file and eyetracker.

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
        log_message = f"{phase}_trial{trial_num}_{event_type}"
        if shape != "all":
            log_message += f"_{shape}"
        if position:
            log_message += f"_{position}"

        self.log_to_eyetracker(log_message)

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

    def start_trial(self, trial_num):
        """Initialize data for a new trial"""
        self.trial_selections = []
        self.trial_start_time = core.getTime()
        self.last_selection_time = 0

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
