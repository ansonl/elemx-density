import re, os, typing, queue, time, datetime, math, enum, copy

from printing_classes import *
from constants import *
from line_ending import *

bbOrigin = Position()
bbOrigin.X, bbOrigin.Y, bbOrigin.Z = 0, -5, 0
bbSize = Position()
bbSize.X, bbSize.Y, bbSize.Z = 25, 10, 8
testBoundingBox = BoundingBox(origin = bbOrigin, size=bbSize, density=0.5)

# Update position state
def checkAndUpdatePosition(cl: str, pp: Position):
  #clear last comment
  pp.comment = None

  # look for movement gcode and record last position before entering a feature
  movementMatch = re.match(MOVEMENT_G, cl)
  if movementMatch:
    m = 0
    travelMove = True
    while m+1 < len(movementMatch.groups()):
      if movementMatch.groups()[m] == None:
        m += 2
        continue
      axis = str(movementMatch.groups()[m])
      if axis == ';':
        axisValue = movementMatch.groups()[m+1]
      else:
        axisValue = float(movementMatch.groups()[m+1])
      m += 2
      if axis == 'X':
        pp.X = axisValue
      elif axis == 'Y':
        pp.Y = axisValue
      elif axis == 'Z':
        pp.Z = axisValue
      elif axis == 'E':
        pp.E = axisValue
        travelMove = False
      elif axis == 'F':
        pp.F = axisValue
      elif axis == ';':
        pp.comment = axisValue
      else:
        print(f"Unknown axis {axis} {axisValue} for input {cl}")
      
    # If this move did not have extrusion, save the Feedrate as last travel speed
    if travelMove:
      pp.FTravel = pp.F

# Update states for movment POSITION and TOOL
def updatePrintState(ps: PrintState, cl: str, sw: bool):
    # look for movement gcode and record last position
    checkAndUpdatePosition(cl=cl, pp=ps.originalPosition)

    ps.layerHeight = ps.originalPosition.Z

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

# check if movement is in bounding box and split movement by intersections
# return array of new movements or false if no intersection
def boundingBoxSplit(movement: Movement, boundingBox: BoundingBox):
  #intersect Left Right Top Bottom of bounding box
  intersectBBL, intersectBBR, intersectBBT, intersectBBB = False, False, False, False

  #currently this only checks if the movement end is in the Z range of the boundingbox
  if movement.end.Z >= boundingBox.origin.Z and movement.end.Z <= boundingBox.origin.Z + boundingBox.size.Z:
    intersectBBL = line_intersection([movement.start.X,movement.start.Y], [movement.end.X,movement.end.Y], [boundingBox.origin.X, boundingBox.origin.Y], [boundingBox.origin.X, boundingBox.origin.Y + boundingBox.size.Y])
    intersectBBR = line_intersection([movement.start.X,movement.start.Y], [movement.end.X,movement.end.Y], [boundingBox.origin.X + boundingBox.size.X, boundingBox.origin.Y], [boundingBox.origin.X + boundingBox.size.X, boundingBox.origin.Y + boundingBox.size.Y])
    intersectBBT = line_intersection([movement.start.X,movement.start.Y], [movement.end.X,movement.end.Y], [boundingBox.origin.X, boundingBox.origin.Y + boundingBox.size.Y], [boundingBox.origin.X + boundingBox.size.X, boundingBox.origin.Y + boundingBox.size.Y])
    intersectBBB = line_intersection([movement.start.X,movement.start.Y], [movement.end.X,movement.end.Y], [boundingBox.origin.X, boundingBox.origin.Y], [boundingBox.origin.X + boundingBox.size.X, boundingBox.origin.Y])

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
  
  newMovements: list[Movement] = []

  # determine which intersection is first on the movement line
  if intersect2 and point_distance(intersect2, movement.start) < point_distance(intersect1, movement.start):
    intersect1, intersect2 = intersect2, intersect1
  
  originalStartEndEDistance = movement.end.E-movement.start.E
  originalStartEndPointDistance = point_distance(movement.start, movement.end)

  # check if movement starts in bounding box to know which side of single intersection found is in the box
  intersect1.E = movement.start.E # absolute E position of the movement before this
  intersect1.E += originalStartEndEDistance * point_distance(movement.start, intersect1)/originalStartEndPointDistance # add the relative E distance

  if intersect2 is False:
    if movement.start.X > boundingBox.origin.X and movement.start.X < boundingBox.origin.X + boundingBox.size.X and movement.start.Y > boundingBox.origin.Y and movement.start.Y < boundingBox.origin.Y + boundingBox.size.Y: # start is in box
      newMovements.append(Movement(movement.start, intersect1, boundingBox))
      newMovements.append(Movement(intersect1, movement.end, None))
    else:
      newMovements.append(Movement(movement.start, intersect1, None))
      newMovements.append(Movement(intersect1, movement.end, boundingBox))
  else:
    intersect2.E = intersect1.E # absolute E position of the movement before this
    intersect2.E += originalStartEndEDistance * point_distance(intersect1, intersect2)/originalStartEndPointDistance # add the relative E distance

    newMovements.append(Movement(movement.start, intersect1, None))
    newMovements.append(Movement(intersect1, intersect2, boundingBox))
    newMovements.append(Movement(intersect2, movement.end, None))
  
  return newMovements

def process(inputFilepath: str, outputFilepath: str):
  lineEndingFlavor = determineLineEndingTypeInFile(inputFilepath)
  print(f"detected line ending {repr(lineEndingFlavor)}")
  if lineEndingFlavor == LineEnding.UNKNOWN:
    lineEndingFlavor = LineEnding.UNIX
    print('default to unix line ending')
  lineEnding = lineEndingFlavor.value

  try:
    with open(inputFilepath, mode='r') as f, open(outputFilepath, mode='w') as out:
      # Persistent variables for the read loop
      
      # The current print state
      currentPrint: PrintState = PrintState()

      #Get total length of file
      f.seek(0, os.SEEK_END)
      #lp = f.tell()
      f.seek(0, os.SEEK_SET)
      

      # Current line buffer
      cl = True
      while cl:
        cl = f.readline()
        clsp = f.tell() - len(cl) - (len(lineEnding)-1) # read line start position
        #cp = f.tell() # position is start of next line after read line. We define in lower scope function as needed for retention.

        if f.tell() == 30440:
          0==0

        # check for feature comment
        featureMatch = re.match(FEATURE_TYPE, cl)
        if featureMatch:
          if len(currentPrint.features) > 0:
            currentPrint.features[-1].end = clsp

          currentFeature = Feature()
          currentFeature.featureType = featureMatch.groups()[0]
          currentFeature.start = clsp
          
          if currentFeature.featureType == LAYER_CHANGE:
            print(f"starting new layer")
            currentPrint.features = []
          currentPrint.features.append(currentFeature)

          out.write(cl)
        else:
          #save copy of last original gcode position before reading current line gcode position
          lastOriginalPosition: Position = copy.copy(currentPrint.originalPosition)

          # Update current print state variables
          updatePrintState(ps=currentPrint, cl=cl, sw=currentPrint.skipWrite)

          currentMovement = Movement(startPos=lastOriginalPosition, endPos = currentPrint.originalPosition, boundingBox=None)

          currentFeature = None
          if len(currentPrint.features) > 0:
            currentFeature = currentPrint.features[-1]

          if lastOriginalPosition.E != currentPrint.originalPosition.E: #current movement is extrusion movement
            newMovements = False
            if currentFeature and currentFeature.featureType == INFILL: #if movement is infill, check for boundingbox intersect
              newMovements = boundingBoxSplit(currentMovement, testBoundingBox)

            # write out movements
            if newMovements:
              for nm in newMovements:
                movementGcode = nm.adjustE(currentPrint)
                out.write(f"{movementGcode}\n")
                
            else:
              movementGcode = currentMovement.adjustE(currentPrint)
              out.write(f"{movementGcode}\n")

          else:
            out.write(cl)
          
          print(f.tell())
          
          # start new infill map

      out.write(f';Post Processed with variable density\n')

  except PermissionError as e:
    print(f"Failed to open {e}")

      
        # elemx infill
        # check for layer marker
        # check for feature: wall/infill/other
        # note absolute E position

        # if infill, check for intersection with density boundary lines
          # if intersect, split infill line at intersection point
          # generate 2 new infill lines on each end of intersection point
          # recursively check for intersection with other density boundary lines and split lines
          # call write command line and do E adjustment there

        #write command line
        # if infill, modify E distance from last E distance based on percentage, note difference between new and old (longer) E position, add E difference to accumulated E diff counter.
          # write infill with new E = (infill E - previous cmd E) * percentage + previous cmd E - accumulated E diff (if saved as positive)
        # if not infill
          # cmd with new E = cmd E - accumulated E diff (if saved as positive)


#process(inputFilepath='long-rect.mpf', outputFilepath='long-rect-output.mpf')
process(inputFilepath='long-rect-verbose.mpf', outputFilepath='long-rect-verbose-output.mpf')