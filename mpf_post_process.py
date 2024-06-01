import re, os, typing, queue, time, datetime, math, enum, copy

from .printing_classes import *
from .constants import *

bbOrigin = Position()
bbOrigin.X, bbOrigin.Y = 0, -5
bbSize = Position()
bbSize.X, bbSize.Y = 25, 10
testBoundingBox = BoundingBox(origin = bbOrigin, size=bbSize)

# Update position state
def checkAndUpdatePosition(cl: str, pp: Position):
  # look for movement gcode and record last position before entering a feature
  movementMatch = re.match(MOVEMENT_G, cl)
  if movementMatch:
    m = 0
    travelMove = True
    while m+1 < len(movementMatch.groups()):
      if movementMatch.groups()[m] == None:
        break
      axis = str(movementMatch.groups()[m])
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
      else:
        print(f"Unknown axis {axis} {axisValue} for input {cl}")
      
    # If this move did not have extrusion, save the Feedrate as last travel speed
    if travelMove:
      pp.FTravel = pp.F

# Update states for movment POSITION and TOOL
def updatePrintState(ps: PrintState, cl: str, sw: bool):
    # look for movement gcode and record last position
    checkAndUpdatePosition(cl=cl, pp=ps.originalPosition)

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
  return (abs(p1.X - p2.X) ** 2 + abs(p1.Y - p2.Y) ** 2) **5

# check if movement is in bounding box and split movement by intersections
# return array of new movements or false if no intersection
def boundingBoxSplit(movement: Movement, boundingBox: BoundingBox):
  #intersect Left Right Top Bottom of bounding box
  intersectBBL, intersectBBR, intersectT, intersectBBB = False
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
  
  # check if movement starts in bounding box to know which side of single intersection found is in the box
  if intersect2 is False:
    if movement.start.X > boundingBox.origin.X and movement.start.X < boundingBox.origin.X + boundingBox.size.X and movement.start.Y > boundingBox.origin.Y and movement.start.Y < boundingBox.origin.Y + boundingBox.size.Y:
      newMovements.append(Movement(movement.start, intersect1, boundingBox))

  

  
  newMovements.append()
  


  
  return intersect1, intersect2


def process(inputFilepath: str, outputFilepath: str):
  startTime = time.monotonic()
  try:
    with open(inputFilepath, mode='r') as f, open(outputFilepath, mode='w') as out:
      # Persistent variables for the read loop
      
      # The current print state
      currentPrint: PrintState = PrintState()

      #Get total length of file
      f.seek(0, os.SEEK_END)
      lp = f.tell()
      f.seek(0, os.SEEK_SET)
      
      curFeatureIdx = -1
      curFeature = None

      # Current line buffer
      cl = True
      while cl:
        cl = f.readline()
        clsp = f.tell() - len(cl) - (len(lineEnding)-1) # read line start position
        cp = f.tell() # position is start of next line after read line. We define in lower scope function as needed for retention.

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
            currentPrint.features = []
          currentPrint.features.append(currentFeature)
        else:
          
          lastOriginalPosition = copy(currentPrint.originalPosition)

          # Update current print state variables
          updatePrintState(ps=currentPrint, cl=cl, sw=currentPrint.skipWrite)

          currentMovement = Movement(startpos=lastOriginalPosition, endpos = currentPrint.originalPosition)

          if lastOriginalPosition.E != currentPrint.originalPosition.E:
            #current movement is extrusion movement
            boundingBoxSplit(currentMovement, testBoundingBox)
          
          # start new infill map

          # check if (current feature) type for infill
          if len(currentPrint.features) > 0:

        #write out line
        out.write(cl)



          
          
      
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

        
          

            #print(f"Current feature toolchange is redundant. Skipping feature toolchange. Start skip at {f.tell()}")
            out.write("; MFM Original Feature Toolchange skipped\n")
            currentPrint.skipWrite = True
            #print(f"start feature toolchange skip ")
          
          if curFeature.wipeEnd and f.tell() == curFeature.wipeEnd.start and curFeature.featureType not in RETAIN_WIPE_END_FEATURE_TYPES:
            writeWithFilters(out, cl, loadedColors)
            #print(f"Skipping feature WIPE_END. Start skip at {f.tell()}")
            out.write(";WIPE_END placeholder for PrusaSlicer Gcode Viewer\n")
            out.write("; WIPE_END placeholder for BambuStudio Gcode Preview\n")
            out.write("; MFM Original WIPE_END skipped\n")
            currentPrint.skipWrite = True
            # Reference original pos as last wipe end pos for next layer
            currentPrint.featureWipeEndPrime = currentPrint.originalPosition
            

        # Write current line
        if currentPrint.skipWrite == False and currentPrint.skipWriteForCurrentLine == False: 
          #out.write(cl)
          writeWithFilters(out, cl, loadedColors)

        if currentPrint.skipWriteForCurrentLine == True:
          currentPrint.skipWrite = False
          currentPrint.skipWriteForCurrentLine = False

      out.write(f'Post Processed with {configuration[CONFIG_APP_NAME]} {configuration[CONFIG_APP_VERSION]}')

      if statusQueue:
        item = StatusQueueItem()
        item.statusLeft = f"Current Layer {currentPrint.height}"
        item.statusRight = f"Completed in {str(datetime.timedelta(seconds=time.monotonic()-startTime))}s"
        item.progress = 99.99
        statusQueue.put(item=item)
  except PermissionError as e:
    if statusQueue:
      item = StatusQueueItem()
      item.statusRight = f"Failed to open {e}"
      statusQueue.put(item=item)