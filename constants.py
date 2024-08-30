# Settings keys
CONFIG_GCODE_FLAVOR = 'SETTING_GCODE_FLAVOR'
CONFIG_INPUT_FILE = 'CONFIG_INPUT_FILE'
CONFIG_OUTPUT_FILE = 'CONFIG_OUTPUT_FILE'
CONFIG_TOOLCHANGE_MINIMAL_FILE = 'CONFIG_TOOLCHANGE_MINIMAL_FILE'
CONFIG_PERIODIC_COLORS = 'CONFIG_PERIODIC_COLORS'
CONFIG_REPLACEMENT_COLORS = 'CONFIG_REPLACEMENT_COLORS'
CONFIG_LINE_ENDING = 'CONFIG_LINE_ENDING'
CONFIG_APP_NAME = 'CONFIG_APP_NAME'
CONFIG_APP_VERSION = 'CONFIG_APP_VERSION'



# Gcode Regex and Constants

# Movement
MOVEMENT_G0 = 'G0'
MOVEMENT_G1 = 'G1'
MOVEMENT_G = '^(?:G(?:0|1) )\s?(?:([XYZE])(-?\d*\.?\d*))?(?:\s+([XYZE])(-?\d*\.?\d*))?(?:\s+([XYZE])(-?\d*\.?\d*))?(?:\s+([XYZE])(-?\d*\.?\d*))?(?: )*(?:(;)?(.*))$'

# Dwell
DWELL_G4 = 'G4 F'

# Layer Change
MACHINE_M1 = '^M1\s+' #signal new layer followed by reset extrusion comments
#LAYER_CHANGE = '^;\s?(?:feature plane change)'
#LAYER_Z_HEIGHT = '^;\s?(?:Z_HEIGHT|Z):\s?(\d*\.?\d*)' # Current object layer height including current layer height
#LAYER_HEIGHT = '^;\s?(?:LAYER_HEIGHT|HEIGHT):\s?(\d*\.?\d*)' # Current layer height

# Feature/Line Type
FEATURE_TYPE = ';\s?(?:feature)\s?(.*)'
LAYER_CHANGE = 'plane change'
TRAVEL = 'travel'
INFILL = 'fill'
UNKNOWN = 'unknown'
OUTER_PERIMETER = 'outer perimeter'
INNER_PERIMETER = 'inner perimeter'

FEATURE_TYPE_WRITE_OUT = '; feature '
PULSE_OFF='PRIO_OFF'
PULSE_ON='PRIO_ON'

FAKE_MOVE = '; fake move for elemx builder preview'

LAYERS_COMPLETED_WRITE_OUT = 'LayersCompleted=' #number of layers completed starting from 1

# User config settings

# G-code options
ADD_ELEMX_PREVIEW_MOVE = False #enable for preview
DWELL_BEFORE_EXTRUDE = False #also enable this for preview
DWELL_AFTER_EXTRUDE = False
OUTPUT_RENAME_OUTER_PERIMETER = INNER_PERIMETER #None or new feature type string

DEBUG_PREVIEW_ALL_DROPLETS_SUPPORTED = False #force all generated droplets to be seen as "supported"

# PRINT SETTINGS
LAYER_HEIGHT = 0.24 #mm

# DROPLET
DROPLET_WIDTH = 0.510 #mm
#DROPLET_OVERLAP_PERC = 0.5 #%
DROPLET_RASTER_RESOLUTION_PERC = 0.25 #% of droplet width
DROPLET_RASTER_SUPPORTED_SEARCH_KERNEL_SIZE = 5 # in raster index widths (must be odd numbers)
DROPLET_RASTER_SUPPORTED_SEARCH_CORNER_RADIUS = 1 # in raster index widths
DROPLET_RASTER_COLLISION_SEARCH_KERNEL_SIZE = 5
DROPLET_RASTER_COLLISION_SEARCH_CORNER_RADIUS = 1

DROPLET_DWELL = 0.2 #s
DROPLET_EXTRUSION_MULTIPLIER = .75 # multiply by this value

# INFILL INSET
MINIMUM_INSET_DROPLET_WIDTH = 2.5 #inset that drops avoid all the time. This includes the last layers of a bounding box where the normal inset is scaled towards 0.
MINIMUM_BOUNDARY_BOX_INSET = DROPLET_WIDTH*MINIMUM_INSET_DROPLET_WIDTH #mm
INSET_DROPLET_WIDTH = 3 #this is in addition to minimum inset!
BOUNDARY_BOX_INSET = DROPLET_WIDTH*INSET_DROPLET_WIDTH #mm

# INFILL Z offset
# raise Z by this amount when doing any infill feature moves
INFILL_Z_OFFSET = 20 #mm

# Input/Output files
MPF_INPUT_FILE = 'test-square-25x25x10.mpf'
#MPF_INPUT_FILE = 'long-rect-piece-205x20x20.mpf'

INSET_FILENAME = f'{INSET_DROPLET_WIDTH+MINIMUM_INSET_DROPLET_WIDTH:.2f}'
EXTRUSION_MULTIPLIER_FILENAME = f'{DROPLET_EXTRUSION_MULTIPLIER}'

MPF_OUTPUT_FILE = f"long-rect-{EXTRUSION_MULTIPLIER_FILENAME.replace('.','-')}mul-{INSET_FILENAME.replace('.','-')}inset-s{int(DROPLET_RASTER_SUPPORTED_SEARCH_KERNEL_SIZE)}k{int(DROPLET_RASTER_SUPPORTED_SEARCH_CORNER_RADIUS)}r-c{int(DROPLET_RASTER_COLLISION_SEARCH_KERNEL_SIZE)}k{int(DROPLET_RASTER_COLLISION_SEARCH_CORNER_RADIUS)}r.mpf"
GCODE_OUTPUT_FILE = 'long-rect-output.gcode'