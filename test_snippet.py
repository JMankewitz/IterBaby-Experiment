from psychopy import visual, core
import math, random, os

def assign_shape_positions(shapes, possible_locations):
    if len(shapes) > len(possible_locations):
        raise ValueError("Not enough locations for the number of shapes.")
    locations_copy = possible_locations.copy()
    random.shuffle(locations_copy)
    shape_positions = {}
    for i, shape in enumerate(shapes):
        shape_positions[shape] = locations_copy[i]
    return shape_positions

def draw_static_shapes(win, shape_positions, image_files, init_size=100, init_opacity=0.3):
    """
    Draws all shapes in their baseline state and flips the window.
    Returns a dictionary of ImageStim objects.
    """
    from psychopy import visual  # ensure we have access here
    stimuli = {}
    for shape, pos in shape_positions.items():
        stim = visual.ImageStim(win, image=image_files[shape], pos=pos, 
                                  size=init_size, opacity=init_opacity, units='pix', ori=0)
        stim.draw()
        stimuli[shape] = stim
    win.flip()
    return stimuli

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
    core.wait(0.2)


# --- Experiment Class Integration ---

class InfantEyetrackingExperiment:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        
        # Create a window using pixel units.
        self.win = visual.Window(size=(1280, 720), units='pix', color='black')
        
        # Set up paths. Adjust 'base_path' as necessary.
        base_path = os.path.abspath("stimuli/images")
        self.image_files = {
            "circle": os.path.join(base_path, "circle.png"),
            "cross": os.path.join(base_path, "cross.png"),
            "star": os.path.join(base_path, "star.png"),
            "t": os.path.join(base_path, "t.png")
        }
        
        # Define shape order and positions (using pixel coordinates).
        self.shape_order = ["circle", "cross", "star", "t"]
        # You can either use a hard-coded dict or assign randomly:
        self.shape_positions = {
            "circle": (-320, 180),
            "cross": (320, 180),
            "star": (-320, -180),
            "t": (320, -180)
        }
        # Alternatively, to randomize:
        # possible_locations = [(-320, 180), (320, 180), (-320, -180), (320, -180)]
        # self.shape_positions = assign_shape_positions(self.shape_order, possible_locations)
        self.logger.info(f"Assigned shape positions: {self.shape_positions}")

    def run_trial(self):
    # Draw all shapes in baseline state.
        static_stimuli = draw_static_shapes(self.win, self.shape_positions, self.image_files,
                                            init_size=100, init_opacity=0.3)
        core.wait(0.5)
        
        # Animate each shape in order.
        for shape in self.shape_order:
            self.logger.info(f"Animating shape: {shape}")
            # Get the stimulus for the current shape.
            stim = static_stimuli[shape]
            pos = self.shape_positions[shape]
            loom_shape_with_background(stim, self.win, pos, current_shape=shape,
                                    background_positions=self.shape_positions,
                                    image_files=self.image_files,
                                    init_size=100, target_size=150,
                                    init_opacity=0.3, target_opacity=1.0,
                                    loom_duration=1.0, jiggle_duration=0.5, fade_duration=0.5,
                                    jiggle_amplitude=5, jiggle_frequency=2)
            # Optionally, redraw the static display between animations.
            static_stimuli = draw_static_shapes(self.win, self.shape_positions, self.image_files,
                                                init_size=100, init_opacity=0.3)
            core.wait(0.2)

    def run_training_phase(self):
        self.logger.info("Starting training phase.")
        self.run_trial()
        self.logger.info("Training phase completed.")
        core.wait(1)

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("InfantEyetracking")
    
    experiment = InfantEyetrackingExperiment({}, logger)
    experiment.run_training_phase()
    experiment.win.close()
