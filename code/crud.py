# crud.py : fonctions Créer / Lire / Modifier / Supprimer
from datetime import datetime, timedelta
from pymongo.errors import PyMongoError, DuplicateKeyError
from config import get_db

db = get_db()

GROUPES_VALIDES = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


# ---------------------------------------------------------------- OUTILS COMMUNS

SEXES_VALIDES = ["F", "M"]
STATUTS_CONSULTATION = ["prévue", "effectuée", "annulée"]


def creer_index_uniques():
    """Crée les index uniques : ils garantissent qu'un code ne peut exister qu'une fois.
    Sans eux, MongoDB accepterait deux patients avec le même code."""
    db.patients.create_index("code", unique=True)
    db.medecins.create_index("matricule", unique=True)
    db.consultations.create_index("code", unique=True)
    db.prescriptions.create_index("code", unique=True)
    db.hospitalisations.create_index("code", unique=True)


def prochain_code(collection, prefixe, largeur, champ="code"):
    """Calcule le prochain code libre : PAT-0061 si le dernier est PAT-0060."""
    dernier = db[collection].find_one({}, {champ: 1}, sort=[(champ, -1)])
    numero = int(dernier[champ].split("-")[1]) + 1 if dernier else 1
    return f"{prefixe}-{numero:0{largeur}d}"


def valider_telephone(telephone):
    """Un numéro camerounais : 9 chiffres commençant par 6."""
    return telephone.isdigit() and len(telephone) == 9 and telephone.startswith("6")


def lire_date(texte, avec_heure=False):
    """Convertit '25/10/2026' (ou '25/10/2026 14:30') en datetime. Renvoie None si invalide."""
    format_date = "%d/%m/%Y %H:%M" if avec_heure else "%d/%m/%Y"
    try:
        return datetime.strptime(texte.strip(), format_date)
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------- CRÉER

def creer_patient(nom, prenom, naissance, sexe, telephone, adresse, groupe_sanguin,
                  allergies=None, antecedents=None, code=None):
    """Crée un patient. Renvoie son code, ou None en cas d'erreur.
    naissance : objet datetime. code : généré automatiquement si absent."""
    nom, prenom = (nom or "").strip(), (prenom or "").strip()
    sexe = (sexe or "").strip().upper()
    groupe_sanguin = (groupe_sanguin or "").strip().upper()
    telephone = (telephone or "").strip()

    # --- validation de la saisie
    if not nom or not prenom:
        print("Le nom et le prénom sont obligatoires.")
        return None
    if sexe not in SEXES_VALIDES:
        print(f"Sexe invalide : {sexe!r} (F ou M).")
        return None
    if groupe_sanguin not in GROUPES_VALIDES:
        print(f"Groupe sanguin invalide : {groupe_sanguin!r}.")
        return None
    if not valider_telephone(telephone):
        print("Téléphone invalide : 9 chiffres commençant par 6.")
        return None
    if not isinstance(naissance, datetime) or naissance > datetime.now():
        print("Date de naissance invalide.")
        return None

    patient = {
        "code": code.strip().upper() if code else prochain_code("patients", "PAT", 4),
        "nom": nom,
        "prenom": prenom,
        "naissance": naissance,
        "sexe": sexe,
        "contact": {"telephone": telephone, "adresse": (adresse or "").strip()},
        "groupe_sanguin": groupe_sanguin,
        "allergies": allergies or [],
        "antecedents": antecedents or [],
    }
    try:
        db.patients.insert_one(patient)
    except DuplicateKeyError:
        print(f"Le code {patient['code']} existe déjà : patient non créé.")
        return None
    except PyMongoError as e:
        print("Erreur de création :", e)
        return None
    print(f"Patient {patient['code']} créé : {prenom} {nom}.")
    return patient["code"]


def creer_medecin(nom, specialite, numero_ordre, service, horaires):
    """Crée un médecin. Renvoie son matricule, ou None en cas d'erreur."""
    nom, specialite = (nom or "").strip(), (specialite or "").strip()
    numero_ordre, service = (numero_ordre or "").strip(), (service or "").strip()
    if not (nom and specialite and numero_ordre and service):
        print("Nom, spécialité, numéro d'ordre et service sont obligatoires.")
        return None
    if not horaires:
        print("Au moins un créneau d'horaires est obligatoire.")
        return None
    for h in horaires:
        if h.get("jour") not in JOURS_VALIDES:
            print(f"Jour invalide : {h.get('jour')!r}")
            return None
    if db.medecins.count_documents({"numero_ordre": numero_ordre}, limit=1):
        print(f"Le numéro d'ordre {numero_ordre} est déjà attribué.")
        return None

    medecin = {
        "matricule": prochain_code("medecins", "MED", 3, champ="matricule"),
        "nom": nom, "specialite": specialite, "numero_ordre": numero_ordre,
        "service": service, "horaires": horaires,
    }
    try:
        db.medecins.insert_one(medecin)
    except DuplicateKeyError:
        print("Ce matricule existe déjà : médecin non créé.")
        return None
    print(f"Médecin {medecin['matricule']} créé : {nom} ({specialite}).")
    return medecin["matricule"]


def creer_consultation(patient_code, medecin_matricule, date_heure, motif, examens=None):
    """Crée une consultation 'prévue'. Vérifie que le patient et le médecin existent
    et que le médecin n'a pas déjà un rendez-vous à la même heure."""
    patient_code = (patient_code or "").strip().upper()
    medecin_matricule = (medecin_matricule or "").strip().upper()
    motif = (motif or "").strip()
    if not motif:
        print("Le motif est obligatoire.")
        return None
    if not isinstance(date_heure, datetime):
        print("Date et heure invalides.")
        return None
    if db.patients.count_documents({"code": patient_code}, limit=1) == 0:
        print(f"Patient {patient_code} introuvable.")
        return None
    if db.medecins.count_documents({"matricule": medecin_matricule}, limit=1) == 0:
        print(f"Médecin {medecin_matricule} introuvable.")
        return None
    # Même créneau déjà pris pour ce médecin ?
    if db.consultations.count_documents({"medecin_matricule": medecin_matricule,
                                         "date_heure": date_heure,
                                         "statut": {"$ne": "annulée"}}, limit=1):
        print("Ce médecin a déjà un rendez-vous à cette date et heure.")
        return None

    consultation = {
        "code": prochain_code("consultations", "CONS", 4),
        "patient_code": patient_code,
        "medecin_matricule": medecin_matricule,
        "date_heure": date_heure,
        "motif": motif,
        "diagnostic": None,
        "examens": examens or [],
        "statut": "prévue",
    }
    try:
        db.consultations.insert_one(consultation)
    except PyMongoError as e:
        print("Erreur de création :", e)
        return None
    print(f"Consultation {consultation['code']} créée pour {patient_code}.")
    return consultation["code"]


def creer_prescription(consultation_code, medicaments):
    """Crée une prescription liée à une consultation.
    medicaments : liste de {"nom": ..., "posologie": ..., "duree": ...}"""
    consultation_code = (consultation_code or "").strip().upper()
    consultation = db.consultations.find_one({"code": consultation_code})
    if consultation is None:
        print(f"Consultation {consultation_code} introuvable.")
        return None
    if consultation["statut"] != "effectuée":
        print("On ne prescrit que pour une consultation effectuée.")
        return None
    if not medicaments:
        print("La liste de médicaments est vide.")
        return None
    for m in medicaments:
        if not all(str(m.get(champ, "")).strip() for champ in ("nom", "posologie", "duree")):
            print(f"Médicament incomplet (nom, posologie et durée obligatoires) : {m}")
            return None

    prescription = {
        "code": prochain_code("prescriptions", "PRES", 4),
        "consultation_code": consultation_code,
        "medicaments": medicaments,
        "date": datetime.now(),
    }
    try:
        db.prescriptions.insert_one(prescription)
    except PyMongoError as e:
        print("Erreur de création :", e)
        return None
    print(f"Prescription {prescription['code']} créée ({len(medicaments)} médicament(s)).")
    return prescription["code"]


def creer_hospitalisation(patient_code, chambre, date_sortie_prevue, motif, medecin_matricule):
    """Admet un patient. Refuse si la chambre est occupée ou si le patient est déjà hospitalisé."""
    patient_code = (patient_code or "").strip().upper()
    medecin_matricule = (medecin_matricule or "").strip().upper()
    chambre, motif = (chambre or "").strip(), (motif or "").strip()
    if not chambre or not motif:
        print("La chambre et le motif sont obligatoires.")
        return None
    if db.patients.count_documents({"code": patient_code}, limit=1) == 0:
        print(f"Patient {patient_code} introuvable.")
        return None
    if db.medecins.count_documents({"matricule": medecin_matricule}, limit=1) == 0:
        print(f"Médecin {medecin_matricule} introuvable.")
        return None
    admission = datetime.now()
    if not isinstance(date_sortie_prevue, datetime) or date_sortie_prevue <= admission:
        print("La sortie prévue doit être postérieure à l'admission.")
        return None
    # Une hospitalisation sans date de sortie réelle est une hospitalisation en cours
    if db.hospitalisations.count_documents({"chambre": chambre, "date_sortie_reelle": None}, limit=1):
        print(f"La chambre {chambre} est déjà occupée.")
        return None
    if db.hospitalisations.count_documents({"patient_code": patient_code,
                                            "date_sortie_reelle": None}, limit=1):
        print(f"Le patient {patient_code} est déjà hospitalisé.")
        return None

    hospitalisation = {
        "code": prochain_code("hospitalisations", "HOSP", 4),
        "patient_code": patient_code,
        "chambre": chambre,
        "date_admission": admission,
        "date_sortie_prevue": date_sortie_prevue,
        "date_sortie_reelle": None,
        "motif": motif,
        "medecin_matricule": medecin_matricule,
    }
    try:
        db.hospitalisations.insert_one(hospitalisation)
    except PyMongoError as e:
        print("Erreur de création :", e)
        return None
    print(f"Hospitalisation {hospitalisation['code']} enregistrée (chambre {chambre}).")
    return hospitalisation["code"]

# ---------------------------------------------------------------- LIRE

def patients_par_groupe(groupe):
    """Renvoie la liste des patients d'un groupe sanguin donné."""
    groupe = groupe.strip().upper()
    if groupe not in GROUPES_VALIDES:
        print(f"Groupe sanguin invalide : {groupe!r}. Valeurs possibles : {GROUPES_VALIDES}")
        return []
    try:
        return list(db.patients.find({"groupe_sanguin": groupe}, {"_id": 0}))
    except PyMongoError as e:
        print("Erreur de lecture :", e)
        return []


def consultations_patient(code_patient):
    """Consultations d'un patient, de la plus récente à la plus ancienne."""
    code_patient = code_patient.strip().upper()
    if not code_patient:
        print("Le code patient est vide.")
        return []
    if db.patients.count_documents({"code": code_patient}, limit=1) == 0:
        print(f"Patient {code_patient} introuvable.")
        return []
    return list(db.consultations.find({"patient_code": code_patient}, {"_id": 0})
                .sort("date_heure", -1))


def medecins_par_specialite(specialite):
    """Médecins d'une spécialité, triés par nom."""
    specialite = specialite.strip()
    if not specialite:
        print("La spécialité est vide.")
        return []
    # Recherche insensible à la casse et aux majuscules saisies par l'utilisateur
    filtre = {"specialite": {"$regex": f"^{specialite}$", "$options": "i"}}
    resultat = list(db.medecins.find(filtre, {"_id": 0}).sort("nom", 1))
    if not resultat:
        print(f"Aucun médecin pour la spécialité {specialite!r}.")
    return resultat


def dossier_complet(code_patient):
    """Dossier complet d'un patient : infos, consultations, prescriptions, hospitalisations."""
    code_patient = code_patient.strip().upper()
    patient = db.patients.find_one({"code": code_patient}, {"_id": 0})
    if patient is None:
        print(f"Patient {code_patient} introuvable.")
        return None

    consultations = list(db.consultations.find({"patient_code": code_patient}, {"_id": 0})
                         .sort("date_heure", -1))
    # Les prescriptions sont liées aux consultations, pas directement au patient
    codes_consultations = [c["code"] for c in consultations]
    prescriptions = list(db.prescriptions.find(
        {"consultation_code": {"$in": codes_consultations}}, {"_id": 0}))
    hospitalisations = list(db.hospitalisations.find(
        {"patient_code": code_patient}, {"_id": 0}).sort("date_admission", -1))

    return {
        "patient": patient,
        "consultations": consultations,
        "prescriptions": prescriptions,
        "hospitalisations": hospitalisations,
    }


# ---------------------------------------------------------------- MODIFIER

JOURS_VALIDES = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def modifier_contact(code_patient, telephone=None, adresse=None):
    """Modifie le téléphone et/ou l'adresse d'un patient (champs imbriqués dans 'contact')."""
    code_patient = code_patient.strip().upper()
    maj = {}
    if telephone:
        telephone = telephone.strip()
        if not (telephone.isdigit() and len(telephone) == 9):
            print("Téléphone invalide : 9 chiffres attendus (ex. 699123456).")
            return False
        maj["contact.telephone"] = telephone       # notation pointée : on ne touche qu'à ce sous-champ
    if adresse and adresse.strip():
        maj["contact.adresse"] = adresse.strip()
    if not maj:
        print("Aucune valeur à modifier.")
        return False
    try:
        r = db.patients.update_one({"code": code_patient}, {"$set": maj})
    except PyMongoError as e:
        print("Erreur de modification :", e)
        return False
    if r.matched_count == 0:
        print(f"Patient {code_patient} introuvable.")
        return False
    print(f"Contact du patient {code_patient} mis à jour.")
    return True


def modifier_horaires(matricule, horaires):
    """Remplace les horaires d'un médecin.
    horaires : liste de dictionnaires {"jour": "lundi", "debut": "08:00", "fin": "14:00"}"""
    matricule = matricule.strip().upper()
    if not horaires:
        print("La liste d'horaires est vide.")
        return False
    for h in horaires:
        if h.get("jour") not in JOURS_VALIDES:
            print(f"Jour invalide : {h.get('jour')!r}")
            return False
        try:
            debut = datetime.strptime(h["debut"], "%H:%M")
            fin = datetime.strptime(h["fin"], "%H:%M")
        except (KeyError, ValueError):
            print(f"Heure invalide dans {h} (format HH:MM attendu).")
            return False
        if debut >= fin:
            print(f"L'heure de début doit précéder l'heure de fin ({h['jour']}).")
            return False
    try:
        r = db.medecins.update_one({"matricule": matricule}, {"$set": {"horaires": horaires}})
    except PyMongoError as e:
        print("Erreur de modification :", e)
        return False
    if r.matched_count == 0:
        print(f"Médecin {matricule} introuvable.")
        return False
    print(f"Horaires du médecin {matricule} mis à jour.")
    return True


def completer_diagnostic(code_consultation, diagnostic, examens=None):
    """Complète le diagnostic d'une consultation et la passe au statut 'effectuée'."""
    code_consultation = code_consultation.strip().upper()
    if not diagnostic or not diagnostic.strip():
        print("Le diagnostic est vide.")
        return False
    consultation = db.consultations.find_one({"code": code_consultation})
    if consultation is None:
        print(f"Consultation {code_consultation} introuvable.")
        return False
    if consultation["statut"] == "annulée":
        print("Impossible de compléter le diagnostic d'une consultation annulée.")
        return False
    maj = {"diagnostic": diagnostic.strip(), "statut": "effectuée"}
    if examens:
        maj["examens"] = examens
    db.consultations.update_one({"code": code_consultation}, {"$set": maj})
    print(f"Diagnostic de la consultation {code_consultation} enregistré.")
    return True


def enregistrer_sortie(code_hospitalisation, date_sortie=None):
    """Enregistre la sortie réelle d'un patient hospitalisé (date du jour par défaut)."""
    code_hospitalisation = code_hospitalisation.strip().upper()
    date_sortie = date_sortie or datetime.now()
    hosp = db.hospitalisations.find_one({"code": code_hospitalisation})
    if hosp is None:
        print(f"Hospitalisation {code_hospitalisation} introuvable.")
        return False
    if hosp.get("date_sortie_reelle") is not None:
        print("Ce patient est déjà sorti.")
        return False
    if date_sortie < hosp["date_admission"]:
        print("La date de sortie ne peut pas précéder la date d'admission.")
        return False
    db.hospitalisations.update_one({"code": code_hospitalisation},
                                   {"$set": {"date_sortie_reelle": date_sortie}})
    print(f"Sortie du patient enregistrée ({hosp['patient_code']}, chambre {hosp['chambre']}).")
    return True


# ---------------------------------------------------------------- SUPPRIMER / ARCHIVER

def supprimer_consultations_annulees():
    """Supprime définitivement les consultations au statut 'annulée'."""
    try:
        r = db.consultations.delete_many({"statut": "annulée"})
    except PyMongoError as e:
        print("Erreur de suppression :", e)
        return 0
    print(r.deleted_count, "consultation(s) annulée(s) supprimée(s).")
    return r.deleted_count


def archiver(db, collection, filtre):
    """Déplace les documents qui respectent le filtre vers <collection>_archives."""
    try:
        documents = list(db[collection].find(filtre))
        if not documents:
            print("Aucun document à archiver.")
            return 0
        for doc in documents:
            doc["date_archivage"] = datetime.now()
        db[collection + "_archives"].insert_many(documents)      # 1. copie dans les archives
        resultat = db[collection].delete_many(                   # 2. suppression de l'original
            {"_id": {"$in": [d["_id"] for d in documents]}})
    except PyMongoError as e:
        print("Erreur d'archivage :", e)
        return 0
    print(resultat.deleted_count, "document(s) archivé(s) dans", collection + "_archives")
    return resultat.deleted_count


def archiver_prescriptions_anciennes(jours=365):
    """Archive les prescriptions datant de plus d'un an (calculé par rapport à aujourd'hui)."""
    limite = datetime.now() - timedelta(days=jours)
    return archiver(db, "prescriptions", {"date": {"$lt": limite}})

# ---------------------------------------------------------------- TESTS RAPIDES

if __name__ == "__main__":
    creer_index_uniques()

    print("== Patients")
    code = creer_patient("Test", "Alice", datetime(1995, 5, 20), "F", "677123456",
                         "Akwa, Douala", "O+", allergies=["pénicilline"],
                         antecedents=[{"type": "vaccin", "nom": "COVID-19"}])
    print(db.patients.find_one({"code": code}, {"_id": 0}))
    creer_patient("Test", "Bob", datetime(1990, 1, 1), "M", "677123457",
                  "Bonanjo", "A+", code="PAT-0001")                 # doublon de code
    creer_patient("", "Bob", datetime(1990, 1, 1), "M", "677123457", "x", "A+")   # nom vide
    creer_patient("Test", "Bob", datetime(1990, 1, 1), "X", "677123457", "x", "A+")  # sexe invalide
    creer_patient("Test", "Bob", datetime(1990, 1, 1), "M", "12345", "x", "A+")   # téléphone invalide
    creer_patient("Test", "Bob", datetime(2099, 1, 1), "M", "677123457", "x", "A+")  # naissance future

    print("== Médecin")
    mat = creer_medecin("Dr Test", "Cardiologie", "ONMC-0001", "Service Cardiologie",
                        [{"jour": "lundi", "debut": "08:00", "fin": "14:00"}])
    creer_medecin("Dr Test2", "Cardiologie", "ONMC-0001", "Service Cardiologie",
                  [{"jour": "lundi", "debut": "08:00", "fin": "14:00"}])      # n° d'ordre déjà pris

    print("== Consultation")
    rdv = datetime.now() + timedelta(days=7)
    rdv = rdv.replace(hour=10, minute=0, second=0, microsecond=0)
    cons = creer_consultation(code, mat, rdv, "Contrôle de routine")
    creer_consultation(code, mat, rdv, "Contrôle de routine")               # créneau déjà pris
    creer_consultation("PAT-9999", mat, rdv, "Test")                         # patient introuvable
    creer_consultation(code, "MED-999", rdv, "Test")                         # médecin introuvable

    print("== Prescription")
    creer_prescription(cons, [{"nom": "Paracétamol", "posologie": "3 fois/jour", "duree": "5 jours"}])  # refusée : pas effectuée
    completer_diagnostic(cons, "Rien à signaler")                            # passe en 'effectuée'
    creer_prescription(cons, [{"nom": "Paracétamol", "posologie": "3 fois/jour", "duree": "5 jours"}])  # acceptée
    creer_prescription(cons, [])                                             # liste vide

    print("== Hospitalisation")
    sortie = datetime.now() + timedelta(days=5)
    hosp = creer_hospitalisation(code, "Ch-401", sortie, "Observation", mat)
    creer_hospitalisation(code, "Ch-402", sortie, "Observation", mat)        # patient déjà hospitalisé
    autre = creer_patient("Test", "Carl", datetime(1980, 3, 3), "M", "699111222", "Bali", "B+")
    creer_hospitalisation(autre, "Ch-401", sortie, "Observation", mat)       # chambre occupée