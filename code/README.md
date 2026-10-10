# Projet 1 : Système de gestion hospitalière (MongoDB + Python)

Matière : Du SQL au NoSQL | Enseignant : FOTSO T. Valdez W.
Groupe : Groupe 1 | Filière-Niveau : SDIA-4

Membre : DJIOGAP NDONTCHIO BEAUDRICK VALEX (25G01393)

## 1. Prérequis
- Python 3.8 ou plus récent
- MongoDB Community Server (local, port 27017) démarré
- MongoDB Database Tools (`mongoexport`, `mongoimport`)

## 2. Installation
```bash
cd code
python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
```
La connexion (adresse et nom de la base `hopital`) se règle uniquement dans `config.py`.

## 3. Lancement

### Option A : réimporter les données exportées (recommandé pour tester)
Depuis le dossier qui contient `exports/` :
```bash
for f in exports/json/*.json; do
  c=$(basename "$f" .json)
  mongoimport --db=hopital --collection="$c" --jsonArray --drop --file="$f"
done
cd code
python -c "import agregations; agregations.creer_index()"   # recrée les index (non inclus dans les exports JSON)
python main.py
```

### Option B : régénérer les données
```bash
cd code
python generer_donnees.py       # génère et insère le jeu de données (graine fixe : random.seed(42))
python main.py
```

## 4. Organisation du code
| Fichier | Rôle |
|---|---|
| `config.py` | Connexion à MongoDB (seul fichier à modifier) |
| `generer_donnees.py` | Génère 60 patients, 15 médecins, 150 consultations, 90 prescriptions, 35 hospitalisations |
| `crud.py` | Créer, lire, modifier, supprimer et archiver, avec gestion des erreurs |
| `agregations.py` | 5 agrégations (+1 bonus), index et démonstration `explain` |
| `main.py` | Menu principal |

## 5. Modélisation (résumé)
- `patients` : allergies et antécédents **imbriqués**
- `medecins` : horaires **imbriqués**
- `consultations` : collection séparée, références `patient_code` et `medecin_matricule`
- `prescriptions` : médicaments imbriqués, référence `consultation_code`
- `hospitalisations` : collection séparée, références patient et médecin
- `prescriptions_archives` : prescriptions de plus d'un an (archivage au lieu de suppression)

## 6. Index
Uniques sur `code` / `matricule` ; composés `(medecin_matricule, date_heure)` et
`(patient_code, date_heure)` sur `consultations`.

## 7. Exports
`exports/json/` : un fichier par collection (contenu complet, réimportable).
`exports/csv/` : collections principales (format plat : listes et sous-documents non inclus).