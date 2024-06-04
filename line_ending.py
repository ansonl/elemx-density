import enum

class LineEnding(enum.Enum):
  AUTODETECT = "autodetect"
  WINDOWS = "\r\n"
  UNIX = "\n"
  UNKNOWN = "unknown"

def determineLineEndingTypeInFile(fn) -> LineEnding:
  with open(fn, mode='rb') as f:
    sample1 = b''
    sample2 = b''
    c = 0
    while True:
      block = f.read(32)
      if not block:
        break
      if c%2:
        sample2=block
      else:
        sample1=block

      if bytes(LineEnding.WINDOWS.value,'utf-8') in (sample1+sample2 if c%2 else sample2+sample1):
        return LineEnding.WINDOWS
      if bytes(LineEnding.UNIX.value,'utf-8') in (sample2+sample1 if not c%2 else sample1+sample2):
        return LineEnding.UNIX
      c^=1

  return LineEnding.UNKNOWN 