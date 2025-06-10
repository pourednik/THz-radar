import pyvisa as pvs
import time

def inst_ready(inst):
    while not inst.query('*OPC?'):
        time.sleep(0.1)
        print('waiting')
    return 1

def init_gen():
    rm = pvs.ResourceManager()
    gen = rm.open_resource('TCPIP0::192.168.85.202::inst0::INSTR')
    gen.write(':OUTPut 0')
    gen.write(':POW 10 dBm')
    inst_ready(gen)
    gen.write(':FREQ 15 GHz')
    inst_ready(gen)
    gen.write(':LFOutput:SOURce TRIGger')
    inst_ready(gen)
    gen.write(':LFOutput:STATe 1')
    inst_ready(gen)
    gen.write(':CHIRp:BLANking 1')
    inst_ready(gen)
    gen.write(':CHIRp:COUNt 20')
    inst_ready(gen)
    gen.write(':CHIRp:TIME ' + str(chirp_t))
    inst_ready(gen)
    gen.write(':FREQuency:CENTer 15 GHz')
    inst_ready(gen)
    gen.write('FREQuency:MODE FIXed')
    inst_ready(gen)
    gen.write(':FREQuency:SPAN ' + str(BW))
    inst_ready(gen)
    gen.write(':TRIGger:SOURce BUS')
    inst_ready(gen)

    gen.write('FREQuency:MODE CHIRp')
    inst_ready(gen)
    print(gen.query(':CHIRp:TIME?'))
    gen.write('FREQuency:MODE FIXed')
    inst_ready(gen)

    gen.close()

    return gen


def fire():

    rm = pvs.ResourceManager()
    gen = rm.open_resource('TCPIP0::192.168.85.202::inst0::INSTR')


    gen.write(':OUTPut 1')
    inst_ready(gen)
    # It seems that chirp needs to be enable after RF On
    gen.write('FREQuency:MODE CHIRp')
    inst_ready(gen)
    gen.write(':TRIGger:IMMediate')
    inst_ready(gen)

    gen.close()


def off():

    rm = pvs.ResourceManager()
    gen = rm.open_resource('TCPIP0::192.168.85.202::inst0::INSTR')

    gen.write(':OUTPut 0')
    inst_ready(gen)
    gen.write('FREQuency:MODE FIXed')
    inst_ready(gen)

    gen.close()