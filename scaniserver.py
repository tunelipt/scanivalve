import scanivalve
import base64

from xmlrpc.server import SimpleXMLRPCServer

class ScaniWrapper(object):

    def __init__(self, ipaddr='192.168.129.7'):

        self.ipaddr = ipaddr
        self.dtc = None
        
    def initialize(self, scanners):

        try:
            self.dtc = dtcinitium.DTCInitium(scanners, self.ipaddr)
        except:
            return (1, "Erro ao abrir o DTC Initium")
        return (0, "")

    def config(self, stbl=1, nfr=1, nms=1, msd=50, trm=0, port=None, fast=False):
        if self.dtc is None:
            return (1, "DTC não inicializado")
        try:
            self.dtc.config(stbl=stbl, nfr=nfr, nms=nms, msd=msd, trm=trm, port=port, fast=fast)
        except:
            return (1, "Erro ao configurar o DTC Initium")
        return (0, "")
            
    def close(self):
        if self.dtc is None:
            return (1, "DTC não inicializado")
        try:
            self.dtc.close()
        except:
            return (1, "Erro ao fechar a interface com o DTC Initium")
        return (0, "")
        
    def stop(self):
        if self.dtc is None:
            return (1, "DTC não inicializado")
        try:
            self.dtc.stop()
        except:
            return (1, "Erro ao abrir o parar a aquisição")
        return (0, "")
            
    def acquire(self, stbl=1, nms=None):
        if self.dtc is None:
            return (1, "DTC não inicializado")
        try:
            p, f = self.dtc.acquire(stbl, nms)
        except:
            return (1, "Erro ao adquirir dados")
        
        return 0, p.shape, p.tostring(), f
    
    
    def start(self, stbl=1, nms=None):
        if self.dtc is None:
            return (1, "DTC não inicializado")
        try:
            self.dtc.start(stbl=stbl, nms=nms)
        except:
            return (1, "Erro ao abrir o iniciar a aquisição")
        return (0, "")

    def read(self):
        if self.dtc is None:
            return (1, "DTC não inicializado")
        try:
            p, f = self.dtc.read()
        except:
            return (1, "Erro ao tentar ler os dados")
        return 0, p.shape, p.tostring(), f

    def isacquiring(self):
        if self.dtc is None:
            return (1, "DTC não inicializado")
        try:
            acq = self.dtc.isacquiring()
        except:
            return (1, "Erro ao determinar se a aquisição está ocorrendo")
        return 0, acq

    def samplesread(self):
        if self.dtc is None:
            return (1, "DTC não inicializado")
        try:
            ns = self.dtc.samplesread()
        except:
            return (1, "Erro ao determinar numero de pontos lidos")
        return 0, ns

    def samplerate(self):
        if self.dtc is None:
            return (1, "DTC não inicializado")
        try:
            freq = self.dtc.samplerate()
        except:
            return (1, "Erro ao determinar a taxa de amostragem")
        return 0, freq

        
        
    
        
def start_server(ip='localhost', port=10101, dtc_ip='192.168.129.7'):
    """Inicializa o servidor relacionando-o a uma instancia importada de um arquivo externo
    
    Keyword arguments:
    ip -- endereco do servidor
    port -- porta do servidor"""
    print("Inicializando interface do DTCInitium")
    dev = DTCWrapper(dtc_ip)
    
    srvr = DTCServer(ip, port, dev)
    srvr.start()

class DTCServer:
    """Cria a instancia do servidor responsavel pela comunicacao XML-RPC com o DTC Initium"""
    def __init__(self, ip, port, dev):
        self.dev=dev
        self.ip=ip
        self.port=int(port)
    def start(self):
        print("Starting XML-RPC Server...")
        #self.server = SimpleXMLRPCServer(("192.168.129.7", 8000), allow_none=True)
        self.server = SimpleXMLRPCServer((self.ip, self.port), allow_none=True)
        self.server.register_instance(self.dev)
        print("Serving XML-RPC...")
        self.server.serve_forever()


if __name__ == "__main__":
    print("Creating interface ...")
    start_server()
