import math

class Biquad():
    def __init__(self, biquadType, fc, q, peakGainDB):
        self.a0 = 0
        self.a1 = 0
        self.a2 = 0
        self.b1 = 0
        self.b2 = 0
        self.z1 = 0
        self.z2 = 0
        self.setBiquad(biquadType, fc, q, peakGainDB)
    
    def clip(self, x, minimum, maximum):
        return max(minimum, min(x, maximum))

    def setBiquad(self, biquadType, fc, q, peakGainDB) :
        self.Fc = self.clip(fc, 0, 0.5)
        self.type = biquadType
        self.Q = q
        self.Fc = fc
        self.peakGain = peakGainDB
        self.calcBiquad()

    def calcBiquad(self):
        norm = 0
        V = pow(10, math.fabs(self.peakGain) / 20.0)
        K = math.tan(math.pi * self.Fc)
        if self.type == 0:  #lowpass
            norm = 1 / (1 + K / self.Q + K * K)
            self.a0 = K * K * norm
            self.a1 = 2 * self.a0
            self.a2 = self.a0
            self.b1 = 2 * (K * K - 1) * norm
            self.b2 = (1 - K / self.Q + K * K) * norm

        elif self.type == 1: #highpass:
            norm = 1 / (1 + K / self.Q + K * K)
            self.a0 = 1 * norm
            self.a1 = -2 * self.a0
            self.a2 = self.a0
            self.b1 = 2 * (K * K - 1) * norm
            self.b2 = (1 - K / self.Q + K * K) * norm

        elif self.type == 2: #bandpass:
            norm = 1 / (1 + K / self.Q + K * K)
            self.a0 = K / self.Q * norm
            self.a1 = 0
            self.a2 = -self.a0
            self.b1 = 2 * (K * K - 1) * norm
            self.b2 = (1 - K / self.Q + K * K) * norm

        elif self.type == 3: #notch:
            norm = 1 / (1 + K / self.Q + K * K)
            self.a0 = (1 + K * K) * norm
            self.a1 = 2 * (K * K - 1) * norm
            self.a2 = self.a0
            self.b1 = self.a1
            self.b2 = (1 - K / self.Q + K * K) * norm

        elif self.type == 4: #peak:
            if (self.peakGain >= 0):    # boost
                norm = 1 / (1 + 1/self.Q * K + K * K)
                self.a0 = (1 + V/self.Q * K + K * K) * norm
                self.a1 = 2 * (K * K - 1) * norm
                self.a2 = (1 - V/self.Q * K + K * K) * norm
                self.b1 = self.a1
                self.b2 = (1 - 1/self.Q * K + K * K) * norm
            else:   # cut
                norm = 1 / (1 + V/self.Q * K + K * K)
                self.a0 = (1 + 1/self.Q * K + K * K) * norm
                self.a1 = 2 * (K * K - 1) * norm
                self.a2 = (1 - 1/self.Q * K + K * K) * norm
                self.b1 = self.a1
                self.b2 = (1 - V/self.Q * K + K * K) * norm
        elif self.type == 5: #lowshelf:
            if (self.peakGain >= 0):   # boost
                norm = 1 / (1 + math.sqrt(2) * K + K * K)
                self.a0 = (1 + math.sqrt(2*V) * K + V * K * K) * norm
                self.a1 = 2 * (V * K * K - 1) * norm
                self.a2 = (1 - math.sqrt(2*V) * K + V * K * K) * norm
                self.b1 = 2 * (K * K - 1) * norm
                self.b2 = (1 - math.sqrt(2) * K + K * K) * norm
            else:    # cut
                norm = 1 / (1 + math.sqrt(2*V) * K + V * K * K)
                self.a0 = (1 + math.sqrt(2) * K + K * K) * norm
                self.a1 = 2 * (K * K - 1) * norm
                self.a2 = (1 - math.sqrt(2) * K + K * K) * norm
                self.b1 = 2 * (V * K * K - 1) * norm
                self.b2 = (1 - math.sqrt(2*V) * K + V * K * K) * norm
        elif self.type == 6: #highshelf:
            if (self.peakGain >= 0):   # boost
                norm = 1 / (1 + math.sqrt(2) * K + K * K)
                self.a0 = (V + math.sqrt(2*V) * K + K * K) * norm
                self.a1 = 2 * (K * K - V) * norm
                self.a2 = (V - math.sqrt(2*V) * K + K * K) * norm
                self.b1 = 2 * (K * K - 1) * norm
                self.b2 = (1 - math.sqrt(2) * K + K * K) * norm
            else:    # cut
                norm = 1 / (V + math.sqrt(2*V) * K + K * K)
                self.a0 = (1 + math.sqrt(2) * K + K * K) * norm
                self.a1 = 2 * (K * K - 1) * norm
                self.a2 = (1 - math.sqrt(2) * K + K * K) * norm
                self.b1 = 2 * (K * K - V) * norm
                self.b2 = (V - math.sqrt(2*V) * K + K * K) * norm

    def compute(self,i):
        out = i * self.a0 + self.z1
        self.z1 = i * self.a1 + self.z2 - self.b1 * out
        self.z2 = i * self.a2 - self.b2 * out
        return out