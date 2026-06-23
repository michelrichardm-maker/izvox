# Configuration VB-Audio Virtual Cable

izvox utilise **deux câbles virtuels** pour rediriger l'audio entre votre micro/casque
et l'application de visioconférence (Teams, Zoom, Meet).

## 1. Installer VB-CABLE (principal)

1. Téléchargez depuis : <https://vb-audio.com/Cable/>
2. Extrayez le ZIP, clic droit sur `VBCABLE_Setup_x64.exe` → **Exécuter en tant qu'administrateur**
3. Cliquez sur **Install Driver**
4. **Redémarrez Windows** (obligatoire)

## 2. Installer VB-CABLE B (secondaire)

Pour le flux entrant (interlocuteur → vous), vous devez installer une **seconde**
instance de VB-CABLE.

1. Téléchargez **VB-CABLE A+B** depuis : <https://vb-audio.com/Cable/>
2. Lancez `VBCABLE_B_Setup_x64.exe` en administrateur
3. Cliquez sur **Install Driver**
4. **Redémarrez Windows**

À l'issue, votre liste de périphériques audio doit afficher :
- **CABLE Input (VB-Audio Virtual Cable)** — sortie
- **CABLE Output (VB-Audio Virtual Cable)** — entrée
- **CABLE-B Input (VB-Audio Cable B)** — sortie
- **CABLE-B Output (VB-Audio Cable B)** — entrée

## 3. Configurer Teams / Zoom / Meet

### Microphone (ce que l'interlocuteur entend)
Sélectionnez **CABLE Input (VB-Audio Virtual Cable)** comme micro.

> izvox prendra votre voix au micro physique, la traduira en anglais, et
> l'enverra dans CABLE Input. Teams capte CABLE Input et l'envoie à l'interlocuteur.

### Haut-parleurs (où sort la voix de l'interlocuteur)
Sélectionnez **CABLE-B Input (VB-Audio Cable B)** comme sortie audio Teams.

> Teams envoie la voix anglaise dans CABLE-B. izvox la capture (loopback),
> la traduit en français, et la joue sur vos vrais haut-parleurs.

## 4. Vérifier

```powershell
python tools\audio_diagnostic.py
```

Vous devez voir :
```
✓ Microphone par défaut: ...
✓ Haut-parleurs par défaut: ...
✓ VB-Cable Input: CABLE Input (VB-Audio Virtual Cable)
✓ VB-Cable B Loopback: CABLE-B Input (VB-Audio Cable B)
```

## 5. Test rapide

1. Lancez izvox : `scripts\run.bat`
2. Ouvrez Teams (test call ou avec un collègue)
3. Parlez en français → l'interlocuteur entend de l'anglais
4. L'interlocuteur parle en anglais → vous l'entendez en français

## Dépannage

### "VB-Cable B non trouvé"
- Vérifiez que vous avez bien installé le pack **A+B** et pas seulement le principal
- Redémarrez Windows si vous venez d'installer

### "Aucun loopback disponible"
- Le loopback WASAPI requiert Windows 10/11
- Mettez à jour Windows si vous êtes sur une ancienne version

### Echo / Larsen
- Désactivez l'amélioration audio Windows sur les périphériques VB-Cable
- Panneau de configuration → Son → clic droit sur le périphérique → Propriétés
  → Améliorations → cocher "Désactiver toutes les améliorations"
