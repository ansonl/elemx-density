import math, copy

from printing_classes import *
from constants import *



def getBBDropletRasterIndicesForPosition(bb: BoundingBox, pos: Position):
  return (round((pos.X-bb.origin.X)/(DROPLET_WIDTH*bb.dropletRasterResolution)), round((pos.Y-bb.origin.Y)/(DROPLET_WIDTH*bb.dropletRasterResolution)))
  #return (math.ceil((1/bb.dropletOverlap)/2) + round((pos.X-bb.origin.X)/(DROPLET_WIDTH*bb.dropletOverlap)), math.ceil((1/bb.dropletOverlap)/2) + round((pos.Y-bb.origin.Y)/(DROPLET_WIDTH*bb.dropletOverlap)))

def fillBBDropletRasterForDroplet(bb: BoundingBox, droplet: Movement):
  indices = getBBDropletRasterIndicesForPosition(bb=bb, pos=droplet.end)
  bb.dropletRaster[1][indices[0]][indices[1]] = 1

def getBBDropletRasterForPosition(bb: BoundingBox, pos: Position, idx: int):
  indices = getBBDropletRasterIndicesForPosition(bb=bb, pos=pos)
  return bb.dropletRaster[idx][indices[0]][indices[1]]

def getNxNBBDropletRasterForPosition(bb: BoundingBox, pos: Position, idx: int, n: int, excludeCornerDropletRadius: int):
  indices = getBBDropletRasterIndicesForPosition(bb=bb, pos=pos)
  rasterX = indices[0]
  rasterY = indices[1]
  sideDist = int((n-1)/2)

  if excludeCornerDropletRadius > sideDist:
    print(f'excludeCornerDropletRadius {excludeCornerDropletRadius} is greater than sideDistance {sideDist}\n')
    0==1 #abort

  for i in range(rasterX-sideDist, rasterX+sideDist+1):
    if i >= 0 and i < len(bb.dropletRaster[idx]):
      for j in range(rasterY-sideDist+max(0, excludeCornerDropletRadius-(sideDist-abs(rasterX-i))), rasterY+sideDist+1-max(0, excludeCornerDropletRadius-(sideDist-abs(rasterX-i)))):
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

  #density = 0.03

  numDroplets = len(droplets)
  nthDroplet = 1/density 
  steps = round(numDroplets/nthDroplet) - 1 #number of steps after the 0th (first) step

  reducedDroplets: list[Movement] = []

  if steps > 1:
    inset45DegreeDropletCount = (MINIMUM_INSET_DROPLET_WIDTH+INSET_DROPLET_WIDTH)*2**0.5
    for i in range(0, steps + 1):
      # Check if scaled droplets is enough drops if we avoid dropping in inset assuming bounding box is exactly where infill bounds are. Assume 45 degree infill angle on average.
      #reducedDroplets.append(droplets[round((i)*(numDroplets-1)/steps)]) #drop evenly spaced
      if numDroplets <= steps+1: #drop all drops
        reducedDroplets.extend(droplets)
        break
      elif numDroplets - math.floor(inset45DegreeDropletCount)*2 < steps+1:
        insetDropletCountOnEnds = math.floor((numDroplets - (steps+1)) / 2)
        reducedDroplets.extend(droplets[insetDropletCountOnEnds:insetDropletCountOnEnds+steps+1]) #drop center droplets
      else: #drop avoiding inset distance on either end
        reducedDroplets.append(droplets[math.floor(inset45DegreeDropletCount) + round((i)*(numDroplets-1-inset45DegreeDropletCount*2)/steps)]) #drop evenly spaced

  else: # Special case if total output droplet count is 1 or 2
    if steps > 0: # output 2 droplets evenly spaced exclusive of endpoints
      reducedDroplets.append(droplets[math.floor(numDroplets/3) if numDroplets/3 > 1.5 else math.floor(numDroplets/3)-1])
      reducedDroplets.append(droplets[math.floor(numDroplets/3*2)])
    else: # output 1 droplet (center)
      reducedDroplets.append(droplets[round(numDroplets/2)])

  return reducedDroplets

def splitMovementToDroplets(m: Movement, singleDropletWidthResolution: bool) -> list[Movement]:
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
  dropletCount = cartesianDistance / (DROPLET_WIDTH * 1 if singleDropletWidthResolution else DROPLET_RASTER_RESOLUTION_PERC)

  segment_x_delta = x_delta / dropletCount
  segment_y_delta = y_delta / dropletCount
  segment_e_delta = (e_delta / dropletCount) * (1 if singleDropletWidthResolution else 1/DROPLET_RASTER_RESOLUTION_PERC)

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

  xyResolution = DROPLET_WIDTH*m.boundingBox.dropletRasterResolution

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

  insetPercentage = 1 - m.boundingBox.percentThroughRampUpDensityZone(m.end.Z)

  for i in range(0, math.ceil(interpolationSteps)):
    checkPosition = copy.copy(m.start)
    checkPosition.X += interpolate_x_delta * i
    checkPosition.Y += interpolate_y_delta * i
    checkPosition.E = 0

    # Check if position is too close to edge of bounding box
    rasterIndices = getBBDropletRasterIndicesForPosition(bb=m.boundingBox, 
    pos=checkPosition)
    #rasterIndices = tuple(rasterIndices[ri]-math.ceil((1/m.boundingBox.dropletOverlap)/2) for ri in range(len(rasterIndices))) #subtract raster indices by padded amount on raster edge to get 0 based location relative to bounding box origin

    insetDistIndices = math.floor(MINIMUM_BOUNDARY_BOX_INSET/xyResolution + BOUNDARY_BOX_INSET/xyResolution*insetPercentage)

    if rasterIndices[0] < insetDistIndices or rasterIndices[0] > len(m.boundingBox.dropletRaster[0]) - insetDistIndices:
      continue 
    if rasterIndices[1] < insetDistIndices or rasterIndices[1] > len(m.boundingBox.dropletRaster[0][0]) - insetDistIndices:
      continue 

    if getNxNBBDropletRasterForPosition(bb=m.boundingBox, pos=checkPosition, idx=0, n=DROPLET_RASTER_SUPPORTED_SEARCH_KERNEL_SIZE, excludeCornerDropletRadius=DROPLET_RASTER_SUPPORTED_SEARCH_CORNER_RADIUS) > 0:
      supportedLocations.append((i,checkPosition))

    checkPositionLeft = copy.copy(checkPosition)
    checkPositionLeft.X += -1*interpolate_y_delta
    checkPositionLeft.Y += interpolate_x_delta
    if getNxNBBDropletRasterForPosition(bb=m.boundingBox, pos=checkPositionLeft, idx=0, n=DROPLET_RASTER_SUPPORTED_SEARCH_KERNEL_SIZE, excludeCornerDropletRadius=DROPLET_RASTER_SUPPORTED_SEARCH_CORNER_RADIUS) > 0:
      supportedLocations.append((i,checkPositionLeft))

    checkPositionRight = copy.copy(checkPosition)
    checkPositionRight.X += interpolate_y_delta
    checkPositionRight.Y += -1* interpolate_x_delta
    if getNxNBBDropletRasterForPosition(bb=m.boundingBox, pos=checkPositionRight, idx=0, n=DROPLET_RASTER_SUPPORTED_SEARCH_KERNEL_SIZE, excludeCornerDropletRadius=DROPLET_RASTER_SUPPORTED_SEARCH_CORNER_RADIUS) > 0:
      supportedLocations.append((i,checkPositionRight))

  return supportedLocations