import re, os, typing, queue, time, datetime, math, enum, copy

from printing_classes import *
from constants import *
from line_ending import *

bbOrigin = Position()
bbOrigin.X, bbOrigin.Y, bbOrigin.Z = -25, -25, 0
bbSize = Position()
bbSize.X, bbSize.Y, bbSize.Z = 50, 50, 0
testBoundingBox = BoundingBox(origin = bbOrigin, size=bbSize, density=0.5)

currentE = 0
insetX = 2
insetY = 3
spacingX = 6 #(0 6 12 18 24 30 36 42 48) + 1
spacingY = 4

movementEFor1mm = 2*1.96/.51

#ticks
tickLength = 2

#droplet
dropletWidth = 0.510

#overlaps
overlaps = [1, 3/4, 1/2, 1/3, 1/4, 1/5, 1/6, 1/7]

PULSE_OFF='PRIO_OFF'
PULSE_ON='PRIO_ON'

def process(outputFilepath: str):
  global currentE

  lineEndingFlavor = LineEnding.UNIX
  print('default to unix line ending')
  lineEnding = lineEndingFlavor.value

# ; feature fill
#PRIO_ON
#G1 X11.16109 Y4.2863 E883.83984 ; EInc=49.14629 cartesianDistance=25.06461 #angle=0.000 pulseDistance=0.51000

# nozzle is 0.45mm
# drop final size is 0.8mm
# spacing is 0.51mm
# E distance per 0.51mm of travel is 49.14629/25.06461 = 1.96mm of E movement per 0.51mm of travel for generated infill

  try:
    with open(outputFilepath, mode='w') as out:
      # Persistent variables for the read loop

      # print tick marks

      xStart = bbOrigin.X + insetX
      while xStart < bbOrigin.X+bbSize.X:

        startLower = Position(xStart, bbOrigin.Y)
        startLower.E = currentE
        endLower = Position(xStart, startLower.Y + tickLength)
        currentE += tickLength*movementEFor1mm
        endLower.E = currentE

        startUpper = Position(xStart, bbOrigin.Y+bbSize.Y)
        startUpper.E = currentE
        endUpper = Position(xStart, startUpper.Y - tickLength)
        currentE += tickLength*movementEFor1mm
        endUpper.E = currentE
        

        status = f"Travel to lower tick {startLower.X},{startLower.Y}"
        out.write(f";{status}\n")
        out.write(f"{PULSE_OFF}\n")
        out.write(f"{Movement(startPos=None, endPos=startLower).travelGcode()}\n")

        status= f"Extrude to {endLower.X},{endLower.Y}"
        out.write(f";{status}\n")
        out.write(f"{PULSE_ON}\n")
        out.write(f"{Movement(startPos=startLower, endPos=endLower).adjustE(ps=None)}\n")

        status = f"Travel to upper tick {startUpper.X},{startUpper.Y}"
        out.write(f";{status}\n")
        out.write(f"{PULSE_OFF}\n")
        out.write(f"{Movement(startPos=None, endPos=startUpper).travelGcode()}\n")

        status= f"Extrude to {endUpper.X},{endUpper.Y}"
        out.write(f";{status}\n")
        out.write(f"{PULSE_ON}\n")
        out.write(f"{Movement(startPos=startUpper, endPos=endUpper).adjustE(ps=None)}\n")

        xStart += spacingX
      
      # droplet tests
      yIteration = 0
      yStart = bbOrigin.Y + insetY
      while yStart + yIteration * spacingY <= bbOrigin.Y+bbSize.Y: #increase dwell time with Y
        xStart = bbOrigin.X + insetX
        xIteration = 0
        while xStart + xIteration * spacingX < bbOrigin.X+bbSize.X: #decrease droplet overlap with X

          dropletNumber = 0
          while dropletNumber < 10:

            dropletStart = Position(xStart + xIteration*spacingX + dropletWidth*dropletNumber - overlaps[xIteration]*dropletWidth*dropletNumber, yStart + yIteration * spacingY)
            dropletStart.E = currentE
            currentE += dropletWidth*movementEFor1mm
            dropletEnd = Position(xStart + xIteration * spacingX, yStart + yIteration * spacingY)
            dropletEnd.E = currentE

            status = f"Travel to droplet no. {dropletNumber} {dropletStart.X},{dropletStart.Y}"
            out.write(f";{status}\n")
            out.write(f"{PULSE_OFF}\n")
            out.write(f"{Movement(startPos=None, endPos=dropletStart).travelGcode()}\n")

            status = f"Dwell {xIteration*2/10} seconds"
            out.write(f";{status}\n")
            out.write(f"{DWELL_G4}{xIteration*2/10:.5f}\n")

            status = f"Extrude droplet no. {dropletNumber} {dropletStart.X},{dropletStart.Y} with overlap {overlaps[xIteration]}"
            out.write(f";{status}\n")
            out.write(f"{PULSE_ON}\n")
            out.write(f"{Movement(startPos=dropletStart, endPos=dropletEnd).extrudeOnlyGcode()}\n")
            out.write(f"{PULSE_OFF}\n")

            

            dropletNumber += 1

          xIteration += 1
        yIteration += 1


  except PermissionError as e:
    print(f"Failed to open {e}")


process(outputFilepath='droplet-movements.mpf')