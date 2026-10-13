# docker compose exec antideepfake-server python -c "
import numpy as np
import soundfile as sf
sr = 16000
t = np.linspace(0, 10, sr * 10, False)
audio = 0.5 * np.sin(2 * np.pi * 440 * t)
sf.write('test.wav', audio, sr)
print('Created test.wav (10s sine wave)')
# "