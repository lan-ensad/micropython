from machine import Pin
from machine import I2C
import time
import ustruct
import math

DATA_FORMAT = 0x31
BW_RATE  = 0x2c
POWER_CTL = 0x2d
INT_ENABLE  = 0x2E
OFSX = 0x1e
OFSY =0x1f
OFSZ =0x20

class ADXL345:
    def __init__(self, scl=7, sda=6, MAXS=(270,256,208)):
        self.scl = scl
        self.sda = sda
        
        self.maxx, self.maxy, self.maxz = MAXS
        self.mm_buffer = []
        self.buffer_size = 5
        
        
        time.sleep(1)
        #Initialisation du protocle I2C
        self.i2c = i2c = I2C(0, scl=Pin(self.scl), sda=Pin(self.sda), freq=400000)
        
        #Identification du catpeur ADXL345 
        slv = self.i2c.scan() #renvois un tableau contenant les adresses de toutes les devices i2C connectées au microcontroleur.
        #print(slv)
        
        for s in slv: #Pour toutes les devies I2C connectées
            buf = self.i2c.readfrom_mem(s, 0, 1) #Requête de l'identifiant
            #print(buf)
            if(buf[0] == 0xe5): #S'il sagit bien du ADXL345 (dont l'identifiant est 0xe5 ) 
                self.slvAddr = s
                #print('adxl345 trouvé !')
                break #Sortir de la boucle
        
        #Mise en route de l'ASXL345
        self.writeByte(POWER_CTL,0x00)
        self.writeByte(POWER_CTL,0x10)
        self.writeByte(POWER_CTL,0x08)
        time.sleep(1)
    
    def get_XYZaccel() : #A faire
        pass
    
    def get_XYZspeed() : #A faire
        pass
    
    def get_XYZposition() : #A faire
        pass
    
    def get_PHITETAangles(self) :
        x,y,z = self.readXYZ()
        phi = math.atan2(y,x)
        teta = math.acos(max(-1,min(1,z/self.maxz)))
        
        return phi/(2*math.pi)*360 , teta/(2*math.pi)*360
    
    
    def readXYZ(self):
        
        buffer = self.i2c.readfrom_mem(self.slvAddr, 0x32, 6) #Lecture des registres contenant les données de mesures (liste des registres page 24 https://docs.rs-online.com/1b7e/0900766b812fa340.pdf )
        
        # Short little-endian : Format des données d'acquisition dans la mémoire du capteur (voir https://docs.micropython.org/en/latest/library/struct.html )
        fmt = '<h'
        
        #Lecture de la mesure selon l'axe X
        x = ustruct.unpack(fmt, buffer[0:2])[0] #Parsing des données (buffer[0:2]) et conversion des bytes en float
        #x = x/self.maxx #Normalisation

        #Lecture de la mesure selon l'axe Y
        y = ustruct.unpack(fmt, buffer[2:4])[0] 
        #y = y/self.maxy #Normalisation
        
        #Leture de la mesure selon l'axe Z
        z = ustruct.unpack(fmt, buffer[4:6])[0] 
        #z = z/self.maxz #Normalisation
        
        #Calcule de la moyenne mobile :
        
        self.mm_buffer.append([x,y,z])# Ajout au buffer 
        if len(self.mm_buffer) > self.buffer_size : #Gestion de la taille du buffer (bon pour le coup ça c'est la lourdeur du python)
            self.mm_buffer.pop(0)
        
        mx = 0
        my = 0
        mz = 0
        for v in self.mm_buffer : #Sommes de valeurs
            mx += v[0]
            my += v[1]
            mz += v[2]
        mx /= len(self.mm_buffer) #Division par la taille du buffer donnant la moyenne
        my /= len(self.mm_buffer)
        mz /= len(self.mm_buffer)
        
        return (mx,my,mz)

    def writeByte(self, addr, data):
        d = bytearray([data])
        self.i2c.writeto_mem(self.slvAddr, addr, d)
    def readByte(self, addr):
        return self.i2c.readfrom_mem(self.slvAddr, addr, 1)

#Exemple d'utilisation
# snsr = ADXL345(7, 6)
# while True:
#     x,y = snsr.get_PHITETAangles()
#     print('phi:',x,'teta:',y)
#     time.sleep(0.1)


