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



class PackDSA3X17(object):

    def __init__(self, s, packlen=112, packid=0x07, rpress=slice(8, 72),
                 rttype=slice(108,112), rtime=slice(104,108)):
        self.buf = None
        self.acquiring = False
        self.samplesread = 0
        self.fps = 1
        self.allocbuffer(1)
        self.dataread = False
        self.s = s
        self.packlen = packlen
        self.packid = packid
        self.rpress = rpress
        self.rtime = rtime
        self.dt = None
        return
    
    def setdt(self, dt):
        self.dt = dt
        return
        
    def allocbuffer(self, fps):
        """
        Allocates a buffer with `fps` elements
        """
        self.buf = np.zeros((fps, self.packlen), np.uint8)
        self.fps = fps

    def scan(self):
        """
        Execute the scan command and read the frames into a buffer.
        """
        s = self.s
        dt = self.dt
        fps = self.fps
        s.settimeout(max(0.2, 3 * dt))
        s.send(b"SCAN\n")
        self.acquiring = True
        try:
            for i in range(fps):
                s.recv_into(self.buf[i], self.packlen)
                self.dataread = True # There is data read
                self.samplesread = i+1
        except:
            self.acquiring = False
            raise RuntimeError("Unaible to read frames from scanivalve")
                
        self.acquiring = False

    def get_pressure(self):
        """
        Given a a buffer filled with frames, return the pressure 
        """
        if not self.dataread:
            raise RuntimeError("No pressure to read from scanivalve!")
        nsamp = self.samplesread
        press = np.zeros((nsamp, 16), np.float64)
            
        for i in range(nsamp):
            np.copyto(press[i], self.buf[i,rpress].view(np.float32))
                
        return press
        
                          
    def get_time(self):
        """
        Given a buffer filled with frames, return the time discretization.
        """
        
        if not self.dataread:
            raise RuntimeError("No pressure to read from scanivalve!")
        if self.rtime is not None:
            ttype = self.buf[0,self.rtype].view(np.int32)[0]
            tmult = 1e6 if ttype==1 else 1e3
            t1 = self.buf[0,104:108].view(np.int32)[0]
        t2 = self.buf[self.samplesread-1,104:108].view(np.int32)[0]
        ns = max(1, self.samplesread-1)
        dt = (t2 - t1) / (tmult * ns)
        return dt
        
    def clear(self):
        if self.acquiring is not False:
            raise RuntimeError("Still acquiring data from scanivalve!")
        self.acquiring = False
        self.samplesread = 0
        self.dataread = False
        
    def isacquiring(self):
        "Is the scanivalve acquiring data?"
        return self.acquiring
    
    def read(self):
        "Read the data from the buffers and return a pair with pressure and sampling rate"
        
        if self.samplesread > 0:
            p = self.get_pressure()
            dt = self.get_time()
            return p, 1.0/dt
        else:
            raise RuntimeError("Nothing to read from scanivalve!")


class PackET3217(object):
    """
    Handles EU with time DSA-3217 packets
    """
    
    def __init__(self):
        self.buf = None
        self.packlen = 112
        self.packid  = 0x07
        self.acquiring = False
        self.samplesread = 0
        self.fps = 1
        self.allocbuffer(1)
        self.dataread = False
        
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
        for i in range(fps):
            s.recv_into(self.buf[i], self.packlen)
            self.dataread = True # There is data read
            self.samplesread = i+1
        #self.samplesread = fps
        self.acquiring = False
        #self.dataread = True
        

    def get_pressure(self):
        """
        Given a a buffer filled with frames, return the pressure 
        """

        if not self.dataread:
            raise RuntimeError("No pressure to read from scanivalve!")
        nsamp = self.samplesread
        press = np.zeros((nsamp, 16), np.float64)
            
        for i in range(nsamp):
            np.copyto(press[i], self.buf[i,8:72].view(np.float32))
                
        return press
        
                          
    def get_time(self):
        """
        Return the sampling time calculated from acquisition parameters.
        """
        ttype = self.buf[0,108:112].view(np.int32)[0]
        tmult = 1e6 if ttype==1 else 1e3
        t1 = self.buf[0,104:108].view(np.int32)[0]
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
        
        
    def isacquiring(self):
        "Is the scanivalve acquiring data?"
        return self.acquiring
    
    def read(self):
        "Read the data from the buffers and return a pair with pressure and sampling rate"
        if self.samplesread > 0:
            p = self.get_pressure()
            dt = self.get_time()
            return p, 1.0/dt
        else:
            raise RuntimeError("Nothing to read from scanivalve!")
    
    
        

    
    

class PackEU3217(object):
    "Handles DSA-3217 EU packets"
    def __init__(self):
        self.buf = None
        self.packlen = 104
        self.packid  = 0x05
        self.acquiring = False
        self.samplesread = 0
        self.fps = 1
        self.dt = 0.0
        self.allocbuffer(1)
        self.dataread = False
        
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
        for i in range(fps):
            s.recv_into(self.buf[i], self.packlen)
            self.dataread = True # There is data read
            self.samplesread = i+1
        #self.samplesread = fps
        self.acquiring = False
        #self.dataread = True
        

    def get_pressure(self):
        """
        Given a a buffer filled with frames, return the pressure 
        """

        if not self.dataread:
            raise RuntimeError("No pressure to read from scanivalve!")
        nsamp = self.samplesread
        press = np.zeros((nsamp, 16), np.float64)
            
        for i in range(nsamp):
            np.copyto(press[i], self.buf[i,8:72].view(np.float32))
                
        return press
        
                          
    def get_time(self):
        """
        Return the sampling time calculated from acquisition parameters.
        """
        return self.dt
        
    def clear(self):
        if self.acquiring is not False:
            raise RuntimeError("Still acquiring data from scanivalve!")
        self.acquiring = False
        self.samplesread = 0
        self.dataread = False
        
        
    def isacquiring(self):
        "Is the scanivalve acquiring data?"
        return self.acquiring
    
    def read(self):
        "Read the data from the buffers and return a pair with pressure and sampling rate"
        if self.samplesread > 0:
            p = self.get_pressure()
            dt = self.get_time()
            return p, 1.0/dt
        else:
            raise RuntimeError("Nothing to read from scanivalve!")
    
    
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
        self.pack.scan(self.s, self.dt)
        #p,freq = self.pack.read()
        #self.pack.clear()
        #return p, freq
       
    def isacquiring(self):
        return self.pack.isacquiring()
    
        
        
        
class Scanivalve(object):
    """
    Handles data acquisition from Scanivalve DSA-3217

    To initialize, the IP address of the scanivalve device should be used.
    ```python
    import scanivalve

    s = scanivalve.Scanivalve(ip)
    
    ```
    
    """
    def __init__(self, ip='191.30.80.131', tinfo=True, port=23):

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip = ip
        self.port = port

        self.acquiring = False

        self.s.connect((self.ip,self.port))
        self.clear()
        self.numchans = 16
        
        self.FPS = 1
        self.PERIOD=500
        self.AVG=16
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
        if tinfo:
            self.pack = PackET3217()
        else:
            self.pack = PackEU3217()

        self.pack.allocbuffer(self.FPS)
        self.thread = None
        
        
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
        Takes data obtained from `list_any` method and builds a 
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
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")

        cmd = ( "SET %s %s\n" % (var, val) ).encode()
        self.s.send(cmd)

    def get_model(self):
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")
        return self.list_any_map("I")["MODEL"]
        
    def stop(self):
        self.s.send(b"STOP\n")
        #if self.acquiring:
            
        time.sleep(0.2)
        buffer = b''
        while self.is_pending(0.5):
            buffer = buffer + self.s.recv(1492)
        return None
    def clear(self):
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")
        self.s.send(b"CLEAR\n")
    
    def error(self):
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")
        self.s.send(b"ERROR\n")

        buffer = b''
        
        while self.is_pending(1):
            buffer = buffer + self.s.recv(1492)
        return buffer
        return buffer.strip().split('\r\n')
    
        
        
        
    def config(self, FPS=1, PERIOD=500, AVG=16):
        if self.acquiring:
            raise RuntimeError("Illegal operation. Scanivalve is currently acquiring data!")
        self.PERIOD = clamp(PERIOD, 125, 65000)
        self.FPS = clamp(FPS, 1, 2**30)
        self.AVG = clamp(AVG, 1, 240)
        self.dt = self.PERIOD*1e-6*16 * self.AVG
        self.set_var("FPS", self.FPS)
        self.pack.allocbuffer(self.FPS)
        self.set_var("AVG", self.AVG)
        self.set_var("PERIOD", self.PERIOD)
        
        
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
        self.thread.join()
        p, freq = self.pack.read()
        self.pack.clear()
        self.thread = None
        self.acquiring = False
        
        return p, freq
    def samplesread(self):
        if self.thread is not None:
            return self.pack.samplesread
        else:
            raise RuntimeError("Scanivalve not reading")
    def isacquiring(self):
        if self.thread is not None:
            return self.pack.isacquring()
        else:
            raise RuntimeError("Scanivalve not reading")
        
    
        
    
