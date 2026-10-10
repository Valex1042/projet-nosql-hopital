# agregations.py : requêtes d'agrégation et statistiques
from datetime import datetime
from pymongo.errors import PyMongoError
from config import get_db

db = get_db()


def afficher(titre, resultats):
    """Affiche proprement le résultat d'une agrégation (utile pour les captures)."""
    print("\n" + "=" * 60)
    print(titre)
    print("=" * 60)
    if not resultats:
        print("(aucun résultat)")
    for ligne in resultats:
        print(ligne)


def executer(collection, pipeline):
    """Exécute un pipeline en gérant les erreurs."""
    try:
        return list(db[collection].aggregate(pipeline))
    except PyMongoError as e:
        print("Erreur d'agrégation :", e)
        return []


# ------------------------------------------------------------------ 1
def consultations_par_specialite():
    """Nombre de consultations par spécialité, de la plus sollicitée à la moins sollicitée.
    La consultation ne contient que le matricule du médecin : on le joint avec $lookup."""
    pipeline = [
        {"$lookup": {"from": "medecins",
                     "localField": "medecin_matricule",
                     "foreignField": "matricule",
                     "as": "medecin"}},
        {"$unwind": "$medecin"},            # le lookup renvoie une liste d'un élément : on la déplie
        {"$group": {"_id": "$medecin.specialite", "nb_consultations": {"$sum": 1}}},
        {"$sort": {"nb_consultations": -1}},
        {"$project": {"_id": 0, "specialite": "$_id", "nb_consultations": 1}},
    ]
    return executer("consultations", pipeline)


# ------------------------------------------------------------------ 2
def top_motifs(limite=5):
    """Les motifs de consultation les plus fréquents."""
    pipeline = [
        {"$group": {"_id": "$motif", "total": {"$sum": 1}}},
        {"$sort": {"total": -1, "_id": 1}},          # à égalité, ordre alphabétique
        {"$limit": limite},
        {"$project": {"_id": 0, "motif": "$_id", "total": 1}},
    ]
    return executer("consultations", pipeline)


# ------------------------------------------------------------------ 3
def duree_moyenne_hospitalisation_par_motif():
    """Durée moyenne d'hospitalisation en jours, par motif.
    On utilise la sortie réelle si elle existe, sinon la sortie prévue."""
    pipeline = [
        {"$project": {
            "motif": 1,
            "jours": {"$divide": [
                {"$subtract": [{"$ifNull": ["$date_sortie_reelle", "$date_sortie_prevue"]},
                               "$date_admission"]},
                1000 * 60 * 60 * 24]},               # millisecondes -> jours
        }},
        {"$group": {"_id": "$motif",
                    "duree_moyenne_jours": {"$avg": "$jours"},
                    "nb_hospitalisations": {"$sum": 1}}},
        {"$project": {"_id": 0, "motif": "$_id",
                      "duree_moyenne_jours": {"$round": ["$duree_moyenne_jours", 1]},
                      "nb_hospitalisations": 1}},
        {"$sort": {"duree_moyenne_jours": -1}},
    ]
    return executer("hospitalisations", pipeline)


# ------------------------------------------------------------------ 4
def patients_par_groupe_et_sexe():
    """Nombre de patients par groupe sanguin et par sexe."""
    pipeline = [
        {"$group": {"_id": {"groupe": "$groupe_sanguin", "sexe": "$sexe"},
                    "nb_patients": {"$sum": 1}}},
        {"$sort": {"_id.groupe": 1, "_id.sexe": 1}},
        {"$project": {"_id": 0, "groupe": "$_id.groupe", "sexe": "$_id.sexe", "nb_patients": 1}},
    ]
    return executer("patients", pipeline)


# ------------------------------------------------------------------ 5
def consultations_du_mois_par_medecin():
    """Pour chaque médecin, son nom et son nombre de consultations du mois en cours
    (hors consultations annulées). On part de la collection medecins pour que les
    médecins sans consultation apparaissent aussi, avec 0."""
    debut = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if debut.month == 12:
        fin = debut.replace(year=debut.year + 1, month=1)
    else:
        fin = debut.replace(month=debut.month + 1)

    pipeline = [
        {"$lookup": {
            "from": "consultations",
            "let": {"mat": "$matricule"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$medecin_matricule", "$$mat"]},
                    {"$gte": ["$date_heure", debut]},
                    {"$lt": ["$date_heure", fin]},
                    {"$ne": ["$statut", "annulée"]},
                ]}}},
            ],
            "as": "consultations_mois"}},
        {"$project": {"_id": 0, "matricule": 1, "medecin": "$nom", "specialite": 1,
                      "consultations_du_mois": {"$size": "$consultations_mois"}}},
        {"$sort": {"consultations_du_mois": -1, "medecin": 1}},
    ]
    return executer("medecins", pipeline)


# ------------------------------------------------------------------ BONUS
def medicaments_les_plus_prescrits(limite=5):
    """Bonus : médicaments les plus prescrits. $unwind sur la liste imbriquée 'medicaments'."""
    pipeline = [
        {"$unwind": "$medicaments"},
        {"$group": {"_id": "$medicaments.nom", "nb_prescriptions": {"$sum": 1}}},
        {"$sort": {"nb_prescriptions": -1, "_id": 1}},
        {"$limit": limite},
        {"$project": {"_id": 0, "medicament": "$_id", "nb_prescriptions": 1}},
    ]
    return executer("prescriptions", pipeline)

# ------------------------------------------------------------------ INDEX

def creer_index():
    """Crée tous les index du projet. Relançable sans risque : un index existant n'est pas recréé."""
    # --- Index uniques : empêchent les doublons d'identifiant
    db.patients.create_index("code", unique=True)
    db.medecins.create_index("matricule", unique=True)
    db.consultations.create_index("code", unique=True)
    db.prescriptions.create_index("code", unique=True)
    db.hospitalisations.create_index("code", unique=True)

    # --- Index composé : planning d'un médecin (filtre sur le médecin, tri/période sur la date)
    db.consultations.create_index([("medecin_matricule", 1), ("date_heure", 1)],
                                  name="idx_medecin_date")
    # --- Index composé : dossier d'un patient, consultations de la plus récente à la plus ancienne
    db.consultations.create_index([("patient_code", 1), ("date_heure", -1)],
                                  name="idx_patient_date")
    # --- Index simples sur les clés de référence utilisées dans les recherches
    db.prescriptions.create_index("consultation_code")
    db.hospitalisations.create_index("patient_code")
    print("Index créés.")


def lister_index():
    """Affiche les index de chaque collection."""
    for nom in ["patients", "medecins", "consultations", "prescriptions", "hospitalisations"]:
        print(f"\n{nom} :")
        for idx in db[nom].list_indexes():
            unique = " (unique)" if idx.get("unique") else ""
            print("  -", idx["name"], dict(idx["key"]), unique)


def _etapes(plan):
    """Parcourt le plan gagnant et renvoie la liste de ses étapes (ex. ['FETCH', 'IXSCAN'])."""
    plan = plan.get("queryPlan", plan)       # MongoDB récent : le plan est parfois dans 'queryPlan'
    etapes = []
    while plan:
        etapes.append(plan["stage"])
        plan = plan.get("inputStage")
    return etapes


def expliquer(collection, filtre, tri=None, forcer_scan_complet=False, titre=""):
    """Exécute explain('executionStats') sur une requête find et affiche l'essentiel.
    forcer_scan_complet=True ignore les index (hint $natural) pour obtenir le 'sans index'."""
    commande = {"find": collection, "filter": filtre}
    if tri:
        commande["sort"] = tri
    if forcer_scan_complet:
        commande["hint"] = {"$natural": 1}
    try:
        res = db.command({"explain": commande, "verbosity": "executionStats"})
    except PyMongoError as e:
        print("Erreur explain :", e)
        return None
    stats = res["executionStats"]
    etapes = _etapes(res["queryPlanner"]["winningPlan"])
    print(f"\n--- {titre}")
    print("Étapes du plan          :", " > ".join(reversed(etapes)))
    print("Documents examinés      :", stats["totalDocsExamined"])
    print("Entrées d'index lues    :", stats["totalKeysExamined"])
    print("Documents renvoyés      :", stats["nReturned"])
    print("Temps d'exécution (ms)  :", stats["executionTimeMillis"])
    return stats


def demonstration_explain():
    """Compare la même requête avec et sans index sur la vraie collection (150 documents)."""
    filtre = {"medecin_matricule": "MED-001",
              "date_heure": {"$gte": datetime(2025, 1, 1)}}
    tri = {"date_heure": 1}
    print("\nPLANNING D'UN MÉDECIN : consultations de MED-001, triées par date")
    expliquer("consultations", filtre, tri, forcer_scan_complet=True, titre="SANS index (COLLSCAN)")
    expliquer("consultations", filtre, tri, titre="AVEC l'index idx_medecin_date (IXSCAN)")

    print("\nDOSSIER D'UN PATIENT : consultations de PAT-0001, récentes d'abord")
    filtre = {"patient_code": "PAT-0001"}
    tri = {"date_heure": -1}
    expliquer("consultations", filtre, tri, forcer_scan_complet=True, titre="SANS index")
    expliquer("consultations", filtre, tri, titre="AVEC l'index idx_patient_date")


def demonstration_gros_volume(nombre=100000):
    """Avec 150 documents, le temps est trop petit pour être mesuré. On crée donc une collection
    temporaire de 'nombre' consultations pour rendre la différence visible, puis on la supprime."""
    import random
    from datetime import timedelta
    test = db["consultations_test"]
    test.drop()
    matricules = [f"MED-{i:03d}" for i in range(1, 16)]
    maintenant = datetime.now()
    print(f"\nCréation de {nombre} consultations de test...")
    for debut in range(0, nombre, 10000):                      # insertion par paquets de 10 000
        test.insert_many([{
            "code": f"T-{debut + i:06d}",
            "patient_code": f"PAT-{random.randint(1, 60):04d}",
            "medecin_matricule": random.choice(matricules),
            "date_heure": maintenant - timedelta(minutes=random.randint(0, 600000)),
            "statut": "effectuée",
        } for i in range(10000)])

    filtre = {"medecin_matricule": "MED-001",
              "date_heure": {"$gte": maintenant - timedelta(days=30)}}
    tri = {"date_heure": 1}
    print(f"Collection de test : {test.count_documents({})} documents")
    expliquer("consultations_test", filtre, tri, titre="SANS index")
    test.create_index([("medecin_matricule", 1), ("date_heure", 1)])
    expliquer("consultations_test", filtre, tri, titre="AVEC l'index composé (médecin + date)")
    test.drop()
    print("\nCollection de test supprimée.")


"""if __name__ == "__main__":
    afficher("1. Consultations par spécialité", consultations_par_specialite())
    afficher("2. Top 5 des motifs de consultation", top_motifs())
    afficher("3. Durée moyenne d'hospitalisation par motif (jours)",
             duree_moyenne_hospitalisation_par_motif())
    afficher("4. Patients par groupe sanguin et par sexe", patients_par_groupe_et_sexe())
    afficher("5. Consultations du mois par médecin", consultations_du_mois_par_medecin())
    afficher("Bonus : médicaments les plus prescrits", medicaments_les_plus_prescrits())
"""

if __name__ == "__main__":
    creer_index()
    lister_index()
    demonstration_explain()
    demonstration_gros_volume()