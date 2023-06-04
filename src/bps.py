import binascii

class File:
    def __init__(self, patcher, name, index, data=b''):
        self.Patcher = patcher
        self.Name = name
        self.Index = index
        self.Offset = 0
        self.Data = data
        self.Size = len(data)

    def fail(self, message):
        return self.Patcher.fail(message.format(self.Name))
    
    def getDataToChecksum(self):
        return self.Data

    def validateChecksum(self):
        return self.Patcher.Patch.readChecksum(self) == binascii.crc32( self.getDataToChecksum() ) or self.fail('{} file checksum does not match expected checksum')

    def withinBounds(self, value):
        return value >= 0 and value <= self.Size
    
    def isValidRange(self, start, end):
        return start >= 0 and end <= self.Size

    def validateOffset(self, offset):
        return self.withinBounds(self.Offset+offset) or self.fail('Exceeded bounds of {} file')
    
    def read(self, start, end, asNumber=True):
        return (int.from_bytes(self.Data[start:end], 'little') if asNumber else self.Data[start:end])  if self.isValidRange(start, end) else self.fail('Attempting read beyond end of {} file')
    
    def readBytes(self, length):
        return self.readNext(length, False)

    def shiftOffset(self, shift):
        self.Offset += shift
        return self.Offset

    def readNext(self, length, asNumber=True):
        return self.read(self.Offset, self.shiftOffset(length), asNumber)
    
    def output(self, length):
        return self.Patcher.Target.write( self.readBytes(length) )
    
    def shift(self, data):
        self.shiftOffset( (-1 if data & 1 else 1) * (data >> 1) )
        return True

    def copy(self, length):
        return self.Patcher.decode( self.shift ) and self.output(length)
    
class Patch(File):
    def __init__(self, patcher, data):
        super().__init__(patcher, "Patch", 1, data)
        self.DataEnd = self.Size-12
        
    def validateFormat(self):
        return True if self.readBytes(4) == 'BPS1'.encode('UTF-8') else self.fail("{} file does not start with 'BPS1'")
    
    # Don't include this checksum value
    def getDataToChecksum(self):
        return self.Data[:-4]

    # This is for the MetaData, which is unused
    def handleSize(self, size):
        return self.readNext(size) is not False
    
    def readChecksum(self, file):
        return self.read(self.Size-4*file.Index, self.Size - 4*(file.Index-1))
    
    def hasDataRemaining(self):
        return self.Offset < self.DataEnd

    def validateFooter(self):
        return self.Offset == self.DataEnd or self.fail('Data extended beyond footer. Expected 12 bytes remaining, received ' + str(len(self.Patch.Data) - self.Patch.Offset))
        
class Source(File):
    def __init__(self, patcher, data):
        super().__init__(patcher, "Source", 3, data)

    def handleSize(self, size):
        return size == self.Size or self.fail('{} file size does not match expected size')
    
    def matchTarget(self, length):
        return self.Patcher.Target.write( self.read(self.Patcher.Target.Size, self.Patcher.Target.Size+length, False) )

class Target(File):
    def __init__(self, patcher):
        super().__init__(patcher, "Target", 2)

    def handleSize(self, size):
        self.Data = bytearray(size)
        return size or self.fail('{} file size is not > 0')

    # can read data which is written during this action, so need to process 1 byte at a time
    def output(self, length):
        for _ in range(length):
            if not self.write( self.readBytes(1) ): return False

        return True

    def write(self, data):
        if data is False: return False

        startSize = self.Size
        self.Size += len(data)

        if self.Size > len(self.Data): return self.fail('Exceeded bounds of {} file')

        self.Data[startSize:self.Size] = data
        return True

class Patcher:
    def __init__(self, patch, source):
        self.Success = True
        self.Message = ''

        self.Patch = Patch(self, patch)
        self.Target = Target(self)
        self.Source = Source(self, source)

        self.Actions = [
            self.Source.matchTarget,
            self.Patch.output,
            self.Source.copy,
            self.Target.copy
        ]

        self.parseHeader() and self.parseBody() and self.parseFooter()
    
    def fail(self, message):
        self.Success = False
        self.Message = message
        return False

    def decode(self, callback):
        number = 0
        shift = 1
        
        while True:
            byte = self.Patch.readNext(1)
            if byte is False: return False
            number += (byte & 0x7f) * shift
            if byte & 0x80: break
            shift <<= 7
            number += shift

        return callback(number)
    
    def parseHeader(self):
        return self.Patch.validateFormat() and self.parseChecksums() and self.parseSizes()

    def parseChecksums(self):
        return self.Patch.validateChecksum() and self.Source.validateChecksum()
    
    def parseSizes(self):
        return self.decode( self.Source.handleSize ) and self.decode( self.Target.handleSize ) and self.decode( self.Patch.handleSize )

    def parseBody(self):
        while self.Patch.hasDataRemaining() and self.decode( self.handleAction ):
            pass

        return self.Success
    
    def handleAction(self, data):
        return self.Actions[data & 0b11]((data >> 2) + 1)
    
    def parseFooter(self):
        return self.Patch.validateFooter() and self.Target.validateChecksum()