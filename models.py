from sqlalchemy import Boolean, Column, ForeignKey, Integer, BigInteger, String, Date
from database import Base

class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Real Information
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    email = Column(String, index=True)
    password = Column(String, index=True)
    temp_password = Column(Boolean, default=True, nullable=False, server_default="true") # Force user to change password on first login
    discord_id = Column(String, index=True, nullable=True)
    inscription_date = Column(Date, index=True, nullable=True)
    inscription_status = Column(String, index=True, nullable=True)  # valid / pending / denied

    # RP Information
    rp_first_name = Column(String, index=True, nullable=True)
    rp_last_name = Column(String, index=True, nullable=True)
    rp_birthdate = Column(Date, index=True, nullable=True)
    rp_gender = Column(String, index=True, nullable=True)
    rp_grade = Column(String, index=True, nullable=True)
    rp_affectation = Column(String, index=True, nullable=True)
    rp_qualif = Column(String, index=True, nullable=True)
    rp_nipol = Column(String, index=True, nullable=False, unique=True)
    rp_server = Column(String, index=True, nullable=True)
    rp_service = Column(String, index=True, nullable=True) # Police(PN) / Gendarmerie(GN) / Police Municipale(PM)

    # Admin
    privileges = Column(String, index=True, nullable=True) # Staff / Admin / Owner
    # Version des refresh tokens : incrémentée pour invalider tous les anciens
    token_version = Column(Integer, default=0, nullable=False, server_default="0")

class Proprietaires(Base):
    __tablename__ = "proprietaires"

    id = Column(Integer, primary_key=True, index=True)
    nom_famille = Column(String, index=True)
    nom_usage = Column(String, index=True)
    prenom = Column(String, index=True)
    second_prenom = Column(String, index=True)
    date_naissance = Column(Date, index=True)
    sexe = Column(String, index=True)
    lieu_naissance = Column(String, index=True)
    departement_naissance_numero = Column(Integer, index=True)
    adresse_numero = Column(Integer, index=True)
    adresse_type_voie = Column(String, index=True)
    adresse_nom_voie = Column(String, index=True)
    adresse_code_postal = Column(String, index=True)
    adresse_commune = Column(String, index=True)

class fnpc(Base):
    __tablename__ = "fnpc"

    # Collones Local 
    id = Column(Integer, primary_key=True, index=True)
    neph = Column(BigInteger, index=True, unique=True)
    numero_titre = Column(Integer, index=True)
    date_delivrance = Column(Date, index=True)
    prefecture_delivrance = Column(String, index=True)
    date_expiration = Column(Date, index=True)
    statut = Column(String, index=True)
    validite = Column(String, index=True)
    cat_am = Column(Boolean, index=True)
    cat_am_delivrance = Column(Date, index=True, nullable=True)
    cat_a1 = Column(Boolean, index=True)
    cat_a1_delivrance = Column(Date, index=True, nullable=True)
    cat_a2 = Column(Boolean, index=True)
    cat_a2_delivrance = Column(Date, index=True, nullable=True)
    cat_a = Column(Boolean, index=True)
    cat_a_delivrance = Column(Date, index=True, nullable=True)
    cat_b1 = Column(Boolean, index=True)
    cat_b1_delivrance = Column(Date, index=True, nullable=True)
    cat_b = Column(Boolean, index=True)
    cat_b_delivrance = Column(Date, index=True, nullable=True)
    cat_c1 = Column(Boolean, index=True)
    cat_c1_delivrance = Column(Date, index=True, nullable=True)
    cat_c = Column(Boolean, index=True)
    cat_c_delivrance = Column(Date, index=True, nullable=True)
    cat_d1 = Column(Boolean, index=True)
    cat_d1_delivrance = Column(Date, index=True, nullable=True)
    cat_d = Column(Boolean, index=True)
    cat_d_delivrance = Column(Date, index=True, nullable=True)
    cat_be = Column(Boolean, index=True)
    cat_be_delivrance = Column(Date, index=True, nullable=True)
    cat_c1e = Column(Boolean, index=True)
    cat_c1e_delivrance = Column(Date, index=True, nullable=True)
    cat_ce = Column(Boolean, index=True)
    cat_ce_delivrance = Column(Date, index=True, nullable=True)
    cat_d1e = Column(Boolean, index=True)
    cat_d1e_delivrance = Column(Date, index=True, nullable=True)
    cat_de = Column(Boolean, index=True)
    cat_de_delivrance = Column(Date, index=True, nullable=True)
    code_restriction = Column(String, index=True, nullable=True) # Ex: 01, 02, 03... (Porteur de lunettes, etc.)
    probatoire = Column(Boolean, index=True)
    date_probatoire = Column(Date, index=True, nullable=True)
    points = Column(Integer, index=True)

    # Collones Etrangères
    prop_id = Column(Integer, ForeignKey("proprietaires.id"))

class infractions_routieres(Base):
    __tablename__ = "infractions_routieres"

    id = Column(Integer, primary_key=True, index=True)
    article = Column(String, index=True, nullable=True)
    classe = Column(String, index=True)
    natinf = Column(String, index=True, nullable=True)
    points = Column(Integer, index=True)
    nipol = Column(String, index=True)
    date_infraction = Column(Date, index=True)
    details = Column(String, index=True, nullable=True)
    statut = Column(String, index=True) # en_cours / payee / annulee


    # Collones Etrangères
    neph = Column(BigInteger, ForeignKey("fnpc.neph"))

class fpr(Base):
    __tablename__ = "fpr"

    id = Column(Integer, primary_key=True, index=True)
    exactitude = Column(String, index=True, nullable=True) #? Identité confirmé, non confirmé, usurpée

    date_enregistrement = Column(Date, index=True)
    motif_enregistrement = Column(String, index=True, nullable=True)
    autorite_enregistrement = Column(String, index=True, nullable=True)
    lieu_faits = Column(String, index=True, nullable=True)
    details = Column(String, index=True, nullable=True)

    dangerosite = Column(String, index=True, nullable=True) #? Faible, moyenne, élevée
    signes_distinctifs = Column(String, index=True, nullable=True)

    conduite = Column(String, index=True, nullable=True) #? Conduite a tenir en cas de découverte


    # Clé Etrangère
    prop_id = Column(Integer, ForeignKey("proprietaires.id"))
    neph = Column(BigInteger, ForeignKey("fnpc.neph"), nullable=True) #? nullable : une FPR peut être créée sans FNPC (ex: si la personne n'a pas le permis)
    num_fijait = Column(BigInteger, nullable=True) #TODO: Faire une relation avec le FIJAIT quand créer

class siv(Base):
    __tablename__ = "siv"

    id = Column(Integer, primary_key=True, index=True)

    # Propriétaire
    prop_id = Column(Integer, ForeignKey("proprietaires.id"))
    co_prop_id = Column(Integer, ForeignKey("proprietaires.id"), nullable=True) #? Co-propriétaire, nullable si pas de co-propriétaire
    
    # Certificat d'immatriculation
    ci_etat_administratif = Column(String, index=True, nullable=True) #? (Valide, Volé, Perdu, Détruit, Annulé)
    ci_numero_immatriculation = Column(String, index=True, nullable=True)
    ci_date_premiere_circulation = Column(Date, index=True, nullable=True) #? Date de la première immatriculation du véhicule
    ci_date_certificat = Column(Date, index=True, nullable=True) #? Date de délivrance du certificat actuel

    # Véhicule
    vl_etat_administratif = Column(String, index=True, nullable=True) #? (Saisi, Mis en Fourrière, Immobilisé, Epave)
    vl_marque = Column(String, index=True, nullable=True)
    vl_denomination_commerciale = Column(String, index=True, nullable=True)
    vl_version = Column(String, index=True, nullable=True)
    vl_couleur_dominante = Column(String, index=True, nullable=True)

    # Caractéristiques techniques
    tech_puissance_kw = Column(Integer, index=True, nullable=True)
    tech_puissance_ch = Column(Integer, index=True, nullable=True)
    tech_puissance_fiscale = Column(Integer, index=True, nullable=True)
    tech_cylindree = Column(Integer, index=True, nullable=True)
    tech_carburant = Column(String, index=True, nullable=True) #? (GO, ES, EL, EE, etc.)
    tech_emissions_co2 = Column(Integer, index=True, nullable=True) #? en g/km

    tech_poids_vide = Column(Integer, index=True, nullable=True) #? Poids à vide en kg
    tech_poids_ptac = Column(Integer, index=True, nullable=True) #? PTAC en kg

    tech_places_assises = Column(Integer, index=True, nullable=True)
    tech_places_debout = Column(Integer, index=True, nullable=True)

    # Controles techniques
    ct_date_echeance = Column(Date, index=True, nullable=True) #? Date d'échéance du contrôle technique

    # Assurance
    as_assureur = Column(String, index=True, nullable=True)
    as_date_contrat = Column(Date, index=True, nullable=True)