import re, os, typing, queue, time, datetime, math, enum, copy, random, shutil

from functools import cmp_to_key

from printing_classes import *
from constants import *
from line_ending import *
from intersection import *
from infill import *

bbOrigin = Position()
bbOrigin.X, bbOrigin.Y, bbOrigin.Z = -10, -12.5, 1.0
bbSize = Position()
bbSize.X, bbSize.Y, bbSize.Z = 22.5, 25, 8
testBoundingBox = BoundingBox(origin = bbOrigin, size=bbSize, density=0.1)

# infill first pass planning
def getInfillRequirements(imq: list[Movement], ps: PrintState):
  for m in imq:
    if m.boundingBox:
      m.dropletMovements = splitMovementToDroplets(m)

      ps.infillModifiedDropletsOriginal += len(m.dropletMovements)
      ps.infillModifiedDropletsNeededForDensity += len(reduceDropletsToDensity(droplets=m.dropletMovements, density=m.boundingBox.densityAtLayerHeightForTargetDensity(layerHeight=ps.layerHeight)))

      if ps.layerHeight==1.2:
        0==0

      # Get supported locations if previous layer raster exists
      if m.boundingBox.dropletRaster:
        m.supportedPositions = findSupportedLocations(m=m)
        ps.infillModifiedDropletsSupportedAvailable += len(m.supportedPositions)
        m.dropletMovements = None # clear movement split droplets from initial planning. 

# infill 
def placeInfill(imq: list[Movement], ps: PrintState):
  #def compareSupportedPositionsCount(move1: Movement, move2: Movement):
  #  return len(move1.supportedPositions) - len(move2.supportedPositions)

  sortedMovements = copy.copy(imq)
  sortedMovements.sort(key=lambda x: len(x.supportedPositions))
  #sorted(sortedMovements, key=cmp_to_key(compareSupportedPositionsCount))

  totalDropletsPlaced = 0

  while ps.infillModifiedDropletsNeededForDensity > 0:
    dropletsPlaced = 0

    for m in sortedMovements:
      if m.boundingBox: # check if movement needs to be modified because it is in bounding box
        
        if m.boundingBox.dropletRaster == None: # initialize raster with [1] allocated if needed
          m.boundingBox.initializeDropletRaster()

        if m.boundingBox.dropletRaster[0] == None: #initial layer, reduce and space out drops
          reducedDroplets = reduceDropletsToDensity(droplets=m.dropletMovements, density=m.boundingBox.density)
          ps.infillModifiedDropletsNeededForDensity -= len(reducedDroplets)
          dropletsPlaced += len(reducedDroplets)
          m.dropletMovements = reducedDroplets
          for d in reducedDroplets:
            fillBBDropletRasterForDroplet(bb=m.boundingBox, droplet=d)
        else: # not initial layer, place drops on supported area
          if len(m.supportedPositions) > 0:
            # pick random unfilled support position to make droplet for
            sp = None
            while sp == None and len(m.supportedPositions) > 0:
              randomSupportPositionIdx = random.randint(0,len(m.supportedPositions)-1)

              # TODO: kernel size?
              # check if another placed droplet on this layer would overlap too much with this droplet
              if get3x3BBDropletRasterForPosition(bb=m.boundingBox, pos=m.supportedPositions[randomSupportPositionIdx][1], idx=1) == 0:
                sp = m.supportedPositions[randomSupportPositionIdx]
                break

              del m.supportedPositions[randomSupportPositionIdx]
            
            if sp:
              # create droplet
              supportPositionStart = sp[1]
              supportPositionEnd = copy.copy(sp[1])
              supportPositionEnd.E += m.dropletE
              supportDroplet = Movement(startPos=supportPositionStart, endPos=supportPositionEnd, boundingBox=m.boundingBox)

              # Add to unsorted list of supported position droplet movements. Sort this when all random position added by the original index
              if m.supportedPositionMovements == None:
                m.supportedPositionMovements = []
              m.supportedPositionMovements.append((sp[0], supportDroplet))

              # Unused because we sort supported droplets before adding to droplet movement list
              # Add droplet to list of droplets replacing the movement
              #if m.dropletMovements == None:
              #  m.dropletMovements = [supportDroplet]
              #else:
              #  m.dropletMovements.append(supportDroplet)

              # Fill current layer raster with droplet
              fillBBDropletRasterForDroplet(bb=m.boundingBox, droplet=supportDroplet)

              ps.infillModifiedDropletsNeededForDensity -= 1
              dropletsPlaced += 1

              # Remove position from supported positions
              del m.supportedPositions[randomSupportPositionIdx]

    totalDropletsPlaced += dropletsPlaced

    # Stop trying to place droplets if we ran out of valid positions
    if dropletsPlaced == 0:
      print(f"Ran out of support positions on layer {ps.layerHeight}")
      break

  # Compare the original random index stored in tuple
  #def compareSupportedPositionsRandomIdx(move1: tuple[int, Movement], move2: tuple[int, Movement]):
  #  return move1[0] - move2[0]

  # Sort all Movements' supportedPositionMovements and replace dropletMovements
  for m in imq:
    if m.supportedPositionMovements:
      m.supportedPositionMovements.sort(key=lambda x:x[0])
      m.dropletMovements = [spm[1] for spm in m.supportedPositionMovements]

  return totalDropletsPlaced

# infill
def processInfillMovementQueue(imq: list[Movement], ps: PrintState):
  ps.infillModifiedDropletsOriginal = 0
  ps.infillModifiedDropletsNeededForDensity = 0

  print(f"getting infill requirements on layer height {ps.layerHeight}")
  getInfillRequirements(imq, ps)
  print(f"infill on layer height {ps.layerHeight} requires {ps.infillModifiedDropletsNeededForDensity}/{ps.infillModifiedDropletsOriginal} droplets for density. Found {ps.infillModifiedDropletsSupportedAvailable} available support locations.")
  print(f"placing infill on layer height {ps.layerHeight}")
  totalDropletsPlaced = placeInfill(imq=imq, ps=ps)
  print(f"infill on layer height {ps.layerHeight} placed {totalDropletsPlaced} droplets and still requires {ps.infillModifiedDropletsNeededForDensity} droplets")

def outputInfillMovementQueue(imq: list[Movement], ps: PrintState):
  outputGcode = ''

  processInfillMovementQueue(imq=imq, ps=ps)

  #increment this as we write out the queue. This will be the tail position when processing
  queueStartPosition = copy.copy(ps.infillMovementQueueOriginalStartPosition)
  queueStartPosition.E += ps.deltaE #apply deltaE now since we will set and print movement E in this loop

  # adjust E values
  def adjustE(m: Movement):
    nonlocal queueStartPosition

    m.adjustE(startE=queueStartPosition.E)

    #track end position as start position of next move
    queueStartPosition = m.end

    #track original position
    ps.infillMovementQueueOriginalStartPosition.E += m.end.E - m.start.E
    
    
  # write out gcode to extrude a droplet
  def writeDroplet(m: Movement):
    nonlocal outputGcode

    # ElemX preview visual
    # Add move that is close to the final droplet position but not the same
    # Turn off for production print, only use for preview
    if ADD_ELEMX_PREVIEW_MOVE:
      fakeMove = Movement(endPos=copy.copy(m.end))
      fakeMove.end.X += 0.00001
      outputGcode += f"{FAKE_MOVE}\n"
      outputGcode += f"{fakeMove.travelGcodeToEnd()}\n"

    # Move to actual droplet position
    outputGcode += f"{m.travelGcodeToEnd()}\n"

    # Dwell
    if DWELL_BEFORE_EXTRUDE:
      outputGcode += f"{DWELL_G4}{DROPLET_DWELL:.5f}\n"

    # Extrude movement w/o XY position
    #outputGcode += f"{m.extrudeOnlyGcode()}\n"
    outputGcode += f"{m.extrudeAndMoveToEndGcode()}\n"

    # Dwell
    if DWELL_AFTER_EXTRUDE:
      outputGcode += f"{PULSE_OFF}\n"
      outputGcode += f"{DWELL_G4}{DROPLET_DWELL:.5f}\n"

  def writeAdjustedExtrusionMove(m: Movement):
    nonlocal outputGcode

    # Move to start position
    outputGcode += f"{m.travelGcodeToStart()}\n"

    # Add feature tag
    outputGcode += f"; {FEATURE_TYPE_WRITE_OUT}{m.feature.featureType}\n"

    # Activate PULSE_ON
    outputGcode += f"{PULSE_ON}\n"

    # Extrusion move
    outputGcode += f"{m.gcode(adjustE=False)}\n"

  def writeTravelMove(m: Movement):
    nonlocal outputGcode

    # Extrusion move
    outputGcode += f"{m.travelGcodeToEnd()}\n"

  outputGcode += f"; Start {len(imq)} queued infill moves\n"

  if ps.layerHeight == 0.96:
    0==0

  for m in imq:
    if m.start == None: #output original misc gcode
      outputGcode += f"{m.originalGcode}"

    elif m.boundingBox: # write droplets
      if m.dropletMovements:
        outputGcode += f"; Interpolated movement to {len(m.dropletMovements)} droplets\n"
        for d in m.dropletMovements:
          adjustE(m=d)
          writeDroplet(m=d)
      else:
        outputGcode += f"; Move with bounding box had no droplets placed so add travel move to the end. Original move is {m.originalGcode}\n"
        writeTravelMove(m=m)
    elif m.start.E != m.end.E: # write G1 move
      outputGcode += f"; Adjusted extrusion move\n"
      adjustE(m=m)
      writeAdjustedExtrusionMove(m=m)
    elif m.start != m.end: # write G0 move
      #outputGcode += f"{m.originalGcode}"
      writeTravelMove(m=m)
    else: #unknown
      0==1

  ps.deltaE += ps.infillMovementQueueOriginalStartPosition.E - ps.originalPosition.E

  ps.infillMovementQueue = None

  outputGcode += f"; End queued infill moves\n"

  return outputGcode

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
  startTime = time.monotonic()

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
      
      currentFeature = Feature()
      currentFeature.featureType = UNKNOWN
      currentFeature.start = f.tell()
      currentPrint.features = [currentFeature]


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
          
          if currentFeature.featureType == INFILL or currentFeature.featureType == TRAVEL:
            if currentPrint.infillMovementQueue == None:
              currentPrint.infillMovementQueue = []
              currentPrint.infillMovementQueueOriginalStartPosition = copy.copy(currentPrint.originalPosition) #save original position at queue start
            #if currentPrint.infillMovementQueue: # save feature tag gcode to queue (write feature tag twice, once where it is in the file and again when writing queue)
            #  currentPrint.infillMovementQueue.append(Movement(originalGcode=cl))

          elif currentPrint.infillMovementQueue: # if non INFILL/TRAVEL feature found
            #process all queued infill moves
            out.write(outputInfillMovementQueue(imq=currentPrint.infillMovementQueue, ps=currentPrint))

          if currentFeature.featureType == LAYER_CHANGE:
            print(f"starting new layer")
            currentPrint.features = []
            testBoundingBox.advanceDropletRasterNextLayer()

          # Replace outer perimeter with another string for output file only
          if currentFeature.featureType == OUTER_PERIMETER and OUTPUT_RENAME_OUTER_PERIMETER:
            cl = cl.replace(OUTER_PERIMETER, OUTPUT_RENAME_OUTER_PERIMETER)

          currentPrint.features.append(currentFeature)

          out.write(cl)
        elif m1Match: #check for M1 new layer/reset extrusion
          #process all queued infill moves
          if currentPrint.infillMovementQueue:
            out.write(outputInfillMovementQueue(imq=currentPrint.infillMovementQueue, ps=currentPrint))

          #Assume M1 will only appear right before plane change
          #During layer change, M1 comes before plane change
          currentPrint.doneLayerCount += 1
          out.write(f"{PULSE_OFF}\n") # Turn off pulse at end of layer to prevent dribbling
          out.write(f"{LAYERS_COMPLETED_WRITE_OUT}{currentPrint.doneLayerCount}\n")

          currentPrint.originalPosition.E = 0
          currentPrint.deltaE = 0
          out.write(cl)

          currentFeature = Feature()
          currentFeature.featureType = UNKNOWN
          currentFeature.start = clsp
          currentPrint.features.append(currentFeature)

          

          

        else: #no new feature tag found
          #save copy of last original gcode position before reading current line gcode position
          lastOriginalPosition: Position = copy.copy(currentPrint.originalPosition)

          # Update current print state variables
          updatePrintState(ps=currentPrint, cl=cl, sw=currentPrint.skipWrite)

          # retrieve current feature
          currentFeature = None
          if len(currentPrint.features) > 0:
            currentFeature = currentPrint.features[-1]

          currentMovement = Movement(startPos=copy.copy(lastOriginalPosition), endPos=copy.copy(currentPrint.originalPosition), boundingBox=None, originalGcode=cl, feature=currentFeature)

          if f.tell() == 83985:
            0==0

          if currentFeature and (currentFeature.featureType == INFILL or currentFeature.featureType == TRAVEL):
            if currentMovement.start != currentMovement.end: #G0 or G1
              if currentMovement.start.E != currentMovement.end.E: #G1 infill
                newMovements: list[Movement] = [currentMovement] # list of new Movements bisected by boundingbox or list of just the original Movement

                #if movement is infill, check for boundingbox intersect
                boundingBoxSplitMovements = boundingBoxSplit(currentMovement, testBoundingBox)

                if boundingBoxSplitMovements:
                  newMovements = boundingBoxSplitMovements
                    
                for nm in newMovements:
                  nm.originalGcode = cl
                  #process infill movements in batch once another feature type is found
                  currentPrint.infillMovementQueue.append(nm)
                  
                  out.write(f"; queued 1{(' =>' + str(len(boundingBoxSplitMovements))) if boundingBoxSplitMovements else ''} infill movement\n")
              else: #G0 travel
                currentPrint.infillMovementQueue.append(currentMovement)
                out.write(f"; queued 1 travel movement\n")
                '''
            else: #misc gcode
              if cl == f"{PULSE_ON}\n" or cl == f"{PULSE_OFF}\n":
                out.write(f"; strip out pulse command inside fill/travel feature")
              else:
                currentMovement.start = None
                currentMovement.end = None
                currentPrint.infillMovementQueue.append(currentMovement)
                out.write(f"; queued 1 misc gcode\n")
                '''
          
          else:
            out.write(cl)
          #print(f.tell())
          
          # start new infill map

      out.write(f';Post Processed with variable density\n')

      print(f"Saved new mpf to {outputFilepath}")

  except PermissionError as e:
    print(f"Failed to open {e}")

  print(f"Completed in {str(datetime.timedelta(seconds=time.monotonic()-startTime))}s")

#process(inputFilepath='test-square.mpf', outputFilepath='test-square-output.mpf')
process(inputFilepath=MPF_INPUT_FILE, outputFilepath=MPF_OUTPUT_FILE)
#process(inputFilepath='test-square-10-layer.mpf', outputFilepath='test-square-output.mpf')

#process(inputFilepath='test-square-10-layer.mpf', outputFilepath='test-square-output.gcode')

# copy and change extesion to .gcode for drag and drop preview in gcode previewer
#shutil.copyfile('test-square-output-2.mpf', 'test-square-output.gcode')