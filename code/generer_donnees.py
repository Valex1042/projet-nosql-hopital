# generer_donnees.py : génère et insère le jeu de données
import random
from datetime import datetime, timedelta
from config import get_db

MOTIFS = ["Paludisme", "Fièvre typhoïde", "Hypertension", "Diabète", "Toux persistante",
          "Douleurs abdominales", "Maux de tête", "Suivi de grossesse", "Infection urinaire",
          "Blessure", "Problème de peau", "Contrôle de routine"]
DIAGNOSTICS = ["Paludisme simple", "Typhoïde", "Hypertension artérielle", "Diabète de type 2",
               "Bronchite", "Gastrite", "Migraine", "Grossesse normale", "Infection urinaire",
               "Plaie simple", "Eczéma", "Rien à signaler"]
EXAMENS = ["Goutte épaisse", "NFS", "Glycémie", "Radiographie thoracique",
           "Échographie", "ECG", "Widal", "Analyse d'urine"]
MEDICAMENTS = [
    {"nom": "Paracétamol 500 mg", "posologie": "1 comprimé 3 fois par jour"},
    {"nom": "Amoxicilline 500 mg", "posologie": "1 gélule 2 fois par jour"},
    {"nom": "Artéméther-luméfantrine", "posologie": "4 comprimés 2 fois par jour"},
    {"nom": "Ibuprofène 400 mg", "posologie": "1 comprimé 2 fois par jour"},
    {"nom": "Metformine 500 mg", "posologie": "1 comprimé 2 fois par jour"},
    {"nom": "Amlodipine 5 mg", "posologie": "1 comprimé par jour"},
    {"nom": "Oméprazole 20 mg", "posologie": "1 gélule le matin"},
    {"nom": "Sels de réhydratation", "posologie": "1 sachet après chaque selle liquide"},
]
CHAMBRES = [f"Ch-{etage}{num:02d}" for etage in (1, 2, 3) for num in range(1, 11)]

db = get_db()

NOMS = ["Mbarga", "Ngo Bassa", "Fotso", "Atangana", "Njoya", "Ekane", "Tchoupo",
        "Bello", "Kamga", "Nkoulou", "Essomba", "Tagne"]
PRENOMS = ["Aline", "Paul", "Kevin", "Marie", "Ibrahim", "Sandra", "Rose", "Moussa",
           "Brice", "Carine", "Patrick", "Nadège"]
VILLES = ["Douala", "Yaoundé", "Bafoussam", "Garoua", "Kribi", "Buea", "Bertoua"]
GROUPES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
ALLERGIES = ["pénicilline", "arachide", "aspirine", "latex"]
SPECIALITES = ["Médecine générale", "Pédiatrie", "Cardiologie",
               "Gynécologie", "Chirurgie", "Dermatologie"]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]


def date_aleatoire(debut, fin):
    """Renvoie une date au hasard entre debut et fin."""
    ecart = (fin - debut).days
    return debut + timedelta(days=random.randint(0, ecart))


def antecedents_aleatoires():
    """Liste de sous-documents de formes variées (0 à 2 éléments)."""
    modeles = [
        lambda: {"type": "maladie_chronique", "nom": random.choice(["diabète", "hypertension", "asthme"]),
                 "depuis": random.randint(2005, 2023)},
        lambda: {"type": "chirurgie", "description": random.choice(["appendicectomie", "césarienne", "hernie"]),
                 "annee": random.randint(2000, 2024)},
        lambda: {"type": "vaccin", "nom": random.choice(["COVID-19", "hépatite B", "fièvre jaune"]),
                 "date": date_aleatoire(datetime(2018, 1, 1), datetime(2025, 12, 31))},
    ]
    return [random.choice(modeles)() for _ in range(random.randint(0, 2))]


def generer_patients(nombre):
    patients = []
    for i in range(1, nombre + 1):
        patients.append({
            "code": f"PAT-{i:04d}",
            "nom": random.choice(NOMS),
            "prenom": random.choice(PRENOMS),
            "naissance": date_aleatoire(datetime(1950, 1, 1), datetime(2020, 12, 31)),
            "sexe": random.choice(["F", "M"]),
            "contact": {"telephone": "6" + str(random.randint(50000000, 99999999)),
                        "adresse": "Quartier " + str(random.randint(1, 20)) + ", " + random.choice(VILLES)},
            "groupe_sanguin": random.choice(GROUPES),
            "allergies": random.sample(ALLERGIES, k=random.randint(0, 2)),
            "antecedents": antecedents_aleatoires(),
        })
    db.patients.delete_many({})
    db.patients.insert_many(patients)
    print(len(patients), "patients insérés")
    return patients


def generer_medecins(nombre):
    medecins = []
    for i in range(1, nombre + 1):
        jours = random.sample(JOURS, k=random.randint(3, 5))
        medecins.append({
            "matricule": f"MED-{i:03d}",
            "nom": random.choice(NOMS) + " " + random.choice(PRENOMS),
            "specialite": SPECIALITES[(i - 1) % len(SPECIALITES)],  # garantit les 6 spécialités
            "numero_ordre": f"ONMC-{random.randint(1000, 9999)}",
            "service": "Service " + SPECIALITES[(i - 1) % len(SPECIALITES)],
            "horaires": [{"jour": j, "debut": "08:00", "fin": random.choice(["14:00", "17:00"])}
                         for j in jours],
        })
    db.medecins.delete_many({})
    db.medecins.insert_many(medecins)
    print(len(medecins), "médecins insérés")
    return medecins


def generer_consultations(nombre, patients, medecins):
    """Consultations étalées de 18 mois dans le passé à 1 mois dans le futur."""
    consultations = []
    maintenant = datetime.now()
    for i in range(1, nombre + 1):
        date_heure = (maintenant + timedelta(days=random.randint(-540, 30))).replace(
            hour=random.randint(8, 16), minute=random.choice([0, 15, 30, 45]),
            second=0, microsecond=0)
        if date_heure > maintenant:
            statut = random.choices(["prévue", "annulée"], weights=[90, 10])[0]
        else:
            statut = random.choices(["effectuée", "annulée"], weights=[85, 15])[0]
        consultations.append({
            "code": f"CONS-{i:04d}",
            "patient_code": random.choice(patients)["code"],
            "medecin_matricule": random.choice(medecins)["matricule"],
            "date_heure": date_heure,
            "motif": random.choice(MOTIFS),
            "diagnostic": random.choice(DIAGNOSTICS) if statut == "effectuée" else None,
            "examens": random.sample(EXAMENS, k=random.randint(0, 2)),
            "statut": statut,
        })
    db.consultations.delete_many({})
    db.consultations.insert_many(consultations)
    print(len(consultations), "consultations insérées")
    return consultations


def generer_prescriptions(nombre, consultations):
    effectuees = [c for c in consultations if c["statut"] == "effectuée"]
    choisies = random.sample(effectuees, k=min(nombre, len(effectuees)))
    prescriptions = []
    for i, cons in enumerate(choisies, start=1):
        medicaments = []
        for med in random.sample(MEDICAMENTS, k=random.randint(1, 3)):
            medicaments.append({"nom": med["nom"],
                                "posologie": med["posologie"],
                                "duree": f"{random.choice([3, 5, 7, 10, 14])} jours"})
        prescriptions.append({
            "code": f"PRES-{i:04d}",
            "consultation_code": cons["code"],
            "medicaments": medicaments,
            "date": cons["date_heure"],
        })
    db.prescriptions.delete_many({})
    db.prescriptions_archives.delete_many({})   # repartir d'archives vides
    db.prescriptions.insert_many(prescriptions)
    print(len(prescriptions), "prescriptions insérées")
    return prescriptions


def generer_hospitalisations(nombre, patients, medecins):
    hospitalisations = []
    maintenant = datetime.now()
    for i in range(1, nombre + 1):
        admission = (maintenant - timedelta(days=random.randint(0, 400))).replace(
            hour=random.randint(7, 20), minute=0, second=0, microsecond=0)
        sortie_prevue = admission + timedelta(days=random.randint(2, 15))
        # Si la sortie prévue est passée, le patient est le plus souvent déjà sorti
        if sortie_prevue < maintenant and random.random() < 0.85:
            sortie_reelle = sortie_prevue + timedelta(days=random.randint(-1, 3))
        else:
            sortie_reelle = None
        hospitalisations.append({
            "code": f"HOSP-{i:04d}",
            "patient_code": random.choice(patients)["code"],
            "chambre": random.choice(CHAMBRES),
            "date_admission": admission,
            "date_sortie_prevue": sortie_prevue,
            "date_sortie_reelle": sortie_reelle,
            "motif": random.choice(MOTIFS),
            "medecin_matricule": random.choice(medecins)["matricule"],
        })
    db.hospitalisations.delete_many({})
    db.hospitalisations.insert_many(hospitalisations)
    print(len(hospitalisations), "hospitalisations insérées")
    return hospitalisations

if __name__ == "__main__":
    random.seed(42)  # mêmes valeurs aléatoires à chaque lancement
    patients = generer_patients(60)
    medecins = generer_medecins(15)
    consultations = generer_consultations(150, patients, medecins)
    prescriptions = generer_prescriptions(90, consultations)
    hospitalisations = generer_hospitalisations(35, patients, medecins)
    print("Génération terminée.")