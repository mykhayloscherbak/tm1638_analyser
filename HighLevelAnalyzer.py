# High Level Analyzer
# For more information and documentation, please go to https://support.saleae.com/extensions/high-level-analyzer-extensions

SEGMENT_SYMBOLS = {
    0x00: " ",
    0x3F: "0", 0x06: "1", 0x5B: "2", 0x4F: "3", 0x66: "4",
    0x6D: "5", 0x7D: "6", 0x07: "7", 0x27 :"7", 0x7F: "8",
    0x6F: "9", 0x77: "A", 0x5F: "a", 0x7C: "b", 0x39: "C",
    0x5E: "d", 0x79: "E", 0x7B: "e", 0x71: "F", 0x50: "r"
}

from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, StringSetting, NumberSetting, ChoicesSetting


# High level analyzers must subclass the HighLevelAnalyzer class.
class Hla(HighLevelAnalyzer):
    # List of settings that a user can set for this High Level Analyzer.
    #my_string_setting = StringSetting()
    #my_number_setting = NumberSetting(min_value=0, max_value=100)
    my_choices_setting = ChoicesSetting(choices=('QYF-TM1638 board', 'tm1638 chip'))

    # An optional list of types this analyzer produces, providing a way to customize the way frames are displayed in Logic 2.
    result_types = {
        'disp cmd': {
            'format': 'cmd: {{data.disp_cmd}}'
        },
        'error': {
            'format': 'err: {{data.error}}'
        },
        'data out cmd' : {
            'format': 'cmd: {{data.disp_cmd}}, data: {{data.b0}} {{data.b1}} {{data.b2}} {{data.b3}} {{data.b4}} {{data.b5}} {{data.b6}} {{data.b7}} {{data.b8}} {{data.b9}} {{data.b10}} {{data.b11}} {{data.b12}} {{data.b13}} {{data.b14}} {{data.b15}}'
        },
        'data in cmd': {
            'format': 'cmd: {{data.disp_cmd}}, data: {{data.b0}} {{data.b1}} {{data.b2}} {{data.b3}}'
        },
        'data out cmd decoded' : {
            'format' : 'cmd: {{data.disp_cmd}}, decoded: {{data.str}}'
        },
        'data in cmd decoded': {
            'format': 'cmd: {{data.disp_cmd}}, decoded: {{data.str}}'
        }
    }


    def __init__(self):
        '''
        Initialize HLA.

        Settings can be accessed using the same name used above.
        '''

        #print("Settings:", self.my_choices_setting)
        self.state = 'Init'
        self.start_time = None
        self.data_mode = 'DataInvalid'
        self.addr = 0
        self.increment = False
        self.data = [0] * 16
        self.disp_cmd = ''
        self.multibyte = False


    def __analyse__(self, framedata, start_time, end_time):
        byte = int.from_bytes(framedata['mosi'])
        if not self.multibyte:

            cmd = (byte >> 6) & 0x3
            if cmd == 0x1:
                if byte & 0x3 == 0:
                    self.data_mode = 'DataOut'
                    self.disp_cmd = 'cmd: Data out'
                if byte & 0x3 == 2:
                    self.data_mode = 'DataIn'
                    self.addr = 0
                    self.multibyte = True
                    self.disp_cmd = 'cmd: Data in'
                if byte & 0x1 == 1 or byte & 0x8 == 0x8: # invalid lsb or test mode
                    self.data_mode = 'DataInvalid'
                self.increment = byte & 0x04 == 0
                self.disp_cmd = 'Mode: {:s}, inc: {:s}'.format(self.data_mode,'yes' if self.increment else 'no')
            if cmd == 0x3:
                self.addr = byte & 0x0f
                self.disp_cmd = 'Addr: {:d}'.format(self.addr)
                self.multibyte = True
                self.data_mode = 'DataOut'
            if cmd == 0x2:
                brightness = byte & 0x07 + 1
                if byte & 0x8 == 0:
                    brightness = 0
                self.disp_cmd = 'Brightness = {:d}'.format(brightness)

        else:
            self.data[self.addr] = byte
            self.addr += 1
            if self.data_mode == 'DataOut':
                self.addr = self.addr & 0xF
            if self.data_mode == 'DataIn':
                self.addr = self.addr & 0x03

    def __decode_data__(self, data_type, data):
        result = ''
        if data_type == 'data out cmd':
            b_tmp = []
            for i in range(8):
                b_tmp.append(data[i * 2])
            b_tmp = bytes(b_tmp)
            transformed = bytearray(8)
            for byte in range(8):
                for bit in range(8):
                    if b_tmp[byte] & (1 << bit) != 0:
                        transformed[7- bit] |= (1 << byte)
            result = "\""
            for s in transformed:
                symbol = SEGMENT_SYMBOLS.get(s & 0x7F, None)
                if symbol is not None:
                    result = result + symbol
                else:
                    result = result + "<{:02X}>".format(s)
                if s & 0x80 != 0:
                    result = result + '.'
            result = result + "\""
        elif data_type == 'data in cmd':
            keys_bitmap = {
                1:  "R3C1",
                2:  "R1C1",
                5:  "R3C2",
                6:  "R1C2",
                9:  "R3C3",
                10: "R1C3",
                13: "R3C4",
                14: "R1C4",
                17: "R4C1",
                18: "R2C1",
                21: "R4C2",
                22: "R2C2",
                25: "R4C3",
                26: "R2C3",
                29: "R4C4",
                30: "R2C4"
            }
            b32 = data[0] + (data[1] << 8) + (data[2] << 16) + (data[3] << 24)
            result = ""
            for bit in range(32):
                if b32 & (1 << bit) != 0 and bit in keys_bitmap.keys():
                    result = result+keys_bitmap[bit] + " "
        format = {'disp_cmd': self.disp_cmd, 'str' : result}
        return format

    def __flush__(self,end_time):
        retval = None
        if self.multibyte :
            format = {'disp_cmd': self.disp_cmd}
            out_needed = False
            if self.data_mode == 'DataOut':
                data_type = 'data out cmd'
                out_needed = True
                for i in range(16):
                    format['b{:d}'.format(i)] = self.data[i]
            if self.data_mode == 'DataIn':
                out_needed = True
                data_type = 'data in cmd'
                for i in range(4):
                    format['b{:d}'.format(i)] = self.data[i]
            if out_needed:
                if self.my_choices_setting == 'QYF-TM1638 board':
                    decoded = self.__decode_data__(data_type, self.data)
                    retval = AnalyzerFrame(data_type + ' decoded', self.start_time, end_time, decoded)
                else:
                    retval = AnalyzerFrame(data_type, self.start_time, end_time, format)
        else:
            retval = AnalyzerFrame('disp cmd', self.start_time, end_time, {'disp_cmd': self.disp_cmd})
        self.multibyte = False
        self.data_mode = 'DataInvalid'
        return retval


    def decode(self, frame: AnalyzerFrame):
        '''
        Process a frame from the input analyzer, and optionally return a single `AnalyzerFrame` or a list of `AnalyzerFrame`s.

        The type and data values in `frame` will depend on the input analyzer.
        '''

        # Return the data frame itself

        if frame.type == "enable":
            self.state = "Data"
            self.start_time = frame.start_time
        if frame.type == "disable":
            self.state = "Idle"
            return self.__flush__(frame.start_time)

        if frame.type == 'result':

                if self.state != 'Data':
                    return AnalyzerFrame('error', frame.start_time, frame.end_time, {'error': 'Unexpected data'})
                else:
                    return self.__analyse__(frame.data,  frame.start_time, frame.end_time)

