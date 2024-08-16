import re, os, typing, queue, time, datetime, math, enum, copy

from printing_classes import *
from constants import *
from line_ending import *

bbOrigin = Position()
bbOrigin.X, bbOrigin.Y, bbOrigin.Z = -25, -5, 0
bbSize = Position()
bbSize.X, bbSize.Y, bbSize.Z = 50, 10, 0
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

      x = bbOrigin.X + insetX
      while x < bbOrigin.X+bbSize.X:

        startLower = Position(x, bbOrigin.Y)
        startLower.E = currentE
        endLower = Position(x, startLower.Y + tickLength)
        currentE += tickLength*movementEFor1mm
        endLower.E = currentE

        startUpper = Position(x, bbOrigin.Y+bbSize.Y)
        startUpper.E = currentE
        endUpper = Position(x, startUpper.Y - tickLength)
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

        x += spacingX
      
      # droplet tests
      testType = 0
      testIteration = 0
      y = bbOrigin.Y + insetY
      while y <= bbOrigin.Y+bbSize.Y:
        x = bbOrigin.X + insetX
        while x < bbOrigin.X+bbSize.X:

          if testType == 0:
            multiplier = 2*testIteration if testIteration > 0 else 1
            dropletStart = Position(x, y)
            dropletStart.E = currentE
            currentE += dropletWidth*movementEFor1mm*multiplier
            dropletEnd = Position(x, y)
            dropletEnd.E = currentE

            status = f"Travel to droplet {dropletStart.X},{dropletStart.Y}"
            out.write(f";{status}\n")
            out.write(f"{PULSE_OFF}\n")
            out.write(f"{Movement(startPos=None, endPos=dropletStart).travelGcode()}\n")

            status = f"Extrude droplet {dropletStart.X},{dropletStart.Y} with multiplier {multiplier}"
            out.write(f";{status}\n")
            out.write(f"{PULSE_ON}\n")
            out.write(f"{Movement(startPos=dropletStart, endPos=dropletEnd).extrudeOnlyGcode()}\n")

          elif testType == 1:

            lineLength = 4

            if testIteration <= 3: 
              multiplier = 2*testIteration if testIteration > 0 else 1
            else:
              multiplier = 2*(testIteration-3)

            dropletStart = Position(x, y)
            dropletStart.E = currentE
            currentE += lineLength*movementEFor1mm*multiplier
            dropletEnd = Position(x+lineLength, y)
            dropletEnd.E = currentE

            if testIteration > 3: #reverse movement extrusion
              currentE += lineLength*movementEFor1mm*multiplier
            dropletEnd2 = Position(x, y)
            dropletEnd2.E = currentE

            status = f"Travel to droplet {dropletStart.X},{dropletStart.Y}"
            out.write(f";{status}\n")
            out.write(f"{PULSE_OFF}\n")
            out.write(f"{Movement(startPos=None, endPos=dropletStart).travelGcode()}\n")

            status = f"Extrude droplet {dropletEnd.X},{dropletEnd.Y} with multiplier {multiplier}"
            out.write(f";{status}\n")
            out.write(f"{PULSE_ON}\n")
            out.write(f"{Movement(startPos=dropletStart, endPos=dropletEnd).adjustE(ps=None)}\n")

            if testIteration > 3: #reverse movement extrusion
              status = f"Extrude droplet {dropletEnd2.X},{dropletEnd2.Y} with multiplier {multiplier}"
              out.write(f";{status}\n")
              out.write(f"{Movement(startPos=dropletEnd, endPos=dropletEnd2).adjustE(ps=None)}\n")

          x += spacingX
          testIteration += 1
          
        y += spacingY
        testType += 1
        testIteration = 0


  except PermissionError as e:
    print(f"Failed to open {e}")


process(outputFilepath='droplet-movements.mpf')