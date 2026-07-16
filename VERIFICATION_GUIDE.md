# Verifikation Guide - Blur & NSFW Detection

## 🎯 Ziel
Sicherstellen, dass Face Blur und NSFW Detection korrekt funktionieren.

---

## Option 1: Automatisierte Tests (Empfohlen)

### Voraussetzungen
```bash
pip install -r requirements.txt
# Für erweiterte Tests:
pip install pillow opencv-python requests
```

### Test ausführen
```bash
# Terminal 1: API starten
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Tests in separate Terminal
python test_blur_nsfw.py
```

**Was wird getestet:**
- ✓ Face Detection funktioniert (faces_detected > 0)
- ✓ Unterschiedliche Blur-Stärken erzeugen unterschiedliche Ergebnisse
- ✓ Intensity Levels funktionieren
- ✓ Padding Parameter funktioniert
- ✓ NSFW Detection lädt Modell
- ✓ Verschiedene Thresholds funktionieren

**Ausgabedateien (visuell überprüfen):**
- `test_blur_output_weak.png` - Blur Stärke 25
- `test_blur_output_strong.png` - Blur Stärke 100

---

## Option 2: Manuelle Tests mit echten Bildern

### A) Face Blur testen

```bash
# 1. API starten
python -m uvicorn app.main:app --reload

# 2. Mit eigenem Bild testen
# Bild sollte mindestens 1 Gesicht enthalten (z.B. portrait-photo.jpg)

curl -X POST "http://localhost:8000/faces/blur" \
  -H "X-API-Key: test-key" \
  -F "file=@your_image.jpg" \
  -F "blur_strength=25" \
  -o output_blur_25.png

curl -X POST "http://localhost:8000/faces/blur" \
  -H "X-API-Key: test-key" \
  -F "file=@your_image.jpg" \
  -F "blur_strength=100" \
  -o output_blur_100.png

# 3. Bilder vergleichen
# Öffne beide output_blur_*.png Dateien
# output_blur_100.png sollte deutlich stärker geblurrt sein!
```

**Erwartete Ergebnisse:**
- ✓ `faces_detected` > 0
- ✓ `processed_image_base64` ist nicht leer
- ✓ Output-Bilder unterscheiden sich sichtbar
- ✓ Höhere blur_strength = stärkerer Blur

### B) Padding testen

```bash
# Gleiche Stärke, aber unterschiedliches Padding
curl -X POST "http://localhost:8000/faces/blur" \
  -H "X-API-Key: test-key" \
  -F "file=@your_image.jpg" \
  -F "blur_strength=50" \
  -F "face_padding=0" \
  -o output_padding_0px.png

curl -X POST "http://localhost:8000/faces/blur" \
  -H "X-API-Key: test-key" \
  -F "file=@your_image.jpg" \
  -F "blur_strength=50" \
  -F "face_padding=30" \
  -o output_padding_30px.png

# Vergleich: Größerer Padding = größerer Blur-Bereich
```

### C) Intensity Levels testen

```bash
# Low Intensity (konservativ - nur offensichtliche Gesichter)
curl -X POST "http://localhost:8000/faces/blur" \
  -H "X-API-Key: test-key" \
  -F "file=@your_image.jpg" \
  -F "intensity=low" \
  -o output_intensity_low.png

# Medium Intensity (balanciert)
curl -X POST "http://localhost:8000/faces/blur" \
  -H "X-API-Key: test-key" \
  -F "file=@your_image.jpg" \
  -F "intensity=medium" \
  -o output_intensity_medium.png

# High Intensity (aggressiv - auch verschwommene Gesichter)
curl -X POST "http://localhost:8000/faces/blur" \
  -H "X-API-Key: test-key" \
  -F "file=@your_image.jpg" \
  -F "intensity=high" \
  -o output_intensity_high.png

# Erwartung: high sollte mehr Gesichter erkennen als low
```

### D) NSFW Detection testen

```bash
# Hinweis: Benötigt models/classifier_nsfw.onnx
# Download: https://github.com/notAI-tech/NudeNet/releases/tag/v3

# Standard Check
curl -X POST "http://localhost:8000/nsfw/check" \
  -H "X-API-Key: test-key" \
  -F "file=@your_image.jpg"

# Mit Details
curl -X POST "http://localhost:8000/nsfw/check" \
  -H "X-API-Key: test-key" \
  -F "file=@your_image.jpg" \
  -F "return_details=true"

# Erwartete Response:
# {
#   "success": true,
#   "is_nsfw": false,
#   "primary_detection": "safe",
#   "confidence": 0.95,
#   "detections": {
#     "safe": 0.95,
#     "partially_nude": 0.04,
#     "nude": 0.01
#   }
# }
```

---

## Option 3: Erweiterte Verifikation mit Python

### A) Bild-Analyse nach dem Blur

```python
from PIL import Image
import numpy as np

# Lade beide Bilder
weak_blur = Image.open('output_blur_25.png')
strong_blur = Image.open('output_blur_100.png')

# Konvertiere zu Arrays
weak_array = np.array(weak_blur)
strong_array = np.array(strong_blur)

# Berechne Bildunterschiede
difference = np.abs(weak_array.astype(float) - strong_array.astype(float)).mean()
print(f"Durchschnittlicher Unterschied zwischen Bildern: {difference:.2f}")
# Erwartung: > 5 (deutlicher Unterschied)

# Berechne Standard-Abweichung (Blur-Effekt Indikator)
weak_std = weak_array.std()
strong_std = strong_array.std()
print(f"Blur weak std: {weak_std:.2f}, Blur strong std: {strong_std:.2f}")
# Erwartung: strong_std < weak_std (mehr Blur = weniger Varianz)
```

### B) API Response Validierung

```python
import requests
import json

API_KEY = "test-key"
BASE_URL = "http://localhost:8000"

# Face Blur Test
response = requests.post(
    f"{BASE_URL}/faces/blur",
    headers={"X-API-Key": API_KEY},
    files={"file": open("your_image.jpg", "rb")},
    data={"blur_strength": 50}
)

assert response.status_code == 200, f"Expected 200, got {response.status_code}"
data = response.json()
assert data["success"] == True
assert data["faces_detected"] > 0, "Kein Gesicht erkannt!"
assert len(data["processed_image_base64"]) > 1000, "Base64 zu kurz"
print("✓ Face Blur Response korrekt")

# NSFW Detection Test
response = requests.post(
    f"{BASE_URL}/nsfw/check",
    headers={"X-API-Key": API_KEY},
    files={"file": open("your_image.jpg", "rb")},
    params={"return_details": "true"}
)

if response.status_code == 200:
    data = response.json()
    assert "is_nsfw" in data
    assert "confidence" in data
    assert "primary_detection" in data
    assert data["primary_detection"] in ["safe", "partially_nude", "nude"]
    print("✓ NSFW Detection Response korrekt")
elif response.status_code == 503:
    print("⚠ NSFW Modell nicht geladen (erwartbar wenn nicht heruntergeladen)")
```

---

## 🔍 Checkliste zur Verifizierung

### Face Blur
- [ ] API läuft ohne Fehler
- [ ] `faces_detected` > 0 für Test-Bild
- [ ] `processed_image_base64` nicht leer
- [ ] `blur_strength=25` sichtbarer als `blur_strength=100`
- [ ] Unterschiedliche `face_padding` Werte sichtbar
- [ ] `intensity=high` erkennt mehr Gesichter als `intensity=low`
- [ ] Logging zeigt: "Face blur completed - detected: X, blur_strength: Y, confidence: Z, padding: W"

### NSFW Detection
- [ ] API läuft ohne Fehler
- [ ] Response hat alle erforderlichen Felder
- [ ] `is_nsfw` ist boolean (true/false)
- [ ] `confidence` ist zwischen 0 und 1
- [ ] `primary_detection` ist eine der 3 Kategorien
- [ ] Mit `return_details=true` sind alle Kategorie-Scores vorhanden
- [ ] Verschiedene Intensitäten erzeugen unterschiedliche Ergebnisse

### Parameter
- [ ] `blur_strength` Parameter funktioniert
- [ ] `face_padding` Parameter funktioniert
- [ ] `intensity` Parameter funktioniert
- [ ] `confidence_threshold` Parameter funktioniert
- [ ] `threshold` Parameter funktioniert

---

## 📝 Test-Bilder Quelle

Für realistische Tests benötigen Sie Bilder mit:
- **Gesichter:** Porträtfotos, Gruppenfoto, etc.
- **Verschiedene Szenen:** Indoor, Outdoor, unterschiedliche Lichter
- **Verschiedene Größen:** Klein, mittel, groß

Quellen:
- Eigene Fotos
- Unsplash.com (gratis Fotos mit echten Personen)
- Pexels.com (gratis Fotos)

---

## 🚨 Häufige Probleme und Lösungen

### Problem: faces_detected = 0
**Ursache:** Gesichter nicht erkannt
**Lösungen:**
1. Überprüfen Sie `static_image_mode=True` in faces.py Zeile 22
2. Versuchen Sie `confidence_threshold=0.3` (niedrigerer Threshold)
3. Überprüfen Sie ob Bild echte Gesichter enthält (keine Zeichnungen/Cartoons)

### Problem: NSFW API antwortet 503
**Ursache:** Modell nicht heruntergeladen
**Lösung:** 
```bash
# Von GitHub herunterladen
# https://github.com/notAI-tech/NudeNet/releases/tag/v3
# Speichern in: models/classifier_nsfw.onnx
```

### Problem: Blur ist nicht sichtbar
**Ursache:** cv2.GaussianBlur wird nicht verwendet
**Lösung:**
Überprüfen Sie Zeile 131 in faces.py:
```python
blurred = cv2.GaussianBlur(face_region, (blur_k, blur_k), 0)  # RICHTIG
# NICHT: blurred = cv2.blur(face_region, (blur_k, blur_k))
```

### Problem: API antwortet 422 Validation Error
**Ursache:** Parameter Typ falsch
**Lösung:**
- `blur_strength`: integer (z.B. 25, nicht "25")
- `face_padding`: integer
- `confidence_threshold`: float (0.0 - 1.0)
- `intensity`: string ("low", "medium", "high")

---

## 📊 Performance & Logs überprüfen

### Logs ansehen
```bash
# Terminal mit API, Ctrl+Shift+K um Logs zu sehen
# Oder in Python:
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Expected Log Output:**
```
DEBUG - Face blur request - intensity: None, blur_strength: 50, face_padding: 10
DEBUG - Image validated - size: (1024, 768)
INFO - Face blur completed - detected: 3, blur_strength: 51, confidence: 0.5, padding: 10
```

### Performance messen
```bash
# Zeit messen
time curl -X POST "http://localhost:8000/faces/blur" \
  -H "X-API-Key: test-key" \
  -F "file=@image.jpg" \
  -o /dev/null

# Erwartung: < 2 Sekunden für 1024x768 Bild
```

---

## ✅ Tests bestanden?

Wenn Sie alle Punkte der Checkliste abhaken konnten, ist die Implementierung korrekt! 🎉

Falls nicht, überprüfen Sie:
1. Logs auf Fehler
2. Dass alle Dependencies installiert sind
3. Dass die richtige Python/API Version läuft
