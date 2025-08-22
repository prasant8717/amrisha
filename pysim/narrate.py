# generate_narration.py
from gtts import gTTS

text = (
"A venomous strike. "
"Poison begins spreading silently through the bloodstream. "
"But Amrisha is ready. "
"The smart, non-invasive wearable detects physiological signs of poisoning. "
"Amrisha deploys nanodiamonds into the bloodstream… "
"Using quantum sensing, they identify the exact toxin. "
"Then, a tailored antidote is delivered from the internal reservoir. "
"Venom neutralized. Life preserved. "
"Amrisha — smart. Quantum. Life-saving."
)
tts = gTTS(text=text, lang="en", slow=True)
tts.save("narration.wav")
print("Saved narration.wav")
