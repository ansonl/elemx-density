import enum, math, gc
from constants import *

class StatusQueueItem:
  def __init__(self):
    self.statusLeft = None
    self.statusRight = None
    self.progress = None

# Position
class Position:
  def __init__(self, x=0, y=0, z=0, e=0):
    self.X: float = x
    self.Y: float = y
    self.Z: float = z
    self.E: float = e
    self.F: float = 0
    self.FTravel: float = 0
    self.comment: str = None

  # compare X/Y/Z/E for equality
  def __eq__(self, other): 
    if not isinstance(other, Position):
      # don't attempt to compare against unrelated types
      return NotImplemented

    return self.X == other.X and self.Y == other.Y and self.Z == other.Z and self.E == other.E

# Bounding Box
class BoundingBox:
  def __init__(self, origin: Position, size: Position, density: float = 1):
    self.origin = origin
    self.size = size
    self.density: float = density
    self.targetDensity: float = 1
    self.dropletOverlap = DROPLET_OVERLAP_PERC #percentage of droplet width
    self.dropletRaster: list[None|list[list[int]]] = None #[last|current][x][y]

  def initializeDropletRasterLayer(self):
    return [[0 for _ in range(0, 1 + math.ceil(self.size.Y/(DROPLET_WIDTH*self.dropletOverlap)))] for _ in range(0, 1 + math.ceil(self.size.X/(DROPLET_WIDTH*self.dropletOverlap)))]

  def initializeDropletRaster(self):
    self.dropletRaster = [None, self.initializeDropletRasterLayer()]

  def freeDropletRaster(self):
    self.dropletRaster = None

  def advanceDropletRasterNextLayer(self):
    if self.dropletRaster:
      self.dropletRaster[0] = self.dropletRaster[1]
      gc.collect()
      self.dropletRaster[1] = self.initializeDropletRasterLayer()

  # Return number of layers needed to stack to together to get to the target density (going up). Start density is first layer. Target density is last layer.
  def numLayersToTargetDensity(self):
    return self.targetDensity / self.density
  
  # Return density % at global layer height for this bounding box
  def densityAtLayerHeightForTargetDensity(self, layerHeight: float) -> float:
    lastLayerHeight = self.origin.Z+self.size.Z
    lastStartDensityLayerHeight = lastLayerHeight-self.numLayersToTargetDensity()*LAYER_HEIGHT

    if layerHeight <= lastStartDensityLayerHeight:
      return self.density
    elif layerHeight >= lastLayerHeight:
      return self.targetDensity
    else: 
      percentThroughBoxHeight = (layerHeight - lastStartDensityLayerHeight) / (lastLayerHeight - lastStartDensityLayerHeight)
      return self.density + percentThroughBoxHeight * (self.targetDensity-self.density)


# State of current Print FILE
class PrintState:
  def __init__(self):
    self.height: float = -1 
    self.doneLayerCount: int = 0
    self.layerHeight: float = 0
    self.previousLayerHeight: float = 0
    self.layerStart: int = 0
    self.layerEnd: int = 0
    self.lastFeature: Feature = None
    self.prevLayerLastFeature: Feature = None

    # Infill movements read in but not written out
    self.infillMovementQueue: list[Movement] = None
    self.infillMovementQueueOriginalStartPosition: Position = None

    # Infill modified droplet stats
    self.infillModifiedDropletsOriginal: int = 0
    self.infillModifiedDropletsNeededForDensity: int = 0
    self.infillModifiedDropletsSupportedAvailable: int = 0

    # Movement info
    self.originalPosition: Position = Position() 
    # E delta
    self.deltaE: float = 0 # how much we have deviated from the original E position

    # Prime tower / Toolchange values for current layer
    self.features: list[Feature] = [] # Printing features
    self.primeTowerFeatures: list[Feature] = [] # The available prime tower features.
    self.stopPositions: list[int] = []
    self.toolchangeInsertionPoint: int = 0
    self.featureWipeEndPrime: Position = None # prime values at end of wipe_end

    #Loop settings
    self.skipWrite: bool = False
    self.skipWriteForCurrentLine: bool = False
    self.prevLayerSkipWrite: bool = False
    
    #self.toolchangeBareInsertionPoint: Feature = None
    #self.toolchangeFullInsertionPoint: Feature = None
    #self.toolchangeNewColorIndex: int = -1
    #self.skipOriginalPrimeTowerAndToolchangeOnLayer: bool = False
    #self.skipOriginalToolchangeOnLayer: bool = False

class Feature:
  def __init__(self):
    self.featureType: str = None
    self.start: int = 0
    self.end: int = 0
    self.toolchange: Feature = None
    self.isPeriodicColor: bool = False
    self.originalColor: int = -1
    self.printingColor: int = -1
    self.startPosition: Position = Position()
    self.wipeStart: Feature = None
    self.wipeEnd: Feature = None
class PeriodicColor:
  def __init__(self, colorIndex = -1, startHeight = -1, endHeight = -1, height = -1, period = -1, enabledFeatures=[]):
    self.colorIndex: int = colorIndex
    self.startHeight: float = startHeight
    self.endHeight: float = endHeight
    self.height: float = height
    self.period: float = period
    self.enabledFeatures: list[str] = enabledFeatures

class PrintColor:
  def __init__(self, index=-1, replacementColorIndex=-1, humanColor=None):
    self.index: int = index
    self.replacementColorIndex: int = replacementColorIndex #the current replacement color
    self.humanColor: str = humanColor

loadedColors: list[PrintColor] = [
  PrintColor(0, -1, 'Base Color'),
  PrintColor(1, -1, 'River Color'),
  PrintColor(2, -1, 'Isoline Color'),
  PrintColor(3, -1, 'High Elevation Color')
]
class ReplacementColorAtHeight:
  def __init__(self, colorIndex, originalColorIndex, startHeight, endHeight):
    self.colorIndex: int = colorIndex
    self.originalColorIndex: int = originalColorIndex
    self.startHeight: float = startHeight
    self.endHeight: float = endHeight

    
# Movements
class Movement:
  # Extrusion amount is based on start and end position E.
  # For travel and extrude-only movements, X,Y location only uses end position.
  # Droplet is an extrude-only movement.

  def __init__(self, startPos: Position = None, endPos: Position = None, boundingBox: BoundingBox = None, originalGcode: str = None, feature: Feature = None):
    self.start: Position = startPos #original gcode start. is None if not a travel or printing command
    self.end: Position = endPos #original gcode end
    self.boundingBox: BoundingBox = boundingBox
    self.originalGcode: str = originalGcode #original gcode only written out for misc gocde
    self.feature: Feature = feature # the active feature
    self.supportedPositions: list[Position] = [] #supported positions underneath from the previous layer

    # E movement for a droplet
    self.dropletE: None

    # Droplet movements that replace this move
    self.dropletMovements: list[Movement] = None

  # Return if this Movement is actually a Droplet (extrude only move)
  def isDroplet(self):
    return (self.start.X == self.end.X) and (self.start.Y == self.end.Y)
  
  def adjustE(self, startE: float):
    # Get relative E movement
    relativeE = self.end.E - self.start.E 

    # Set start to the last tracked queue position
    self.start.E = startE
    self.end.E = self.start.E + relativeE

  # return gcode and adjustE if specified
  def gcode(self, adjustE: bool = False, deltaE: float = None):
    gcode = MOVEMENT_G1

    gcode += f" X{self.end.X:.5f} Y{self.end.Y:.4f} E{(self.end.E + deltaE if adjustE else self.end.E):.5f}"
    
    gcode += f"{' ;' if (self.end.comment or self.boundingBox) else ''}{self.end.comment if self.end.comment else ''}{f'; EInc={self.end.E-self.start.E}'}"
    return gcode
  
  def travelGcodeToStart(self):
    gcode = ''
    gcode += f"{FEATURE_TYPE_WRITE_OUT}{TRAVEL}\n"
    gcode += f"{PULSE_OFF}\n"
    gcode += MOVEMENT_G0
    gcode += f" X{self.start.X:.5f} Y{self.start.Y:.4f} ;Travel to start"
    return gcode

  def travelGcodeToEnd(self):
    gcode = ''
    gcode += f"{FEATURE_TYPE_WRITE_OUT}{TRAVEL}\n"
    gcode += f"{PULSE_OFF}\n"
    gcode += MOVEMENT_G0
    gcode += f" X{self.end.X:.5f} Y{self.end.Y:.4f} ;Travel to end"
    return gcode
  
  # Return G-code for extrude only move. Assume E position is pre-adjusted and final.
  def extrudeOnlyGcode(self, adjustE: bool = False, deltaE: float = None):
    gcode = ''
    gcode += f"{FEATURE_TYPE_WRITE_OUT}{INFILL}\n"
    gcode += f"{PULSE_ON}\n"
    gcode += MOVEMENT_G1
    gcode += f" E{(self.end.E + deltaE if adjustE else self.end.E):.5f} ; EInc={self.end.E-self.start.E}"
    return gcode
