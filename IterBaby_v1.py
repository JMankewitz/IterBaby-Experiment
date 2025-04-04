from experiment import InfantEyetrackingExperiment
from config import EXPERIMENT_CONFIG
from utils import setup_logging

def main():
    # Initialize logging (clears any existing log file)
    logger = setup_logging(EXPERIMENT_CONFIG['log_file'])
    
    # Create an instance of the experiment with configuration and logger
    experiment = InfantEyetrackingExperiment(EXPERIMENT_CONFIG, logger)
    
    # Run each phase of the experiment
    experiment.run_training_phase()
    experiment.run_gaze_triggered_phase()
    experiment.EndDisp()
if __name__ == '__main__':
    main()
