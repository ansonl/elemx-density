import re, os, typing, queue, time, datetime, math, enum, copy, random, shutil

from line_ending import *

from io import TextIOWrapper

START_GCODE_END = 'PARAM_SETUP'

SPLIT_AFTER_GCODE = 'M1'
END_GCODE_START = 'G53 G0 Z=$MA_POS_LIMIT_PLUS[Z]-1'

def outFilepathGenerator(outputDirectory: str, i: int):
  return f"{outputDirectory}/{i:d}.mpf"

def startOutput(outputDirectory: str, layer: int, startGcode: str) -> TextIOWrapper:
  try:
    outFile = open(outFilepathGenerator(outputDirectory=outputDirectory, i=layer), mode='w')
  except PermissionError as e:
    print(f"Failed to open {e}")

  outFile.write(startGcode)
  return outFile

def endOutput(outFile: TextIOWrapper, endGcode: str):
  outFile.write(endGcode)

def process(inputFilepath: str, outputDirectory: str):
  startTime = time.monotonic()

  lineEndingFlavor = determineLineEndingTypeInFile(inputFilepath)
  print(f"detected line ending {repr(lineEndingFlavor)}")
  if lineEndingFlavor == LineEnding.UNKNOWN:
    lineEndingFlavor = LineEnding.UNIX
    print('default to unix line ending')
  lineEnding = lineEndingFlavor.value

  try:
    with open(inputFilepath, mode='r') as f:
      
      startGcode = ''
      startGcodePosition = -1
      endGcode = ''
      endGcodePosition = -1

      cl = True
      if len(startGcode) == 0:
        while cl:
          cl = f.readline()
          startGcode += cl
          if cl.startswith(START_GCODE_END):
            startGcodePosition = f.tell()
            break

      if len(endGcode) == 0:
        while cl and cl.startswith(END_GCODE_START) == False:
          cl = f.readline()
          if f.tell() == 758693:
            0==0
        if cl.startswith(END_GCODE_START):
          endGcodePosition = f.tell() - len(cl) - (len(lineEnding)-1)
          endGcode += cl
          while cl:
            cl = f.readline()
            endGcode += cl
        
      if startGcodePosition == -1:
        print('no start gcode end found')
      if endGcodePosition == -1:
        print('no end gcode start found')
      
      # jump back to after start gcode
      f.seek(startGcodePosition, os.SEEK_SET)

      layer: int = 0

      outFile = startOutput(outputDirectory=outputDirectory, layer=layer, startGcode=startGcode)

      cl = True
      while cl and cl != endGcodePosition:
        cl = f.readline()
        outFile.write(cl)

        if cl.startswith(SPLIT_AFTER_GCODE) == True:
          endOutput(outFile=outFile, endGcode=endGcode)
          
          print(f"Wrote layer {layer} to file {outFilepathGenerator(outputDirectory=outputDirectory, i=layer)}")
          layer += 1

          outFile = startOutput(outputDirectory=outputDirectory, layer=layer, startGcode=startGcode)

      endOutput(outFile=outFile, endGcode=endGcode)
      print(f"Wrote layer {layer} to file {outFilepathGenerator(outputDirectory=outputDirectory, i=layer)}")
  except PermissionError as e:
    print(f"Failed to open {e}")

  print(f"Completed in {str(datetime.timedelta(seconds=time.monotonic()-startTime))}s")

#process(inputFilepath='test-square-25x25x10.mpf', outputDirectory="./")
process(inputFilepath='test-square-25x25x10-original.mpf', outputDirectory="./")