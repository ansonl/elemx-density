import re, os, typing, queue, time, datetime, math, enum, copy

from printing_classes import *
from constants import *
from line_ending import *
from intersection import *
from infill import *

bbOrigin = Position()
bbOrigin.X, bbOrigin.Y, bbOrigin.Z = -10, -25, 0.5
bbSize = Position()
bbSize.X, bbSize.Y, bbSize.Z = 40, 50, 8
testBoundingBox = BoundingBox(origin = bbOrigin, size=bbSize, density=0.1)

# infill first pass planning
def getInfillRequirements(imq: list[Movement], ps: PrintState):
  for m in imq:
    if m.boundingBox:
      m.dropletMovements = splitMovementToDroplets(m)

      ps.infillModifiedDropletsOriginal += len(m.dropletMovements)
      ps.infillModifiedDropletsNeededForDensity += len(reduceDropletsToDensity(droplets=m.dropletMovements, density=m.boundingBox.density))

# infill 
def placeInfill(imq: list[Movement], ps: PrintState):
  for m in imq:
    if m.boundingBox: # check if movement needs to be modified because it is in bounding box
      if m.boundingBox.dropletRaster == None:
        m.boundingBox.initializeDropletRaster()

      if m.boundingBox.dropletRaster[0] == None: #initial layer, reduce and space out drops
        reducedDroplets = reduceDropletsToDensity(droplets=m.dropletMovements, density=m.boundingBox.density)
        ps.infillModifiedDropletsNeededForDensity -= len(reducedDroplets)
        m.dropletMovements = reducedDroplets
        for d in reducedDroplets:
          fillBBDropletRasterForDroplet(bb=m.boundingBox, droplet=d)
      else: # not initial layer, place drops on supported area
        ##TODO: implement
        reducedDroplets = reduceDropletsToDensity(droplets=m.dropletMovements, density=m.boundingBox.density)
        ps.infillModifiedDropletsNeededForDensity -= len(reducedDroplets)
        m.dropletMovements = reducedDroplets
        for d in reducedDroplets:
          fillBBDropletRasterForDroplet(bb=m.boundingBox, droplet=d)

# infill
def processInfillMovementQueue(imq: list[Movement], ps: PrintState):
  ps.infillModifiedDropletsOriginal = 0
  ps.infillModifiedDropletsNeededForDensity = 0

  getInfillRequirements(imq, ps)
  print(f"infill on layer height {ps.layerHeight} requires {ps.infillModifiedDropletsNeededForDensity}/{ps.infillModifiedDropletsOriginal} droplets for density")
  print(f"placing infill")
  placeInfill(imq=imq, ps=ps)
  print(f"infill on layer height {ps.layerHeight} placed and still requires {ps.infillModifiedDropletsNeededForDensity} droplets")

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

        if f.tell() == 91483:
          0==0

        # check for feature comment
        featureMatch = re.match(FEATURE_TYPE, cl)
        m1Match = re.match(MACHINE_M1, cl)
        if featureMatch:
          if len(currentPrint.features) > 0:
            currentPrint.features[-1].end = clsp

          currentFeature = Feature()
          currentFeature.featureType = featureMatch.groups()[0]
          currentFeature.start = clsp
          
          if currentFeature.featureType == INFILL:
            currentPrint.infillMovementQueue = []
            currentPrint.infillMovementQueueOriginalStartPosition = copy.copy(currentPrint.originalPosition) #save original position at queue start
          elif currentPrint.infillMovementQueue:
            #process all queued infill moves
            processInfillMovementQueue(imq=currentPrint.infillMovementQueue, ps=currentPrint)

            #increment this as we write out the queue. This will be the tail position when processing
            queueStartPosition = copy.copy(currentPrint.infillMovementQueueOriginalStartPosition)
            queueStartPosition.E += currentPrint.deltaE #apply deltaE now since we will set and print movement E in this loop

            # adjust E values
            def adjustE(m: Movement):
              nonlocal queueStartPosition

              m.adjustE(startE=queueStartPosition.E)

              #track end position as start position of next move
              queueStartPosition = m.end

              #track original position
              currentPrint.infillMovementQueueOriginalStartPosition.E += m.end.E - m.start.E
              
              
            # write out gcode for movement
            def writeDroplet(m: Movement):
              out.write(f"{m.travelGcodeToEnd()}\n")
              out.write(f"{m.extrudeOnlyGcode()}\n")

            def writeAdjustedMove(m: Movement):
              out.write(f"{m.travelGcodeToStart()}\n")
              out.write(f"{m.gcode(adjustE=False)}\n")

            out.write(f"write queued infill moves\n")

            for m in currentPrint.infillMovementQueue:
              if m.dropletMovements: 
                for d in m.dropletMovements:
                  adjustE(m=d)
                  writeDroplet(m=d)
              else:
                adjustE(m=m)
                writeAdjustedMove(m=m)

            currentPrint.deltaE += currentPrint.infillMovementQueueOriginalStartPosition.E - currentPrint.originalPosition.E
            '''
            # print out original movements
            for nm in currentPrint.infillMovementQueue:
              movementGcode = nm.extrudeAndTravelGcode(ps=currentPrint)
              out.write(f"{movementGcode}\n")
            '''



            currentPrint.infillMovementQueue = None


          if currentFeature.featureType == LAYER_CHANGE:
            print(f"starting new layer")
            currentPrint.features = []
            testBoundingBox.advanceDropletRasterNextLayer()
          currentPrint.features.append(currentFeature)

          out.write(cl)
        elif m1Match: #check for M1 new layer/reset extrusion
          currentPrint.originalPosition.E = 0
          currentPrint.deltaE = 0
          out.write(cl)
        else:
          #save copy of last original gcode position before reading current line gcode position
          lastOriginalPosition: Position = copy.copy(currentPrint.originalPosition)

          # Update current print state variables
          updatePrintState(ps=currentPrint, cl=cl, sw=currentPrint.skipWrite)

          currentMovement = Movement(startPos=copy.copy(lastOriginalPosition), endPos=copy.copy(currentPrint.originalPosition), boundingBox=None)

          currentFeature = None
          if len(currentPrint.features) > 0:
            currentFeature = currentPrint.features[-1]

          if lastOriginalPosition.E != currentPrint.originalPosition.E: #current movement is extrusion movement
            newMovements: list[Movement] = [currentMovement] # list of new Movements bisected by boundingbox or list of just the original Movement
            if currentFeature and currentFeature.featureType == INFILL: #if movement is infill, check for boundingbox intersect
              boundingBoxSplitMovements = boundingBoxSplit(currentMovement, testBoundingBox)

              if boundingBoxSplitMovements and len(boundingBoxSplitMovements) > 1:
                0==0

              if boundingBoxSplitMovements:
                newMovements = []
                for nm in boundingBoxSplitMovements:
                  currentPrint.infillMovementQueue.append(nm)
                  #process infill movements that intersect boundingbox in batch once another feature type is found
                out.write(f"queued 1 => {len(boundingBoxSplitMovements)} infill movement\n")

            # write out unbroken up movements
            for nm in newMovements:
              movementGcode = nm.gcode(adjustE=True, deltaE=currentPrint.deltaE)
              out.write(f"{movementGcode}\n")
                
          else:
            out.write(cl)
          
          #print(f.tell())
          
          # start new infill map

      out.write(f';Post Processed with variable density\n')

      print(f"saved new mpf to {outputFilepath}")

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
#process(inputFilepath='test-square.mpf', outputFilepath='test-square-output.mpf')
process(inputFilepath='test-square-4-layer.mpf', outputFilepath='test-square-output.mpf')