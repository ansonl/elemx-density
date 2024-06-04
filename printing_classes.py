import enum
from constants import *

class StatusQueueItem:
  def __init__(self):
    self.statusLeft = None
    self.statusRight = None
    self.progress = None

# Position
class Position:
  def __init__(self):
    self.X: float = 0
    self.Y: float = 0
    self.Z: float = 0
    self.E: float = 0
    self.F: float = 0
    self.FTravel: float = 0
    self.comment: str = None

# Bounding Box
class BoundingBox:
  def __init__(self, origin: Position, size: Position, density: float = 1):
    self.origin = origin
    self.size = size
    self.density = density

# State of current Print FILE
class PrintState:
  def __init__(self):
    self.height: float = -1 
    self.layerHeight: float = 0
    self.previousLayerHeight: float = 0
    self.layerStart: int = 0
    self.layerEnd: int = 0
    self.lastFeature: Feature = None
    self.prevLayerLastFeature: Feature = None

    

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
  def __init__(self, startPos: Position, endPos: Position, boundingBox: BoundingBox = None):
    self.start: Position = startPos #original gcode start
    self.end: Position = endPos #original gcode end
    self.boundingBox: BoundingBox = boundingBox
  
  # return gcode with adjusted E and update PrintState.deltaE\
  # expects Movement E value to be the full original density value for the length of the movement
  def adjustE(self, ps: PrintState):
    gcode = MOVEMENT_G1
    newEndAbsoluteE = self.end.E
    if self.boundingBox:
      newEndRelativeE = (self.end.E - self.start.E) * self.boundingBox.density
      newEndAbsoluteE = self.start.E + newEndRelativeE
    movementDeltaE = newEndAbsoluteE - self.end.E #negative deltaE if newEndE is lower than original endE
    ps.deltaE += movementDeltaE #add delta E from this movement to the total delta E

    addComment = f"originalEInc={self.end.E-self.start.E:.5f} adjustedEInc={newEndAbsoluteE-self.start.E:.5f} density={self.boundingBox.density if self.boundingBox else 'N/A'}"

    gcode += f" X{self.end.X:.4f} Y{self.end.Y:.4f} E{self.end.E + ps.deltaE:.5f} {';' if (self.end.comment or self.boundingBox) else ''}{self.end.comment if self.end.comment else ''}{' => ' + addComment if self.boundingBox else ''}"
    return gcode