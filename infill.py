import math, copy

from printing_classes import *
from constants import *

def fillBBDropletRasterForDroplet(bb: BoundingBox, droplet: Movement):
  bb.dropletRaster[1][round((droplet.end.X-bb.origin.X)/(DROPLET_WIDTH*bb.dropletOverlap))][round((droplet.end.Y-bb.origin.Y)/(DROPLET_WIDTH*bb.dropletOverlap))] = 1

def getBBDropletRasterIndicesForPosition(bb: BoundingBox, pos: Position):
  return (round((pos.X-bb.origin.X)/(DROPLET_WIDTH*bb.dropletOverlap)), round((pos.Y-bb.origin.Y)/(DROPLET_WIDTH*bb.dropletOverlap)))

def getBBDropletRasterForPosition(bb: BoundingBox, pos: Position, idx: int):
  indices = getBBDropletRasterIndicesForPosition(bb=bb, pos=pos)
  return bb.dropletRaster[idx][indices[0]][indices[1]]

def get3x3BBDropletRasterForPosition(bb: BoundingBox, pos: Position, idx: int):
  indices = getBBDropletRasterIndicesForPosition(bb=bb, pos=pos)
  rasterX = indices[0]
  rasterY = indices[1]

  for i in range(rasterX-1, rasterX+2):
    if i >= 0 and i < len(bb.dropletRaster[idx]):
      for j in range(rasterY-1, rasterY+2):
        if j >= 0 and j < len(bb.dropletRaster[idx][i]):
          if bb.dropletRaster[idx][i][j]:
            return bb.dropletRaster[idx][i][j]

  return 0

def reduceDropletsToDensity(droplets: list[Movement], density: float) -> list[Movement]:
  """
  Reduce # dots to % density. Evenly space droplets inclusive of start and end segments.

  :param droplets: The chain of droplets to reduce in density.
  :type droplets: list[Movement]
  :param density: Target density.
  :type density: float
  :return: List of droplets at the target density.
  :rtype: list[Movement]
  """  
  numDroplets = len(droplets)

  nthDroplet = 1/density 
  steps = round(numDroplets/nthDroplet) - 1 #number of steps after the 0th (first) step

  reducedDroplets: list[Movement] = []

  if steps > 1:
    for i in range(0, steps + 1):
      reducedDroplets.append(droplets[round((i)*(numDroplets-1)/steps)])
  else: # Special case if total output droplet count is 1 or 2
    if steps > 0: # output 2 droplets
      reducedDroplets.append(droplets[math.floor(numDroplets/3) if numDroplets/3 > 1.5 else math.floor(numDroplets/3)-1])
      reducedDroplets.append(droplets[math.floor(numDroplets/3*2)])
    else: # output 1 droplet (center)
      reducedDroplets.append(droplets[round(numDroplets/2)])

  return reducedDroplets

def splitMovementToDroplets(m: Movement) -> list[Movement]:
  """
  Split movement into individual droplets

  :param m: The movement to split into droplets
  :type m: Movement
  :return: List of droplets for the movement
  :rtype: list[Movement]
  """  

  x_delta = m.end.X-m.start.X
  y_delta = m.end.Y-m.start.Y
  e_delta = m.end.E-m.start.E

  cartesianDistance = math.sqrt(x_delta**2 + y_delta**2)
  dropletCount = cartesianDistance / (DROPLET_WIDTH)

  segment_x_delta = x_delta / dropletCount
  segment_y_delta = y_delta / dropletCount
  segment_e_delta = e_delta / dropletCount

  m.dropletE = segment_e_delta * DROPLET_EXTRUSION_MULTIPLIER

  newDroplets: list[Movement] = []

  for i in range(0, math.ceil(dropletCount)):
    start = copy.copy(m.start)
    start.E += segment_e_delta * i
    start.X += segment_x_delta * (i+0.5)
    start.Y += segment_y_delta * (i+0.5)

    end = copy.copy(start)
    end.E += segment_e_delta * DROPLET_EXTRUSION_MULTIPLIER
    droplet = Movement(startPos=start, endPos=end, boundingBox=m.boundingBox)
    newDroplets.append(droplet)
  
  return newDroplets

def findSupportedLocations(m: Movement) -> list[(int,Position)]:
  """
  Find support locations along a Movement. Movement is interpolated at a resolution. Supported locations are checked at each interpolated point and the 2 points perpendicular (negative reciprocal slope * resolution) the movement slope on each side of the movement line from the interpolated point.

  :param m: The movement
  :return: List of supported locations in form of original interpolated index and Position.
  :rtype: list[(int,Position)]
  """

  x_delta = m.end.X-m.start.X
  y_delta = m.end.Y-m.start.Y
  cartesianDistance = math.sqrt(x_delta**2 + y_delta**2)

  xyResolution = DROPLET_WIDTH*m.boundingBox.dropletOverlap

  interpolate_x_delta = 0
  interpolate_y_delta = 0

  # normalize x/y delta for interpolation by raster resolution
  if y_delta > x_delta:
    interpolate_x_delta = xyResolution/y_delta * x_delta
    interpolate_y_delta = xyResolution
  else:
    interpolate_y_delta = xyResolution/x_delta * y_delta
    interpolate_x_delta = xyResolution

  interpolationSteps = x_delta/interpolate_x_delta

  supportedLocations: list[(int,Position)] = []

  for i in range(0, math.ceil(interpolationSteps)):
    checkPosition = copy.copy(m.start)
    checkPosition.X += interpolate_x_delta * i
    checkPosition.Y += interpolate_y_delta * i
    checkPosition.E = 0

    # Check if position is too close to edge of bounding box
    rasterIndices = getBBDropletRasterIndicesForPosition(bb=m.boundingBox, pos=checkPosition)
    if rasterIndices[0] < math.floor(BOUNDARY_BOX_INSET/(DROPLET_WIDTH*m.boundingBox.dropletOverlap)) or rasterIndices[0] > len(m.boundingBox.dropletRaster[0]) - math.floor(BOUNDARY_BOX_INSET/(DROPLET_WIDTH*m.boundingBox.dropletOverlap)):
      continue 
    if rasterIndices[1] < math.floor(BOUNDARY_BOX_INSET/(DROPLET_WIDTH*m.boundingBox.dropletOverlap)) or rasterIndices[1] > len(m.boundingBox.dropletRaster[0][0]) - math.floor(BOUNDARY_BOX_INSET/(DROPLET_WIDTH*m.boundingBox.dropletOverlap)):
      continue 

    if get3x3BBDropletRasterForPosition(bb=m.boundingBox, pos=checkPosition, idx=0) > 0:
      supportedLocations.append((i,checkPosition))

    checkPositionLeft = copy.copy(checkPosition)
    checkPositionLeft.X += -1*interpolate_y_delta
    checkPositionLeft.Y += interpolate_x_delta
    if get3x3BBDropletRasterForPosition(bb=m.boundingBox, pos=checkPositionLeft, idx=0) > 0:
      supportedLocations.append((i,checkPositionLeft))

    checkPositionRight = copy.copy(checkPosition)
    checkPositionRight.X += interpolate_y_delta
    checkPositionRight.Y += -1* interpolate_x_delta
    if get3x3BBDropletRasterForPosition(bb=m.boundingBox, pos=checkPositionRight, idx=0) > 0:
      supportedLocations.append((i,checkPositionRight))

  return supportedLocations