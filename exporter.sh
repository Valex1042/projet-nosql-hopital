#!/bin/bash
# exporter.sh : exporte toutes les collections de la base hopital en JSON et CSV
# À lancer depuis la racine du projet : bash exporter.sh

BASE="hopital"
mkdir -p exports/json exports/csv

command -v mongoexport >/dev/null || {
  echo "mongoexport introuvable : sudo apt-get install -y mongodb-database-tools"; exit 1; }

# Champs exportés en CSV pour chaque collection principale
declare -A CHAMPS=(
  [patients]="code,nom,prenom,naissance,sexe,contact.telephone,contact.adresse,groupe_sanguin"
  [medecins]="matricule,nom,specialite,numero_ordre,service"
  [consultations]="code,patient_code,medecin_matricule,date_heure,motif,diagnostic,statut"
  [prescriptions]="code,consultation_code,date"
  [hospitalisations]="code,patient_code,chambre,date_admission,date_sortie_prevue,date_sortie_reelle,motif,medecin_matricule"
)

for coll in patients medecins consultations prescriptions hospitalisations; do
  echo "== $coll"
  mongoexport --db="$BASE" --collection="$coll" --jsonArray --out="exports/json/$coll.json"
  mongoexport --db="$BASE" --collection="$coll" --type=csv --fields="${CHAMPS[$coll]}" \
              --out="exports/csv/$coll.csv"
done

# Collection d'archives : n'existe qu'après un premier archivage
existe=$(mongosh --quiet "$BASE" --eval 'db.getCollectionNames().includes("prescriptions_archives")')
if [ "$existe" = "true" ]; then
  echo "== prescriptions_archives"
  mongoexport --db="$BASE" --collection=prescriptions_archives --jsonArray \
              --out="exports/json/prescriptions_archives.json"
else
  echo "(pas de collection prescriptions_archives : lancez d'abord un archivage)"
fi

echo; echo "Fichiers produits :"; ls -lh exports/json exports/csv