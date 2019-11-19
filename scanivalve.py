import socket
import numpy as np
from select import select
import threading
import time


def clamp(x,min,max):
    "Clamps the value x between `min` and `max` "
    if x < min:
        return min
    elif x > max:
        return max
    else:
        return x


def check_server(ip='191.30.80.131', port=23, timeout=3):
    """
    # `check_server(ip, port, timeout)`
    
    Check if the server at `ip` on port `port` is responding.

    It waits for `timeout` seconds before returning `False`

    ## Arguments
    * `ip`: IP address of the server
    * `port`: Port number the connection should be attempted
    * `timeout`: Time in seconds that the function should wait before giving up
    ## Return
    * `True` if the server responded
    * `False`otherwise 
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((ip,port))
        return True
    except:
        return False



class Packet(object):
    """
    Handles EU with time DSA-3217 packets
    """
    
    def __init__(self, packet_info):
        self.model = packet_info['model']
        self.packlen = packet_info['packlen']
        self.press = packet_info['press']
        self.temp = packet_info['temp']
        self.t = packet_info['t']
        self.time = packet_info['time']
        self.tunit = packet_info['tunit']
        
        self.acquiring = False
        self.samplesread = 0
        self.fps = 1

        self.buf = None
        self.allocbuffer(1)
        self.dataread = False
        self.time1 = None
        self.time2 = None
        self.timeN = None
        self.stop_reading = False
        
    def allocbuffer(self, fps):
        """
        Allocates a buffer with `fps` elements
        """
        self.buf = np.zeros((fps, self.packlen), np.uint8)
        self.fps = fps
    def scan(self, s, dt):
        """
        Execute the scan command and read the frames into a buffer.
        """
        fps = self.fps
        self.dt = dt
        s.settimeout(max(0.5, 3 * dt))
        s.send(b"SCAN\n")

        self.acquiring = True
        self.time1 = time.monotonic()

        s.recv_into(self.buf[0], self.packlen)

        self.time2 = time.monotonic()
        self.timeN = self.time2
        self.dataread = True # There is data read
        self.samplesread = 1

        for i in range(1,fps):
            if self.stop_reading:
                print("STOP_READING")
                break
            
            s.recv_into(self.buf[i], self.packlen)
            self.timeN = time.monotonic()
            self.samplesread = i+1

        self.acquiring = False
        
    def get_pressure(self):
        """
        Given a a buffer filled with frames, return the pressure 
        """

        if not self.dataread:
            raise RuntimeError("No pressure to read from scanivalve!")
        nsamp = self.samplesread
        P = np.zeros((nsamp, 16), np.float64)
            
        for i in range(nsamp):
            np.copyto(P[i], self.buf[i,self.press].view(np.float32))
                
        return P
        
                          
    def get_time(self, meas=True):
        """
        Return the sampling time calculated from acquisition parameters.
        """
            
        nsamp = self.samplesread
        if meas:
            if nsamp > 4:
                return (self.timeN - self.time2) / (nsamp-1)
            elif nsamp > 0:
                return (self.timeN - self.time1) / nsamp
                
        if not self.t:
            return -1000.0
        
        ttype = self.buf[0,self.tunit].view(np.int32)[0]
        tmult = 1e6 if ttype==1 else 1e3
        t1 = self.buf[0,self.time].view(np.int32)[0]
        t2 = self.buf[self.samplesread-1,104:108].view(np.int32)[0]
        ns = max(1, self.samplesread-1)
        dt = (t2 - t1) / (tmult * ns)
        return self.dt
        
    def clear(self):
        if self.acquiring is not False:
            raise RuntimeError("Still acquiring data from scanivalve!")
        self.acquiring = False
        self.samplesread = 0
        self.dataread = False
        self.time1 = None
        self.time2 = None
        self.timeN = None
        self.stop_reading = False
        
    def isacquiring(self):
        "Is the scanivalve acquiring data?"
        return self.acquiring
    
    def read(self, meas=True):
        "Read the data from the buffers and return a pair with pressure and sampling rate"
        if self.samplesread > 0:
            p = self.get_pressure()
            dt = self.get_time(meas)
            return p, 1.0/dt
        else:
            raise RuntimeError("Nothing to read from scanivalve!")
    
    def stop(self):
        self.stop_reading = True
        return None
        
 
    
class ScanivalveThread(threading.Thread):
    """
    Handles asynchronous threaded data acquisition.

    Objects of this class, handle the threading part of the acquisition
    """
    
    def __init__(self, s, dt, pack):
        threading.Thread.__init__(self)
        self.pack = pack
        self.s = s
        self.dt = dt
        

    def run(self):
        self.pack.clear()
        self.pack.scan(self.s, self.dt)
       
    def isacquiring(self):
        return self.pack.isacquiring()
    
        
valid_lists = ['FPS', 'AVG', 'PERIOD', 'XSCANTRIG']

        
class Scanivalve(object):
    """
    # Data Aquisition from DSA3217
    
    Handles data acquisition from Scanivalve DSA-3217

    To initialize, the IP address of the scanivalve device should be used.

    
    ```python
    import scanivalve

    s = scanivalve.Scanivalve(ip)
    
    ```
    
    """
    def __init__(self, ip='191.30.80.131', tinfo=False):

        # Create the socket
        
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip = ip
        self.port = 23

        self.acquiring = False
        self.s.settimeout(5)
        # Connect to socket
        try:
            self.s.connect((self.ip,self.port))
        except:
            self.s = None
            raise RuntimeError("Unable to connect to scanivalve on IP:{}!".format(ip))

        # Clear errors and configure the scanivalve
        self.clear()
        self.numchans = 16
        
        self.FPS = 1
        self.PERIOD=500
        self.AVG=16
        self.XSCANTRIG = 0
        
        self.time = 2 if tinfo else 0
        
        self.set_var("BIN", 1)
        self.set_var("EU", 1)
        self.set_var("UNITSCAN", "PA")
        self.set_var("XSCANTRIG", 0)
        self.set_var("QPKTS", 0)
        self.set_var("TIME", self.time)
        self.set_var("SIM", 0)
        self.set_var("AVG", self.AVG)
        self.set_var("PERIOD", self.PERIOD)
        self.set_var("FPS", self.FPS)
        self.dt = self.PERIOD*1e-6*16 * self.AVG

        self.packet_info = self.packet_info()

        self.model = self.packet_info['model']
        
        self.pack = Packet(self.packet_info)
        
        self.pack.allocbuffer(self.FPS)
        self.thread = None

    def packet_info(self, tinfo=True):
        model = self.get_model().strip()
        if model=='3017':
            tinfo = False
            packlen = 104
            tt = None
            tunit = None
        elif model=='3217':
            press = slice(8, 72)
            temp = slice(72,104)
            if tinfo:
                packlen = 112
                tt = slice(104, 108)
                tunit = slice(108, 112)
                
            else:
                packlen = 104
                tt = None
                tunit =  None
        else:
            raise RuntimeError("Model {} not recognized!".format(model))
        
        return dict(model=model, packlen=packlen, press=press, temp=temp, t=tinfo, time=tt, tunit=tunit)
            
        

    def is_pending(self, timeout=0.5):
        "Check whether the scanivalve sent some information"

        r, w, x = select([self.s], [], [], timeout)

        if r == []:
            return None
        else:
            return True

    def list_any(self, command, timeout=0.2):
        """
        Most query commands of the DSA-3X17 consists of
        something like LIST S\n

        This method simplys sends the LIST command to the scanivalve and returns
        the data.
        """
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")

        cmd = ("LIST %s\n" % (command)).encode()

        self.s.send(cmd)

        buffer = b''
        
        while self.is_pending(timeout):
            buffer = buffer + self.s.recv(1492)
            
        return [b.split(' ') for b in  buffer.decode().strip().split('\r\n')]

    def list_any_map(self, command, timeout=0.5):
        """
        Takes data obtained from `list_any` method and builds a dictionary with the
        different parameters
        """

        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")

        buffer = self.list_any(command, timeout)
        list = {}
        for i in range(len(buffer)):
            list[buffer[i][1]] = buffer[i][2]
        return list

    def hard_zero(self):
        "Command to zero the DSA-3X17"
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")

        self.s.send(b"CALZ\n")
        
    

    def set_var(self, var, val):
        """
        Set the value of a parameter in the scanivalve by using the command
        SET var val
        """
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")

        cmd = ( "SET %s %s\n" % (var, val) ).encode()
        self.s.send(cmd)

    def get_model(self):
        """
        Returns the model of the scanivalve
        """
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")
        return self.list_any_map("I")["MODEL"]
        
    def stop(self):
        """
        Stop the scanivalve
        """
        self.pack.stop_reading = True
        self.pack.acquiring = False
        self.s.send(b"STOP\n")
            
        self.acquiring = False
        self.thread = None
        time.sleep(0.2)
        buffer = b''
        while self.is_pending(0.5):
            buffer = buffer + self.s.recv(1492)
        return None
    def clear(self):
        """
        Clear the error buffer in the scanivalve
        """
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")
        
        self.s.send(b"CLEAR\n")
    
    def error(self):
        """
        Returns a list of errors detected by the scanivalve.
        """
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")
        self.s.send(b"ERROR\n")

        buffer = b''
        
        while self.is_pending(1):
            buffer = buffer + self.s.recv(1492)
        return buffer
        return buffer.strip().split('\r\n')
    
        
        
    
    def config1(self, FPS=1, PERIOD=500, AVG=16, xtrig=False):
        """
        Configures data aquisition 
        """
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")

        XSCANTRIG = int(xtrig)
        if self.model=='3017':
            self.PERIOD = clamp(PERIOD, 500, 62500)  # 325 if raw packets: not implemented!
            self.FPS = clamp(FPS, 1, 2**31) # Could be 0. Not implemented for now!
            self.AVG = clamp(AVG, 1, 32767)
        else:
            self.PERIOD = clamp(PERIOD, 125, 65000)
            self.FPS = clamp(FPS, 1, 2**30) # Could be 0. Not implemented for now!
            self.AVG = clamp(AVG, 1, 240)

        self.dt = self.PERIOD*1e-6*16 * self.AVG
        self.set_var("FPS", self.FPS)
        self.pack.allocbuffer(self.FPS)
        self.set_var("AVG", self.AVG)
        self.set_var("PERIOD", self.PERIOD)
        self.set_var("XSCANTRIG", XSCANTRIG)
    def config(self, **kw):
        """
        Configures data aquisition 
        """
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")
        isold = self.model=='3017'
        for k in kw.keys():
            K = k.upper()
            if K == 'XSCANTRIG':
                val = int(kw[k])
                self.XSCANTRIG = val
            elif K=='PERIOD':
                x = int(kw[k])
                val = clamp(x, 500, 62500)  if isold else clamp(x, 160, 650000)
                self.PERIOD = val
            elif K=='AVG':
                x = int(kw[k])
                val = clamp(x, 1, 32767) if isold else clamp(x, 1, 240)
                self.AVG = val
            elif K=='FPS':
                x = int(kw[k])
                val = clamp(x, 1, 2**31) if isold else clamp(x, 1, 2**30)
                self.FPS = val
                self.pack.allocbuffer(self.FPS)
            else:
                RuntimeError("Illegal configuration. SET {} {} not implemented!".format(K, kw[k]))

            self.set_var(K, val)

        self.dt = self.PERIOD*1e-6*16 * self.AVG
        
        
    def acquire(self):
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")
        self.pack.scan(self.s, self.dt)
        p,freq = self.pack.read()
        self.pack.clear()
        return p, freq
    
    def start(self):
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")
        self.thread = ScanivalveThread(self.s, self.dt, self.pack)
        self.thread.start()
        self.acquiring = True
        
        
    def read(self):
        
        if self.thread is not None:
            self.thread.join()

        if self.pack.samplesread > 0:
            p, freq = self.pack.read()
            self.pack.clear()
            self.thread = None
            self.acquiring = False
            return p, freq
        else:
            #raise RuntimeError("Nothing to read")
            print("ERRO EM READ")
        
    def samplesread(self):
        if self.thread is not None:
            return self.pack.samplesread
        else:
            raise RuntimeError("Scanivalve not reading")
    def samplerate(self, meas=True):
        if self.thread is not None:
            dt = self.pack.get_time(True)
            if dt < -1.0:
                dt = self.dt
            return 1.0/dt
        else:
            raise RuntimeError("Scanivalve not reading")
        
    def isacquiring(self):
        if self.thread is not None:
            return self.pack.isacquring()
        else:
            raise RuntimeError("Scanivalve not reading")
        
    def close(self):
        if self.acquiring:
            self.stop()
        self.thread = None
        self.s.close()
        self.s = None

    def nchans(self):
        return 16

    def channames(self):
        return ["{:02d}".format(i+1) for i in range(self.nchans())]
    
    
    def list_config(self):
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")
        conf = dict(devtype='pressure', manufacturer='scanivalve', model=self.model,
                    parameters=self.list_any_map('S'))
        return conf
    
        
    
        

        
