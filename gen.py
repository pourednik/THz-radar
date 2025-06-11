import pyvisa as pvs
import time

class GenInstrument:
    def __init__(self, address='TCPIP0::192.168.85.202::inst0::INSTR'):
        self.rm = pvs.ResourceManager()
        self.address = address
        self.gen = self.rm.open_resource(self.address)
        self._connected = False  # Track connection status

    def connect(self):
        """
        Ensure the instrument is connected and ready for commands.
        If already connected, this should be a no-op.
        """
        if not self._connected:
            # Establish connection to hardware if not already connected
            self.gen = self.rm.open_resource(self.address)
            self._connected = True

    # def __enter__(self):
    #     print('there')
    #     self.gen = self.rm.open_resource(self.address)
    #     return self

    # def __exit__(self, exc_type, exc_val, exc_tb):
    #     if self.gen is not None:
    #         try:
    #             if exc_type is not None:
    #                 # If there was an error, try to turn off safely
    #                 try:
    #                     self.off()
    #                 except Exception as e:
    #                     print(f"Error during off(): {e}")
    #             print('here')
    #             self.gen.close()
    #         except Exception as e:
    #             print(f"Error closing instrument: {e}")

    def inst_ready(self):
        while not self.gen.query('*OPC?'):
            time.sleep(0.1)
            print('waiting')
        return 1

    def init(self, chirp_t, BW):
        self.connect()
        self.gen.write(':OUTPut 0')
        self.gen.write(':POW 10 dBm')
        self.inst_ready()
        self.gen.write(':FREQ 15 GHz')
        self.inst_ready()
        self.gen.write(':LFOutput:SOURce TRIGger')
        self.inst_ready()
        self.gen.write(':LFOutput:STATe 1')
        self.inst_ready()
        self.gen.write(':CHIRp:BLANking 1')
        self.inst_ready()
        self.gen.write(':CHIRp:COUNt 20')
        self.inst_ready()
        self.gen.write(':CHIRp:TIME ' + str(chirp_t))
        self.inst_ready()
        self.gen.write(':FREQuency:CENTer 15 GHz')
        self.inst_ready()
        self.gen.write('FREQuency:MODE FIXed')
        self.inst_ready()
        self.gen.write(':FREQuency:SPAN ' + str(BW))
        self.inst_ready()
        self.gen.write(':TRIGger:SOURce BUS')
        self.inst_ready()
        self.gen.write('FREQuency:MODE CHIRp')
        self.inst_ready()
        print(self.gen.query(':CHIRp:TIME?'))
        self.gen.write('FREQuency:MODE FIXed')
        self.inst_ready()
        self.close()

    def on(self):
        self.connect()
        self.gen.write(':OUTPut 1')
        self.inst_ready()
        self.gen.write('FREQuency:MODE CHIRp')
        self.inst_ready()
        self.close()

    def fire(self):
        self.connect()
        self.gen.write(':TRIGger:IMMediate')
        self.inst_ready()
        self.close()

    def off(self):
        self.connect()
        self.gen.write(':OUTPut 0')
        self.inst_ready()
        self.gen.write('FREQuency:MODE FIXed')
        self.inst_ready()
        self.close()

    def close(self):
        """
        Close the connection to the instrument.
        Should be safe to call multiple times.
        """
        if self._connected:
            # Close hardware connection
            self.gen.close()
            self._connected = False

# Example usage:
# with GenInstrument() as gen:
#     gen.init(chirp_t, BW)
#     gen.on()
#     gen.fire()
#     gen.off()