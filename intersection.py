import re, os, typing, queue, time, datetime, math, enum, copy

from printing_classes import *
from constants import *
from line_ending import *


#https://stackoverflow.com/a/72474223/761902
def line_intersection(a, b, c, d):
    try:
      t = ((a[0] - c[0]) * (c[1] - d[1]) - (a[1] - c[1]) * (c[0] - d[0])) / ((a[0] - b[0]) * (c[1] - d[1]) - (a[1] - b[1]) * (c[0] - d[0]))
      u = ((a[0] - c[0]) * (a[1] - b[1]) - (a[1] - c[1]) * (a[0] - b[0])) / ((a[0] - b[0]) * (c[1] - d[1]) - (a[1] - b[1]) * (c[0] - d[0]))
    except:
      # divide by zero means lines are on top of each other
      return False

    # check if line actually intersect
    if (0 <= t and t <= 1 and 0 <= u and u <= 1):
        return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
    else: 
        return False
    
def point_distance(p1: Position, p2: Position):
  return (abs(p1.X - p2.X) ** 2 + abs(p1.Y - p2.Y) ** 2) **0.5

#only checks XY
def point_in_box(p1: Position, boundingBox: BoundingBox):
  if p1.X > boundingBox.origin.X and p1.X < boundingBox.origin.X + boundingBox.size.X and p1.Y > boundingBox.origin.Y and p1.Y < boundingBox.origin.Y + boundingBox.size.Y: 
    return True
  return False

# check if movement is in bounding box and split movement by intersections
# return array of new movements or false if no intersection
def boundingBoxSplit(movement: Movement, boundingBox: BoundingBox):
  currentBoundingBox = copy.copy(boundingBox) #only use this for intersection checking
  currentBoundingBox.origin = boundingBox.currentBoundingBoxOriginAtHeight(movement.end.Z)
  currentBoundingBox.size = boundingBox.currentBoundingBoxSizeAtHeight(movement.end.Z)

  newMovements: list[Movement] = []

  #intersect Left Right Top Bottom of bounding box
  intersectBBL, intersectBBR, intersectBBT, intersectBBB = False, False, False, False

  #currently this only checks if the movement end is in the Z range of the boundingbox
  if movement.end.Z >= currentBoundingBox.origin.Z and movement.end.Z <= currentBoundingBox.origin.Z + currentBoundingBox.size.Z:

    #check if entire movement start and end are in bounding box
    if point_in_box(movement.start, currentBoundingBox) and point_in_box(movement.end, currentBoundingBox):
      movementWithBoundingBox = copy.copy(movement)
      movementWithBoundingBox.boundingBox = currentBoundingBox
      newMovements.append(movementWithBoundingBox)
      return newMovements

    intersectBBL = line_intersection([movement.start.X,movement.start.Y], [movement.end.X,movement.end.Y], [currentBoundingBox.origin.X, currentBoundingBox.origin.Y], [currentBoundingBox.origin.X, currentBoundingBox.origin.Y + currentBoundingBox.size.Y])
    intersectBBR = line_intersection([movement.start.X,movement.start.Y], [movement.end.X,movement.end.Y], [currentBoundingBox.origin.X + currentBoundingBox.size.X, currentBoundingBox.origin.Y], [currentBoundingBox.origin.X + currentBoundingBox.size.X, currentBoundingBox.origin.Y + currentBoundingBox.size.Y])
    intersectBBT = line_intersection([movement.start.X,movement.start.Y], [movement.end.X,movement.end.Y], [currentBoundingBox.origin.X, currentBoundingBox.origin.Y + currentBoundingBox.size.Y], [currentBoundingBox.origin.X + currentBoundingBox.size.X, currentBoundingBox.origin.Y + currentBoundingBox.size.Y])
    intersectBBB = line_intersection([movement.start.X,movement.start.Y], [movement.end.X,movement.end.Y], [currentBoundingBox.origin.X, currentBoundingBox.origin.Y], [currentBoundingBox.origin.X + currentBoundingBox.size.X, currentBoundingBox.origin.Y])

  intersect1: Position|False = False
  intersect2: Position|False = False
  intersectChecks = [intersectBBL, intersectBBR, intersectBBT, intersectBBB]
  for i in intersectChecks:
    if i != False:
      iPosition = Position()
      iPosition.X = i[0]
      iPosition.Y = i[1]
      if intersect1:
        if intersect2:
          print(f'three intersections found {intersect1} {intersect2} {i}')
        intersect2 = iPosition
      else:
        intersect1 = iPosition

  # Return False if no intersections
  if intersect1 is False:
    return False

  # determine which intersection is first on the movement line
  if intersect2 and point_distance(intersect2, movement.start) < point_distance(intersect1, movement.start):
    intersect1, intersect2 = intersect2, intersect1
  
  #set Z position for intersections (since we don't check for Z intersect point)
  intersect1.Z = movement.end.Z
  if intersect2:
    intersect2.Z = movement.end.Z

  originalStartEndEDistance = movement.end.E-movement.start.E
  originalStartEndPointDistance = point_distance(movement.start, movement.end)

  # check if movement starts in bounding box to know which side of single intersection found is in the box
  intersect1.E = movement.start.E # absolute E position of the movement before this
  intersect1.E += originalStartEndEDistance * point_distance(movement.start, intersect1)/originalStartEndPointDistance # add the relative E distance

  if intersect2 is False:
    if point_in_box(movement.start, boundingBox): # start is in box
      newMovements.append(Movement(startPos=movement.start, endPos=intersect1, boundingBox=boundingBox, feature=movement.feature))
      newMovements.append(Movement(startPos=intersect1, endPos=movement.end, boundingBox=None, feature=movement.feature))
    else:
      newMovements.append(Movement(startPos=movement.start, endPos=intersect1, boundingBox=None, feature=movement.feature))
      newMovements.append(Movement(startPos=intersect1, endPos=movement.end, boundingBox=boundingBox, feature=movement.feature))
  else:
    intersect2.E = intersect1.E # absolute E position of the movement before this
    intersect2.E += originalStartEndEDistance * point_distance(intersect1, intersect2)/originalStartEndPointDistance # add the relative E distance

    newMovements.append(Movement(startPos=movement.start, endPos=intersect1, boundingBox=None, feature=movement.feature))
    newMovements.append(Movement(startPos=intersect1, endPos=intersect2, boundingBox=boundingBox, feature=movement.feature))
    newMovements.append(Movement(startPos=intersect2, endPos=movement.end, boundingBox=None, feature=movement.feature))
  
  return newMovements