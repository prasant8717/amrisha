from gtts import gTTS

text = """
A venomous snake strikes...
venom spreads rapidly through the bloodstream...
But Amrisha is ready.
The wearable device detects the bite instantly... activating advanced quantum sensors.
Within seconds... therapeutic pulses neutralize venom molecules at the source.
Life is saved — without delay.
Amrisha... the future of universal antivenom.
"""

tts = gTTS(text=text, lang="en", slow=True)
tts.save("amrisha.wav")
print("Narration audio saved as amrisha.wav")
