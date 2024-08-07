import math, copy

from printing_classes import *
from constants import *

def fillBBDropletRasterForDroplet(bb: BoundingBox, droplet: Movement):
  bb.dropletRaster[1][round((droplet.end.X-bb.origin.X)/(DROPLET_WIDTH*bb.dropletOverlap))][round((droplet.end.Y-bb.origin.Y)/(DROPLET_WIDTH*bb.dropletOverlap))] = 1

def getBBDropletRasterForPosition(bb: BoundingBox, pos: Position, idx: int):
  return bb.dropletRaster[idx][round((pos.X-bb.origin.X)/(DROPLET_WIDTH*bb.dropletOverlap))][round((pos.Y-bb.origin.Y)/(DROPLET_WIDTH*bb.dropletOverlap))]

def get3x3BBDropletRasterForPosition(bb: BoundingBox, pos: Position, idx: int):
  rasterX = round((pos.X-bb.origin.X)/(DROPLET_WIDTH*bb.dropletOverlap))
  rasterY = round((pos.Y-bb.origin.Y)/(DROPLET_WIDTH*bb.dropletOverlap))

  for i in range(rasterX-1, rasterX+2):
    if i >= 0 and i < len(bb.dropletRaster[idx]):
      for j in range(rasterY-1, rasterY+2):
        if j >= 0 and j < len(bb.dropletRaster[idx][i]):
          if bb.dropletRaster[idx][i][j]:
            return bb.dropletRaster[idx][i][j]

  return 0


# Reduce # dots to % density. Evenly space droplets inclusive of start and end segments.
def reduceDropletsToDensity(droplets: list[Movement], density: float):
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

# split movement into individual droplets
def splitMovementToDroplets(m: Movement):
  x_delta = m.end.X-m.start.X
  y_delta = m.end.Y-m.start.Y
  e_delta = m.end.E-m.start.E

  cartesianDistance = math.sqrt(x_delta**2 + y_delta**2)
  dropletCount = cartesianDistance / (DROPLET_WIDTH * m.boundingBox.dropletOverlap)

  segment_x_delta = x_delta / dropletCount
  segment_y_delta = y_delta / dropletCount
  segment_e_delta = e_delta / dropletCount

  m.dropletE = segment_e_delta

  newDroplets: list[Movement] = []

  for i in range(0, math.ceil(dropletCount)):
    start = copy.copy(m.start)
    start.E += segment_e_delta * i
    start.X += segment_x_delta * (i+0.5)
    start.Y += segment_y_delta * (i+0.5)

    end = copy.copy(start)
    end.E += segment_e_delta
    droplet = Movement(startPos=start, endPos=end, boundingBox=m.boundingBox)
    newDroplets.append(droplet)
  
  return newDroplets

def findSupportedLocations(m: Movement) -> list[Position]:
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

  supportedLocations: list[Position] = []

  for i in range(0, math.ceil(interpolationSteps)):
    checkPosition = copy.copy(m.start)
    checkPosition.X += interpolate_x_delta * i
    checkPosition.Y += interpolate_y_delta * i
    checkPosition.E = 0
    if get3x3BBDropletRasterForPosition(bb=m.boundingBox, pos=checkPosition, idx=0) > 0:
      supportedLocations.append(checkPosition)

    checkPositionLeft = copy.copy(checkPosition)
    checkPositionLeft.X += -1*interpolate_y_delta
    checkPositionLeft.Y += interpolate_x_delta
    if get3x3BBDropletRasterForPosition(bb=m.boundingBox, pos=checkPositionLeft, idx=0) > 0:
      supportedLocations.append(checkPositionLeft)

    checkPositionRight = copy.copy(checkPosition)
    checkPositionRight.X += interpolate_y_delta
    checkPositionRight.Y += -1* interpolate_x_delta
    if get3x3BBDropletRasterForPosition(bb=m.boundingBox, pos=checkPositionRight, idx=0) > 0:
      supportedLocations.append(checkPositionRight)

  return supportedLocations