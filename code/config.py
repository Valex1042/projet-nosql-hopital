# config est notre seul fichier qui coontient les parametres de connexion
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

MONGO_URI= "mongodb://localhost:27017/"
NOM_BASE = "hopital"

def get_db():
    """Ouvre la connexion et renvoie la base, ou arrête le programme proprement."""
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    try:
        client.admin.command("ping")
    except ServerSelectionTimeoutError:
        raise SystemExit("Impossible de joindre MongoDB : vérifiez qu'il est démarré.")
    return client[NOM_BASE]


if __name__ == "__main__":
    db = get_db()
    print("Connexion réussie à la base :", db.name)