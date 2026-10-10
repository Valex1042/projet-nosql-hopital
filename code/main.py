# main.py : menu principal de l'application hospitalière
from datetime import datetime

import crud
import agregations


# ---------------------------------------------------------------- OUTILS D'AFFICHAGE ET DE SAISIE

def saisir(message):
    """Demande une saisie et supprime les espaces autour."""
    return input(message).strip()


def formater(valeur):
    """Affiche les dates au format JJ/MM/AAAA HH:MM."""
    if isinstance(valeur, datetime):
        return valeur.strftime("%d/%m/%Y %H:%M")
    return valeur


def afficher_docs(docs, champs):
    """Affiche une liste de documents sur une ligne chacun, avec les champs demandés."""
    if not docs:
        print("(aucun résultat)")
        return
    for d in docs:
        print("  " + " | ".join(str(formater(d.get(c, ""))) for c in champs))
    print(f"{len(docs)} résultat(s)")


def lire_horaires():
    """Saisie de créneaux d'horaires, un par ligne : 'lundi 08:00 14:00'."""
    horaires = []
    print("Créneaux (format : jour début fin, ex. lundi 08:00 14:00). Ligne vide pour terminer.")
    while True:
        ligne = saisir("> ")
        if not ligne:
            break
        parties = ligne.split()
        if len(parties) != 3:
            print("Format invalide.")
            continue
        horaires.append({"jour": parties[0].lower(), "debut": parties[1], "fin": parties[2]})
    return horaires


def lire_medicaments():
    """Saisie de médicaments, un par ligne : 'nom ; posologie ; durée'."""
    medicaments = []
    print("Médicaments (format : nom ; posologie ; durée). Ligne vide pour terminer.")
    while True:
        ligne = saisir("> ")
        if not ligne:
            break
        parties = [p.strip() for p in ligne.split(";")]
        if len(parties) != 3:
            print("Format invalide.")
            continue
        medicaments.append({"nom": parties[0], "posologie": parties[1], "duree": parties[2]})
    return medicaments


# ---------------------------------------------------------------- PATIENTS

def menu_creer_patient():
    nom = saisir("Nom : ")
    prenom = saisir("Prénom : ")
    naissance = crud.lire_date(saisir("Date de naissance (JJ/MM/AAAA) : "))
    if naissance is None:
        print("Date invalide (format JJ/MM/AAAA).")
        return
    sexe = saisir("Sexe (F/M) : ")
    telephone = saisir("Téléphone (9 chiffres) : ")
    adresse = saisir("Adresse : ")
    groupe = saisir("Groupe sanguin (ex. O+) : ")
    saisie = saisir("Allergies (séparées par des virgules, vide si aucune) : ")
    allergies = [a.strip() for a in saisie.split(",") if a.strip()]
    crud.creer_patient(nom, prenom, naissance, sexe, telephone, adresse, groupe, allergies)


def menu_patients_par_groupe():
    groupe = saisir("Groupe sanguin : ")
    afficher_docs(crud.patients_par_groupe(groupe), ["code", "nom", "prenom", "sexe", "groupe_sanguin"])


def menu_modifier_contact():
    code = saisir("Code du patient : ")
    telephone = saisir("Nouveau téléphone (vide = inchangé) : ") or None
    adresse = saisir("Nouvelle adresse (vide = inchangée) : ") or None
    crud.modifier_contact(code, telephone, adresse)


def menu_dossier_complet():
    dossier = crud.dossier_complet(saisir("Code du patient : "))
    if not dossier:
        return
    p = dossier["patient"]
    print(f"\n{p['prenom']} {p['nom']} ({p['code']}) | né(e) le {formater(p['naissance'])[:10]} "
          f"| sexe {p['sexe']} | groupe {p['groupe_sanguin']}")
    print("Contact     :", p["contact"]["telephone"], "-", p["contact"]["adresse"])
    print("Allergies   :", ", ".join(p["allergies"]) or "aucune")
    print("Antécédents :", len(p["antecedents"]))
    for a in p["antecedents"]:
        print("   ", a)
    print(f"\nConsultations ({len(dossier['consultations'])}) :")
    afficher_docs(dossier["consultations"], ["code", "date_heure", "motif", "diagnostic", "statut"])
    print(f"\nPrescriptions ({len(dossier['prescriptions'])}) :")
    for pr in dossier["prescriptions"]:
        noms = ", ".join(m["nom"] for m in pr["medicaments"])
        print(f"  {pr['code']} | {formater(pr['date'])} | {noms}")
    print(f"\nHospitalisations ({len(dossier['hospitalisations'])}) :")
    afficher_docs(dossier["hospitalisations"],
                  ["code", "chambre", "date_admission", "date_sortie_reelle", "motif"])


# ---------------------------------------------------------------- MÉDECINS

def menu_creer_medecin():
    nom = saisir("Nom : ")
    specialite = saisir("Spécialité : ")
    numero_ordre = saisir("Numéro d'ordre : ")
    service = saisir("Service : ")
    crud.creer_medecin(nom, specialite, numero_ordre, service, lire_horaires())


def menu_medecins_par_specialite():
    specialite = saisir("Spécialité : ")
    afficher_docs(crud.medecins_par_specialite(specialite),
                  ["matricule", "nom", "specialite", "service"])


def menu_modifier_horaires():
    matricule = saisir("Matricule du médecin : ")
    crud.modifier_horaires(matricule, lire_horaires())


# ---------------------------------------------------------------- CONSULTATIONS

def menu_creer_consultation():
    patient = saisir("Code du patient : ")
    medecin = saisir("Matricule du médecin : ")
    date_heure = crud.lire_date(saisir("Date et heure (JJ/MM/AAAA HH:MM) : "), avec_heure=True)
    if date_heure is None:
        print("Date invalide (format JJ/MM/AAAA HH:MM).")
        return
    motif = saisir("Motif : ")
    crud.creer_consultation(patient, medecin, date_heure, motif)


def menu_consultations_patient():
    code = saisir("Code du patient : ")
    afficher_docs(crud.consultations_patient(code),
                  ["code", "date_heure", "medecin_matricule", "motif", "statut"])


def menu_completer_diagnostic():
    code = saisir("Code de la consultation : ")
    diagnostic = saisir("Diagnostic : ")
    crud.completer_diagnostic(code, diagnostic)


def menu_supprimer_annulees():
    if saisir("Supprimer définitivement toutes les consultations annulées ? (o/n) ").lower() == "o":
        crud.supprimer_consultations_annulees()
    else:
        print("Opération annulée.")


# ---------------------------------------------------------------- PRESCRIPTIONS

def menu_creer_prescription():
    code = saisir("Code de la consultation : ")
    crud.creer_prescription(code, lire_medicaments())


def menu_archiver_prescriptions():
    if saisir("Archiver les prescriptions de plus d'un an ? (o/n) ").lower() == "o":
        crud.archiver_prescriptions_anciennes()
    else:
        print("Opération annulée.")


# ---------------------------------------------------------------- HOSPITALISATIONS

def menu_creer_hospitalisation():
    patient = saisir("Code du patient : ")
    chambre = saisir("Chambre (ex. Ch-101) : ")
    sortie = crud.lire_date(saisir("Sortie prévue (JJ/MM/AAAA) : "))
    if sortie is None:
        print("Date invalide (format JJ/MM/AAAA).")
        return
    motif = saisir("Motif : ")
    medecin = saisir("Matricule du médecin responsable : ")
    crud.creer_hospitalisation(patient, chambre, sortie, motif, medecin)


def menu_enregistrer_sortie():
    code = saisir("Code de l'hospitalisation : ")
    texte = saisir("Date de sortie (JJ/MM/AAAA HH:MM, vide = maintenant) : ")
    date_sortie = None
    if texte:
        date_sortie = crud.lire_date(texte, avec_heure=True)
        if date_sortie is None:
            print("Date invalide.")
            return
    crud.enregistrer_sortie(code, date_sortie)


# ---------------------------------------------------------------- STATISTIQUES ET INDEX

def stat(titre, fonction):
    """Renvoie une action de menu qui exécute et affiche une agrégation."""
    return lambda: agregations.afficher(titre, fonction())


# ---------------------------------------------------------------- MENUS

def sous_menu(titre, actions, sortie="Retour"):
    """Affiche un menu numéroté et exécute l'action choisie, jusqu'à ce que l'utilisateur sorte."""
    while True:
        print(f"\n===== {titre} =====")
        for i, (libelle, _) in enumerate(actions, start=1):
            print(f"{i}. {libelle}")
        print(f"0. {sortie}")
        choix = saisir("Votre choix : ")
        if choix == "0":
            return
        if choix.isdigit() and 1 <= int(choix) <= len(actions):
            try:
                actions[int(choix) - 1][1]()
            except Exception as e:          # filet de sécurité : le menu ne doit jamais planter
                print("Erreur inattendue :", e)
        else:
            print("Choix invalide.")


def menu_principal():
    sous_menu("GESTION HOSPITALIÈRE", [
        ("Patients", lambda: sous_menu("Patients", [
            ("Créer un patient", menu_creer_patient),
            ("Patients d'un groupe sanguin", menu_patients_par_groupe),
            ("Modifier le contact d'un patient", menu_modifier_contact),
            ("Dossier complet d'un patient", menu_dossier_complet),
        ])),
        ("Médecins", lambda: sous_menu("Médecins", [
            ("Créer un médecin", menu_creer_medecin),
            ("Médecins d'une spécialité", menu_medecins_par_specialite),
            ("Modifier les horaires d'un médecin", menu_modifier_horaires),
        ])),
        ("Consultations", lambda: sous_menu("Consultations", [
            ("Créer une consultation", menu_creer_consultation),
            ("Consultations d'un patient", menu_consultations_patient),
            ("Compléter le diagnostic", menu_completer_diagnostic),
            ("Supprimer les consultations annulées", menu_supprimer_annulees),
        ])),
        ("Prescriptions", lambda: sous_menu("Prescriptions", [
            ("Créer une prescription", menu_creer_prescription),
            ("Archiver les prescriptions de plus d'un an", menu_archiver_prescriptions),
        ])),
        ("Hospitalisations", lambda: sous_menu("Hospitalisations", [
            ("Admettre un patient", menu_creer_hospitalisation),
            ("Enregistrer la sortie d'un patient", menu_enregistrer_sortie),
        ])),
        ("Statistiques", lambda: sous_menu("Statistiques", [
            ("Consultations par spécialité",
             stat("Consultations par spécialité", agregations.consultations_par_specialite)),
            ("Top 5 des motifs de consultation",
             stat("Top 5 des motifs", agregations.top_motifs)),
            ("Durée moyenne d'hospitalisation par motif",
             stat("Durée moyenne d'hospitalisation (jours)",
                  agregations.duree_moyenne_hospitalisation_par_motif)),
            ("Patients par groupe sanguin et par sexe",
             stat("Patients par groupe et par sexe", agregations.patients_par_groupe_et_sexe)),
            ("Consultations du mois par médecin",
             stat("Consultations du mois par médecin", agregations.consultations_du_mois_par_medecin)),
            ("Médicaments les plus prescrits (bonus)",
             stat("Médicaments les plus prescrits", agregations.medicaments_les_plus_prescrits)),
        ])),
        ("Index et performances", lambda: sous_menu("Index et performances", [
            ("Créer les index", agregations.creer_index),
            ("Lister les index", agregations.lister_index),
            ("Démonstration explain (150 documents)", agregations.demonstration_explain),
            ("Démonstration explain (100 000 documents)", agregations.demonstration_gros_volume),
        ])),
    ], sortie="Quitter")


if __name__ == "__main__":
    try:
        menu_principal()
    except (KeyboardInterrupt, EOFError):
        pass
    print("\nAu revoir.")