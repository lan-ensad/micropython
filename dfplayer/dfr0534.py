from machine import UART
import time


class DFR0534 :
    def __init__(self, rx=20, tx=21) :#Pins RX et TX pour le XIAO ESP32 C3
        self.RX = rx
        self.TX = tx
        
        self.uart1 = UART(1, baudrate=9600, tx=TX, rx=RX)
        self.ANSWER_WAIT_TIME = .02 # Constante de temps minimale permettant de lire la réponse d'une commande (après tâtonnage, peut probablement être modifiée, voir retirée [en utilisant le pin Busy du DFR0534 en particulier])
        #print(self.is_playing())
    
    def is_playing(self) :
        commande = b'\xaa\x01\x00\xab'
        self.uart1.write(commande) #Envoie de la commande 
        time.sleep(self.ANSWER_WAIT_TIME) #Attente de la réponse
        answer = self.uart1.read()#Lecture de la réponse 
        
        if answer != None : #Si réponse il y a
            return bool(answer[2])
            # La répons est de forme :
            #\xaa					\x01					\x01							|\x00				\xAB
            #Constante de démarrage	|numéro de la commande	|taille (en byte) de la réponse	|Etat de la lecture	|Somme de vérification 
            #								(ici 01)					(ici 1						(0 ou 1)
            # answer[3] se réfere à la 3 ème valeur de la réponse (on part bien de 0!), qui est l'état de la lecture
            # En python, un nombre peut être converti en booléen (0 est False sinon True)
        else :
            print('connexion non établie')
    
    def play(self):
        commande = b'\xaa\x02\x00\xac'
        self.uart1.write(commande)
    
    def pause(self) :
        commande = b'\xaa\x03\x00\xad'
        self.uart1.write(commande)

    def stop(self):
        commande = b'\xaa\x04\x00\xae'
        self.uart1.write(commande)

    def play_prev(self):
        commande = b'\xaa\x05\x00\xaf'
        self.uart1.write(commande)

    def play_next(self):
        commande = b'\xaa\x06\x00\xb0'
        self.uart1.write(commande)

    
    def set_volume(self, v) :
        v= int(v)
        v = min(30,max(0,v))
        
        #			commande			valeur	checksum
        commande = b'\xaa\x13\x01' + bytes([v, v + 0xbe])
        #Envoyer la somme du message (appellée checksum) à la fin du message est un moyen courrant de vérifier l'intégrité du message.
        #Ici 0xbe = hex(sum(b'\xaa\x13\x01'))
        
        self.uart1.write(commande)
        
    def play_track(self,track):
        track = max(0,int(track))
        commande = b'\xaa\x07\x02\x00' + bytes([track, track + 0xb3])
        self.uart1.write(commande)
    
    # Implémanter les commandes x08→x12 >.<

    def volume_up(self) :
        commande = b'\xaa\x14\x00\xbe'
        self.uart1.write(commande)
    
    def volume_down(self):
        commande = b'\xaa\x15\x00\xbf'
        self.uart1.write(commande)
    
    def loop_mode(self, v) : #De 1 à 6, dans l'ordre : LOOPBACKALL, SINGLEAUDIOLOOP, SINGLEAUDIOSTOP, PLAYRANDOM,DIRECTORYLOOP, RANDOMINDIRECTORY, SEQUENTIALINDIRECTORY or SEQUENTIAL
        v= min(6,int(v))
        commande = b'\xaa\x18\x01' + bytes([v, v + 0xc3])
    
#Sur le même modèle, le reste des commandes listées ici https://wiki.dfrobot.com/Voice_Module_SKU__DFR0534
#peuvent être implémentées.    
