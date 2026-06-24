# 📥 Installation détaillée d'izvox

## 1. Prérequis système

| Composant       | Minimum                          | Recommandé                     |
|-----------------|----------------------------------|--------------------------------|
| OS              | Windows 10 (64-bit)              | Windows 11                     |
| Python          | 3.10                             | 3.11 ou 3.12                   |
| RAM             | 8 GB                             | 16 GB                          |
| GPU             | Aucun (CPU possible)             | NVIDIA RTX 3060+ (12 GB VRAM)  |
| Disque          | 3 GB                             | 8 GB (modèles + cache)         |
| Connectivité    | Internet pour le 1er lancement   | Idem                           |

## 2. Installer Python 3.10+

Le script `install_windows.bat` **détecte et installe Python automatiquement
via winget** s'il manque (Windows 10 1809+ ou Windows 11). Tu peux donc passer
directement à l'étape 5 si tu veux que ça soit géré tout seul.

Sinon, en manuel :

1. Télécharger depuis <https://www.python.org/downloads/windows/>
2. Lancer l'installeur en cochant **"Add Python to PATH"**
3. Vérifier dans PowerShell :
   ```powershell
   python --version
   # Python 3.11.x ou 3.12.x
   ```

## 3. Installer VB-Audio Virtual Cable (A + B)

izvox a besoin de **deux** câbles virtuels. Voir le guide dédié :
[scripts/setup_vbcable.md](../scripts/setup_vbcable.md).

> ⚠ Redémarrez Windows après l'installation des câbles.

## 4. Récupérer izvox

```powershell
git clone https://github.com/michelrichardm-maker/izvox.git
cd izvox
```

(ou téléchargez le ZIP depuis GitHub et dézippez-le.)

## 5. Installation automatique (recommandée)

Lance depuis **n'importe quel CWD** (le script se replace tout seul à la racine
du projet) :

```powershell
# Depuis n'importe ou (le script auto-cd a la racine du projet)
C:\Saas\izvox-main\scripts\install_windows.bat

# Ou la version PowerShell, identique :
powershell -ExecutionPolicy Bypass -File C:\Saas\izvox-main\scripts\install_windows.ps1
```

Le script :
1. **Auto-cd** à la racine du projet
2. **Détecte** `python` ou `py`
3. **S'il manque**, installe Python 3.12 automatiquement via winget
4. **Refresh le PATH** dans la session courante
5. Crée le venv `venv\`
6. Installe PyTorch avec CUDA 11.8 (fallback CPU si échec)
7. Installe `requirements.txt`
8. Lance `setup_check.py`

Si winget est indisponible (vieux Windows 10), le script donne le lien
python.org avec les instructions précises.

## 6. Installation manuelle

```powershell
# 1. Environnement virtuel
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. PyTorch
# - Pour NVIDIA CUDA 11.8 :
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# - Pour AMD/Intel (DirectML) :
pip install torch torch-directml

# - Pour CPU uniquement :
pip install torch torchvision torchaudio

# 3. Dépendances
pip install -r requirements.txt

# 4. Vérification
python tools\setup_check.py
```

## 7. Pré-téléchargement des modèles (optionnel)

Les modèles se téléchargent automatiquement au premier lancement.
Pour le faire à l'avance :

```powershell
python tools\download_models.py
```

Tailles approximatives (profil balanced) :
- Whisper medium : ~1.5 GB
- NLLB-200 1.3B : ~5 GB
- Piper voices : ~120 MB
- Silero VAD : ~30 MB

## 8. Premier lancement

```powershell
.\scripts\run.bat
```

Au premier lancement, attendez-vous à 5-10 minutes pour le téléchargement
des modèles. Les lancements suivants sont quasi-instantanés.

## 9. Vérification

```powershell
python tools\setup_check.py        # Vérification globale
python tools\audio_diagnostic.py   # Périphériques audio
python tools\benchmark.py          # Latence des composants
python tools\test_translation.py   # REPL traduction
```
