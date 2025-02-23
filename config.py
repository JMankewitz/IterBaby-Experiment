# Configuration parameters for the experiment.
EXPERIMENT_CONFIG = {
    'training_duration': 15,         # e.g., number of repetitions or time in seconds
    'loom_duration': 1,              # duration of the looming animation in seconds
    'fixation_threshold': 0.5,       # required fixation time (in seconds)
    'gaze_trigger_timeout': 5,       # max time to wait for a fixation before re-cueing
    'results_file': 'experiment_results.csv',
    'log_file': 'experiment_log.txt',
    # Additional parameters (e.g., screen resolution, shape positions, etc.) can be added here.
}
