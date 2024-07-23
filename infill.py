import math, copy

from printing_classes import *
from constants import *

def fillBBDropletRasterForDroplet(bb: BoundingBox, droplet: Movement):
  bb.dropletRaster[1][round((droplet.end.X-bb.origin.X)/(DROPLET_WIDTH*bb.dropletOverlap))][round((droplet.end.Y-bb.origin.Y)/(DROPLET_WIDTH*bb.dropletOverlap))] = 1

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
  dropletCount = cartesianDistance / (DROPLET_WIDTH * DROPLET_OVERLAP_PERC)

  segment_x_delta = x_delta / dropletCount
  segment_y_delta = y_delta / dropletCount
  segment_e_delta = e_delta / dropletCount

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
