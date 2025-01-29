# Importer les modules nécéssaires
import tkinter as tk
import cv2
import numpy as np
from tkinter import filedialog, Toplevel
from PIL import Image, ImageTk
import os
import csv
import subprocess
from datetime import datetime
from tkinter import simpledialog, messagebox
import shutil
import threading
import random


# Initialiser la fenêtre Tkinter
fenetre = tk.Tk()

# Mettre le titre de la fenêtre et spécifier sa taille
fenetre.title("Suite BeProAct")

fenetre.geometry("1000x800") 


# Déterminer le répertoire du script en cours
script_dir = os.path.dirname(os.path.abspath(__file__))
       
default_directory = os.path.join(script_dir, "projets")  # Dossier "projets" à côté du script

# Vérification et création du dossier "Projets" au démarrage si non existant
if not os.path.exists(default_directory):
    os.makedirs(default_directory)
    print("Dossier 'projets' créé")
else:
    print("Dossier 'projets' déjà existant")



####variablles globales####

# Variables d'état du projet (aucun projet ouvert par défaut)
current_directory = default_directory # Dossier actuel qui sera mis à jour au fur et à mesure
projet_ouvert = False # Indiquer si un projet est ouvert ou non
mesure_ouvert = False # Indiquer si une mesure est ouverte ou non

# Contient le nom du projet/mesure/rapport défaut actuel
nom_projet_ouvert = "projets" 
nom_mesure_ouvert = "projets"
nom_fichier_csv = "projets" 


# Nombre de chiffres après la virgule pour les données enregistrées
precision = 2 


image_path = "Photos/fissure2.jpeg"  # Contient le chemin de l'image à analyser par défaut

defects_data = []  # Liste pour stocker les données des défauts

# Fonction pour calculer la largeur maximale réelle d'une fissure
def calculate_max_width(contour):
    max_width = 0
    for i in range(len(contour)):
        for j in range(i + 1, len(contour)):
            # Calculer la distance entre deux points du contour
            distance = cv2.norm(contour[i][0] - contour[j][0])
            max_width = max(max_width, distance)
    return max_width


# Fonction de détection des fissures (développé par Jules et intégré à l'interface)
def detectionFissure():
    global image_path, defects_data
    # Chemin de l'image
    image = cv2.imread(image_path)

    # Vérifier si l'image a été correctement chargée
    if image is None:
        print("Erreur : Impossible de charger l'image. Vérifiez le chemin.")
        return

    # Convertir l'image en niveaux de gris
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Appliquer CLAHE pour améliorer le contraste
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_image = clahe.apply(gray_image)

    # Créer un détecteur de QR code
    qr_detector = cv2.QRCodeDetector()

    # Détecter et décoder le QR code
    data, points, _ = qr_detector.detectAndDecode(image)

    if points is not None:
        # Convertir les points en entiers
        points = points[0].astype(int)

        # Extraire les coordonnées des coins du QR code
        top_left, top_right, bottom_right, bottom_left = points

        # Tracer un rectangle autour du QR code
        cv2.polylines(image, [points], isClosed=True, color=(0, 255, 0), thickness=2)

        # Définir l'origine du repère comme le coin inférieur gauche du QR code
        origin = tuple(bottom_left)

        # Tracer les axes du plan orthonormé
        cv2.arrowedLine(image, origin, (origin[0] + 100, origin[1]), (255, 0, 0), 2, tipLength=0.2)  # Axe X (rouge)
        cv2.arrowedLine(image, origin, (origin[0], origin[1] - 100), (0, 0, 255), 2, tipLength=0.2)  # Axe Y (bleu)

        # Calculer la conversion pixel -> cm (QR code = 13 cm dans la vraie vie)
        qr_width_px = np.linalg.norm(top_right - top_left)
        pixel_to_cm = 13 / qr_width_px
        print(f"Conversion pixel -> cm : {pixel_to_cm:.4f} cm/px")

        # Appliquer un flou pour réduire le bruit
        blurred_image = cv2.GaussianBlur(gray_image, (5, 5), 0)

        # Appliquer un seuillage global pour détecter les défauts sombres
        threshold_value = int(np.mean(gray_image) * 0.4)
        _, binary_image = cv2.threshold(blurred_image, threshold_value, 255, cv2.THRESH_BINARY_INV)

        # Trouver les contours
        contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Copier l'image originale pour dessiner les contours fusionnés
        output_image = image.copy()

        # Convertir les points du QR code en float32 pour compatibilité avec pointPolygonTest
        qr_contour = np.array(points, dtype=np.float32)

        # Traiter chaque défaut détecté
        min_contour_area = 500  # Seuil pour ignorer les petits contours
        defect_count = 0  # Compteur de défauts valides
        for i, contour in enumerate(contours):
            if cv2.contourArea(contour) > min_contour_area:
                # Vérifier si le défaut est dans la zone du QR code en testant plusieurs points du contour
                inside_qr = False
                for point in contour:
                    px, py = map(float, point[0])  # Assurez-vous que px et py sont de type float
                    if cv2.pointPolygonTest(qr_contour, (px, py), False) >= 0:
                        inside_qr = True
                        break
                
                if inside_qr:
                    continue  # Ignorer ce défaut

                # Calculer la boîte englobante
                x, y, w, h = cv2.boundingRect(contour)

                # Incrémenter le compteur de défauts valides
                defect_count += 1

                # Calculer les dimensions et la position
                defect_position_px = (x, y)
                defect_position_cm = ((x - origin[0]) * pixel_to_cm, (origin[1] - y) * pixel_to_cm)
                max_width_px = calculate_max_width(contour)
                width_cm = max_width_px * pixel_to_cm
                height_cm = h * pixel_to_cm

                # Colorier l'intérieur du défaut
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                cv2.drawContours(output_image, [contour], -1, color, thickness=cv2.FILLED)

                # Annoter l'image avec les informations
                info_text = f"Defaut {defect_count}: {width_cm:.2f}x{height_cm:.2f} cm"
                cv2.putText(output_image, info_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                # Enregistrer dans la liste des défauts les informations de chaque défauts
                # On caste en float et on arrondit au centième (precision = 2)  
                defects_data.append([
                    defect_count,
                    (float(round(defect_position_px[0], precision)), float(round(defect_position_px[1], precision))),
                    (float(round(defect_position_cm[0], precision)), float(round(defect_position_cm[1], precision))),
                    float(round(width_cm, precision)),
                    float(round(height_cm, precision))
                ])

                # Afficher les informations dans la console
                print(f"Defaut {defect_count}:")
                print(f"  - Position (px): {defect_position_px}")
                print(f"  - Position (cm): ({defect_position_cm[0]:.2f}, {defect_position_cm[1]:.2f})")
                print(f"  - Dimensions (cm): {width_cm:.2f} x {height_cm:.2f}")

        # Afficher le nombre total de défauts détectés
        print(f"Nombre total de défauts détectés: {defect_count}")

    else:
        print("Aucun QR Code détecté.")
        return
    
    # Enregistrer ou afficher l'image
    output_path = "output_with_colored_defects.jpg"
    cv2.imwrite(output_path, output_image)
    print(f"Image annotée enregistrée sous : {output_path}")
    
    # Redimensionner l'image pour qu'elle tienne dans la fenêtre
    max_width = 800  # Largeur maximale
    max_height = 600  # Hauteur maximale
    
    height, width = output_image.shape[:2]
    
    # Calculer le facteur de redimensionnement en fonction de la taille maximale
    scaling_factor = min(max_width / width, max_height / height)
    
    # Appliquer le redimensionnement si nécessaire
    if scaling_factor < 1:
        output_image = cv2.resize(output_image, (int(width * scaling_factor), int(height * scaling_factor)))
    # Affichage (optionnel)
    cv2.imshow("Image avec repere et defauts", output_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Fonction pour lancer la fonction de détection dans un thread
def start_detection_thread():
    try:
        # Lancer la fonction dans un thread séparé
        detection_thread = threading.Thread(target=detectionFissure)
        detection_thread.daemon = True  # Permet de terminer le thread lorsque le programme principal se ferme
        detection_thread.start()
    except Exception as e:
        messagebox.showerror("Erreur", f"Une erreur est survenue : {e}")

# Fonction pour afficher le logo de la fenêtre Tkinter
def afficher_logo():
    try:
        # Charger l'image d'icône
        chemin_icone = "logoPolytech.ico"
        icone = ImageTk.PhotoImage(file=chemin_icone)
        fenetre.iconphoto(False, icone)  # Définir l'icône de la fenêtre
    except Exception as e:
        print(f"Erreur lors du chargement de l'icône : {e}")
        

# Fonction pour vérifier si un dossier est un projet valide
def verifier_projet(dossier):
    # Vérifier si un fichier "beproact_config" existe dans le dossier
    fichier_projet = os.path.join(dossier, "beproact_config")
    return os.path.isfile(fichier_projet)

# Fonction pour ouvrir un projet
def ouvrir_projet():
    global projet_ouvert, mesure_ouvert, nom_projet_ouvert, nom_mesure_ouvert, current_directory
    
    projet_ouvert = True
    mesure_ouvert = False
    
    # Ouvrir une boîte de dialogue pour sélectionner un dossier
    dossier_selectionne = filedialog.askdirectory(title="Sélectionnez un projet", initialdir=default_directory)
   
    # Vérifier si un dossier a été sélectionné
    if not dossier_selectionne:
        messagebox.showwarning("Avertissement", "Aucun dossier sélectionné. Veuillez sélectionner un projet.")
        return
    
    if not verifier_projet(dossier_selectionne):
        messagebox.showerror("Erreur", f"Le dossier sélectionné ('{dossier_selectionne}') n'est pas un projet valide.")
        return
    
    # Mettre à jour le répertoire actuel et le nom du projet
    current_directory = dossier_selectionne
    nom_projet_ouvert = os.path.basename(dossier_selectionne)  # Extraire le nom du dossier
    print(f"Le répertoire actuel est: {current_directory}")
    
    messagebox.showinfo("Succès", f"Projet ouvert : {nom_projet_ouvert}")
    
    print("Projet ouvert")
    
    menu_fichier.entryconfig("Fermer projet", state="normal")
    menu_fichier.entryconfig("Ouvrir projet", state="disabled")
    menu_fichier.entryconfig("Nouvelle mesure", state="normal")
    menu_fichier.entryconfig("Nouveau projet", state="disabled")
    menu_fichier.entryconfig("Modifier une mesure", state="normal")
    
    # Mettre à jour le label du projet et mesure pour indiquer à l'utilisateur sur quel projet il se trouve
    # et quelle campagne de mesure est ouverte
    update_projet_mesure_label()
    
    # Activer les boutons et autres actions si nécéssaire
    activer_boutons()


# Fonction pour quitter le projet
def quitter_projet():
    global projet_ouvert,mesure_ouvert, nom_mesure_ouvert, nom_projet_ouvert
    
    if projet_ouvert:
        # Mettre à jour les variables d'état de l'interface
        projet_ouvert = False 
        mesure_ouvert = False
        nom_projet_ouvert = None
        nom_mesure_ouvert = None
        activer_boutons()
        update_projet_mesure_label()
        print("Projet fermé")
        menu_fichier.entryconfig("Fermer projet", state="disabled")
        menu_fichier.entryconfig("Ouvrir projet", state="normal")
        menu_fichier.entryconfig("Nouveau projet", state="normal")
        menu_fichier.entryconfig("Nouvelle mesure", state="disabled")
        

# Fonction pour créer un nouveau projet
def nouveau_projet():
    global projet_ouvert, mesure_ouvert, nom_projet_ouvert, nom_mesure_ouvert, current_directory
    
    # Ouvrir le gestionnaire de fichiers pour sélectionner ou créer un dossier
    dossier_projet = filedialog.asksaveasfilename(
        title="Créer un nouveau projet",
        filetypes=[("Dossier", "")],
        initialdir=default_directory  # Répertoire par défaut
    )
    
    if dossier_projet:
        # Créer le dossier si ce n'est pas déjà fait
        if not os.path.exists(dossier_projet):
            os.makedirs(dossier_projet)
            print(f"Nouveau projet créé dans : {dossier_projet}")
        else:
            print("Ce dossier existe déjà.")
        
        # Créer un fichier vide nommé 'beproact_config' dans le dossier généré
        chemin_fichier_config = os.path.join(dossier_projet, "beproact_config")
        with open(chemin_fichier_config, "w") as fichier:
            pass  # Le fichier est créé vide

        print(f"Fichier 'beproact_config' créé dans : {chemin_fichier_config}")
        
        # Mettre à jour le répertoire actuel et le nom du projet
        current_directory = dossier_projet
        nom_projet_ouvert = os.path.basename(dossier_projet)  # Extraire le nom du dossier
        print(f"Le répertoire actuel est: {current_directory}")
        
        projet_ouvert = True
        mesure_ouvert = False
        
        # Mettre à jour le label du projet et mesure pour indiquer à l'utilisateur sur quel projet il se trouve
        # et quelle campagne de mesure est ouverte
        update_projet_mesure_label()
        
        # Mettre à jour l'état des boutons du menu fichier pour empêcher l'utilisateur de faire n'importe quoi
        menu_fichier.entryconfig("Nouveau projet", state="disabled")
        menu_fichier.entryconfig("Ouvrir projet", state="disabled")
        menu_fichier.entryconfig("Fermer projet", state="normal")
        menu_fichier.entryconfig("Nouvelle mesure", state="normal")
        
        messagebox.showinfo("Nouveau projet créé avec succès", f"Projet ouvert : {nom_projet_ouvert}")


#Fonction pour créer une nouvelle mesure
def nouvelle_mesure():
    global projet_ouvert, mesure_ouvert, nom_projet_ouvert, nom_mesure_ouvert, current_directory, nom_fichier_csv
    print("Nouvelle mesure!")
    
    # Demander à l'utilisateur une date
    while True:
        date_mesure = simpledialog.askstring(
            "Nouvelle mesure", 
            "Entrez la date de la mesure (format: DD-MM-YYYY) :"
        )
        if not date_mesure:
            messagebox.showinfo("Annulé", "Opération annulée.")
            return

        # Vérifier le format de la date
        try:
            datetime.strptime(date_mesure, "%d-%m-%Y")  # Valider le format
            break  # La date est valide, on peut continuer
        except ValueError:
            messagebox.showerror("Erreur", "Date invalide. Veuillez entrer une date au format DD-MM-YYYY.")
    
    # Création du sous-dossier avec le nom du projet courant et la date
    nom_projet = os.path.basename(current_directory)  # Récupérer le nom du projet
    nom_sous_dossier = f"{nom_projet}_{date_mesure}"  # Nom du sous-dossier
    chemin_sous_dossier = os.path.join(current_directory, nom_sous_dossier)


    if not os.path.exists(chemin_sous_dossier):
        os.makedirs(chemin_sous_dossier)
        print(f"Sous-dossier créé : {chemin_sous_dossier}")
        
        # Création des répertoires intermédiaires "données brutes" et "resultats"
        donnees_brutes = os.path.join(chemin_sous_dossier, "donnees brutes")
        resultat = os.path.join(chemin_sous_dossier, "resultats")
        os.makedirs(donnees_brutes, exist_ok=True)
        os.makedirs(resultat, exist_ok=True)
        print(f"Répertoires intermédiaires créés : 'donnees brutes' et 'resultats'")

        # Création du sous-dossier "images_defauts" dans "données brutes"
        chemin_images_defauts = os.path.join(donnees_brutes, "images_defauts")
        os.makedirs(chemin_images_defauts, exist_ok=True)
        print(f"Sous-dossier créé : {chemin_images_defauts}")

        # Création des sous-dossiers "fichiers_meshroom" et "fichiers_blender" dans "resultats"
        sous_dossiers_resultats = ["fichiers_meshroom", "fichiers_blender"]
        for sous_dossier in sous_dossiers_resultats:
            chemin_complet = os.path.join(resultat, sous_dossier)
            os.makedirs(chemin_complet, exist_ok=True)
            print(f"Sous-dossier créé : {chemin_complet}")

        # Création du fichier CSV dans "resultat"
        nom_fichier_csv = f"rapport_defauts_{nom_sous_dossier}.csv"
        chemin_fichier_csv = os.path.join(resultat, nom_fichier_csv)
        with open(chemin_fichier_csv, 'w') as fichier_csv:
            fichier_csv.write("Date,Description,Statut\n")  # Écriture d'un en-tête par défaut
            print(f"Fichier CSV créé : {chemin_fichier_csv}")
    else:
        print(f"Le sous-dossier existe déjà : {chemin_sous_dossier}")
    
    messagebox.showinfo("Succès", f"Sous-dossier '{nom_sous_dossier}' créé avec succès.")
    
    # Mettre à jour la variable 'nom_mesure_ouvert' avec le nom du sous-dossier
    nom_mesure_ouvert = nom_sous_dossier
    mesure_ouvert = True

    # Mettre à jour current_directory pour pointer vers le nouveau sous-dossier horodaté
    current_directory = chemin_sous_dossier
    print(f"Répertoire actuel mis à jour : {current_directory}")
    
    menu_fichier.entryconfig("Nouvelle mesure", state="disabled")
    menu_fichier.entryconfig("Modifier une mesure", state="disabled")
    
    #Activer les boutons car on est dans une campagne de mesure et on peut commencer à analyser les défauts
    activer_boutons()
    
    # Mettre à jour le label du projet et mesure pour indiquer à l'utilisateur sur quel projet il se trouve
    # et quelle campagne de mesure est ouverte
    update_projet_mesure_label()

    
# Fonction qui permet de sélectionner une image dans le dossier images_défauts des données brutes
def select_image():
    global current_directory, image_path

    # Vérifier que le projet actuel est défini / Utile si on n'a pas désactivé le bouton Détecter les défauts
    if not current_directory:
        messagebox.showerror("Erreur", "Aucun projet actif. Veuillez ouvrir ou créer un projet avant de sélectionner une image.")
        return

    # Déterminer le chemin du sous-dossier 'données brutes/images_defauts' dans la mesure actuelle
    sous_dossier_images = os.path.join(current_directory, "donnees brutes", "images_defauts")

    # Vérifier que le sous-dossier 'images_defauts' existe
    if not os.path.exists(sous_dossier_images):
        messagebox.showerror("Erreur", f"Le sous-dossier 'images_defauts' est introuvable dans {current_directory}.")
        return

    # Ouvrir une boîte de dialogue pour sélectionner une image
    chemin_image_selectionnee = filedialog.askopenfilename(
        title="Sélectionnez une image",
        filetypes=[("Fichiers image", "*.jpeg *.jpg *.png")],
        initialdir=sous_dossier_images
    )

    # Vérifier si une image a été sélectionnée
    if not chemin_image_selectionnee:
        messagebox.showinfo("Annulé", "Aucune image sélectionnée.")
        return
    else:
        # Mettre à jour la variable globale image_path
        image_path = chemin_image_selectionnee
        messagebox.showinfo("Succès", f"Image sélectionnée : {image_path}")
        start_detection_thread()


# Fonction pour modifier une mesure déjà existante 
def modifier_mesure():
    
    global projet_ouvert, mesure_ouvert, nom_projet_ouvert, nom_mesure_ouvert, current_directory, nom_fichier_csv
    
    #Vérifier qu'une mesure et un projet est ouvert / utile si on décide de ne pas désactiver le bouton modifier Mesure 
    if not projet_ouvert or not current_directory:
        messagebox.showwarning("Avertissement", "Aucun projet ouvert. Veuillez d'abord ouvrir un projet.")
        return

    # Ouvrir une boîte de dialogue pour sélectionner un dossier horodaté
    dossier_mesure = filedialog.askdirectory(
        title="Sélectionnez une mesure existante",
        initialdir=current_directory
    )

    # Vérifier si un dossier a été sélectionné
    if not dossier_mesure:
        messagebox.showinfo("Annulé", "Aucun dossier sélectionné. Opération annulée.")
        return

    
    # Vérifier si le dossier sélectionné appartient bien au projet courant
    nom_projet = os.path.basename(current_directory)
    if not os.path.basename(dossier_mesure).startswith(nom_projet + "_"):
       messagebox.showerror(
           "Erreur",
           f"Le dossier sélectionné ('{os.path.basename(dossier_mesure)}') n'appartient pas au projet courant ('{nom_projet}')."
       )
       return

    # Mettre à jour current_directory pour qu'il pointe vers le sous-dossier horodaté
    current_directory = dossier_mesure

    # Mettre à jour 'nom_mesure_ouvert' avec le nom du dossier de mesure sélectionné
    nom_mesure_ouvert = os.path.basename(dossier_mesure)

    # Mettre à jour 'nom_mesure_ouvert' avec le nom du rapport
    nom_fichier_csv = f"rapport_defauts_{nom_mesure_ouvert}.csv"
    
    # Afficher un message confirmant la sélection
    messagebox.showinfo("Succès", f"Mesure sélectionnée : {dossier_mesure}")
    print(f"Mesure actuelle : {dossier_mesure}")
    mesure_ouvert = True
    menu_fichier.entryconfig("Nouvelle mesure", state="disabled")
    menu_fichier.entryconfig("Modifier une mesure", state="disabled")
    activer_boutons()
    
    # Mettre à jour le label du projet et mesure pour indiquer à l'utilisateur sur quel projet il se trouve
    # et quelle campagne de mesure est ouverte
    update_projet_mesure_label()


# Fonction qui permet d'importer des images provenant de la campagne de mesures et les placer dans le 
def import_image():
    global current_directory  # Le dossier de la mesure actuelle

    # Vérifier que la mesure actuelle est sélectionnée
    if not current_directory:
        messagebox.showerror("Erreur", "Aucune mesure sélectionnée. Veuillez ouvrir ou créer une mesure avant d'importer des images.")
        return

    # Déterminer le chemin correct du sous-dossier 'donnees brutes/images_defauts'
    sous_dossier_images = os.path.join(current_directory, "donnees brutes", "images_defauts")
    
    # Vérifier que le sous-dossier 'images_defauts' existe et le créer si nécessaire
    if not os.path.exists(sous_dossier_images):
        os.makedirs(sous_dossier_images)
        print(f"Sous-dossier créé : {sous_dossier_images}")

    # Ouvrir un dialogue pour sélectionner une ou plusieurs images
    images_selectionnees = filedialog.askopenfilenames(
        title="Sélectionnez des images de défauts",
        filetypes=[("Fichiers JPEG", "*.jpeg *.jpg"), ("Fichiers PNG", "*.png")],
        initialdir=current_directory
    )
    
    if not images_selectionnees:
        messagebox.showinfo("Annulé", "Aucune image sélectionnée.")
        return

    # Copier les images sélectionnées dans le sous-dossier 'images_defauts'
    for image in images_selectionnees:
        try:
            shutil.copy(image, sous_dossier_images)
            print(f"Image importée : {image}")
        except Exception as e:
            print(f"Erreur lors de l'importation de l'image {image} : {e}")

    messagebox.showinfo("Succès", f"{len(images_selectionnees)} image(s) importée(s) dans '{sous_dossier_images}'.")


# Fonction pour afficher une fenêtre A propos qui donne à l'utilisateur le contexte du projet BeProAct 
def afficher_apropos():
    # Créer une nouvelle fenêtre
    fenetre_aide = Toplevel(fenetre)
    fenetre_aide.title("A propos de BeProAct")
    fenetre_aide.geometry("600x400")
    
    # Ajouter le A propos du projet 
    try:
        with open("Apropos.txt", "r", encoding="utf-8") as fichier:
            texte_aide = fichier.read()
    except FileNotFoundError:
        texte_aide = "Fichier d'aide introuvable."
    
    label_aide = tk.Label(fenetre_aide, text=texte_aide, wraplength=250, justify="center")
    label_aide.pack(padx=10, pady=10)

# Fonction pour lancer le logiciel Blender depuis l'interface
def ouvrir_blender():
    try:
        #IMPORTANT Préciser le chemin du logiciel sur la machine actuelle
        blender_path = r"C:\Program Files\Blender Foundation\Blender 4.2\blender-launcher.exe"
        subprocess.Popen([blender_path])  # Ouvre Blender
    except FileNotFoundError:
        print("Blender introuvable. Vérifiez le chemin.")

# Fonction pour lancer le logiciel Meshroom depuis l'interface
def ouvrir_meshroom():
    try:
        #IMPORTANT Préciser le chemin du logiciel sur la machine actuelle
        meshroom_path = r"C:\Users\lingm\OneDrive\Documents\Meshroom-2023.3.0\Meshroom.exe"
        subprocess.Popen([meshroom_path])  # Ouvre Meshroom
    except FileNotFoundError:
        print("Meshroom introuvable. Vérifiez le chemin.")
    print("Répertoire actuel :", os.getcwd())
    

# Fonction pour enregistrer les données d'inspections après traitement d'image 
def enregistrer_data() :
    
    global nom_projet_ouvert,nom_mesure_ouvert,nom_fichier_csv
    
    # Construire le chemin vers le fichier CSV à partir des variables d'état de l'interface
    chemin_fichier_csv = os.path.join("projets",nom_projet_ouvert,nom_mesure_ouvert,"resultats",nom_fichier_csv)

    # Vérifier qu'il y a des données à enregistrer
    if not defects_data:
        print("Aucune donnée à enregistrer.")
        return
    
    # Ouvrir le fichier rapport défauts de la mesure actuellle en utilisant le chemin reconstruit 
    with open(chemin_fichier_csv, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        #Ecrire dans le fichier les en-têtes des colonnes et les données collectées lors du traitement d'image
        writer.writerow(["Defaut N°", "Position (px)", "Position (cm)", "Largeur (cm)", "Hauteur (cm)"])
        writer.writerows(defects_data)
    
    print(f"Données enregistrées dans : {chemin_fichier_csv}")
    

# Fonction pour activer ou désactiver les boutons et empêcher un utilisateur de faire n'importe quoi
def activer_boutons():
    """Active ou désactive les boutons en fonction de l'état des variables globales."""
    if projet_ouvert and mesure_ouvert:
        btn_import.config(state="normal")
        btn_detect.config(state="normal")
        btn_save.config(state ="normal")
        btn_meshroom.config(state ="normal")
        btn_blender.config(state ="normal")
    else:
        btn_import.config(state="disabled")        
        btn_detect.config(state="disabled")       
        btn_save.config(state="disabled")
        btn_meshroom.config(state ="disabled")
        btn_blender.config(state ="disabled")


# Fonction pour placer les images après initialisation de la fenêtre
def positionner_images():
    # Dimensions de la fenêtre
    window_width = fenetre.winfo_width()
    window_height = fenetre.winfo_height()

    # Dimensions des images
    img1_width, img1_height = image1_resized.size
    img2_width, img2_height = image2_resized.size

    # Décalage vertical supplémentaire pour éloigner du bas
    vertical_offset = 70

    # Position de l'image 1 (bas à gauche)
    label1.place(x=10,  # Proche du bord gauche
                 y=window_height - img1_height - vertical_offset)

    # Position de l'image 2 (bas à droite)
    label2.place(x=window_width - img2_width - 10,  # Proche du bord droit
                 y=window_height - img2_height - vertical_offset)


# Fonction pour redimensionner proportionnellement une image
def resize_image(image, max_width, max_height):
    width, height = image.size
    aspect_ratio = width / height
    if width > height:
        new_width = min(width, max_width)
        new_height = int(new_width / aspect_ratio)
    else:
        new_height = min(height, max_height)
        new_width = int(new_height * aspect_ratio)
    return image.resize((new_width, new_height))


    
# Fonction pour mettre à jour le label avec les informations du projet et de la mesure
def update_projet_mesure_label():
    global nom_projet_ouvert, nom_mesure_ouvert
    
    if nom_projet_ouvert and nom_mesure_ouvert:
        label_projet_mesure.config(text=f"Projet: {nom_projet_ouvert} - Mesure: {nom_mesure_ouvert}")
    elif nom_projet_ouvert:
        label_projet_mesure.config(text=f"Projet: {nom_projet_ouvert} - Aucune mesure ouverte")
    else:
        label_projet_mesure.config(text="Aucun projet ou mesures d'ouverts")
    
    # Réactualiser toutes les 1000ms (1 seconde)
    fenetre.after(1000, update_projet_mesure_label)
        
# Créer la barre de menu
menu_barre = tk.Menu(fenetre)

# Créer le menu "Fichier"
menu_fichier = tk.Menu(menu_barre, tearoff=0)
menu_fichier.add_command(label="Nouveau projet", command=nouveau_projet)
menu_fichier.add_command(label="Ouvrir projet", command=ouvrir_projet)
menu_fichier.add_command(label="Nouvelle mesure", command=nouvelle_mesure, state="disabled")
menu_fichier.add_command(label="Modifier une mesure", command=modifier_mesure, state="disabled")
menu_fichier.add_command(label="Fermer projet", command=quitter_projet, state="disabled")
menu_fichier.add_command(label="Créer rapport projet", command=lambda: print("Créer rapport de projet"))
menu_fichier.add_separator()  # Ligne de séparation
menu_fichier.add_command(label="Quitter BeProAct", command=fenetre.destroy)

# Créer le menu "Aide"
menu_aide = tk.Menu(menu_barre, tearoff=0)
menu_aide.add_command(label="À propos", command=afficher_apropos)


# Ajouter le menu "Fichier" à la barre de menu
menu_barre.add_cascade(label="Fichier", menu=menu_fichier)
menu_barre.add_cascade(label="Aide", menu=menu_aide)


# Ajouter un label pour "Outils de la suite BeProAct"
label_outils = tk.Label(fenetre, text="Outils de la suite BeProAct", font=("Helvetica", 16, "bold"), fg="black")
label_outils.pack(side="top", pady=10)


frame_boutons = tk.Frame(fenetre)
frame_boutons.pack(side="top", anchor = "w",pady=10)

# Bouton pour ouvrir Meshroom
btn_meshroom = tk.Button(frame_boutons, text="Modéliser sur Meshroom", command=ouvrir_meshroom, bg="cyan", fg="black")
btn_meshroom.pack(side="left", padx=10)

# Bouton pour ouvrir Blender
btn_blender = tk.Button(frame_boutons, text="Porter sur Blender", command=ouvrir_blender, bg="orange", fg="black")
btn_blender.pack(side = "left", pady=10, padx = 20)

# Bouton pour importer les images à analyser
btn_import = tk.Button(frame_boutons, text="Importer images défauts (.jpeg)", command=import_image, bg="light blue", fg="black")
btn_import.pack(side = "left", pady=10, padx = 20) 

# Bouton pour lancer le script de détection des fissures
btn_detect = tk.Button(frame_boutons, text="Détecter les défauts", command=select_image, bg="salmon", fg="black")
btn_detect.pack(side = "left", pady=10, padx = 20) 

# Bouton pour enregistrer les données de la détection dans le rapport
btn_save = tk.Button(frame_boutons, text="Enregistrer les données", command=enregistrer_data, bg="light green", fg="black")
btn_save.pack(side = "left", pady=10, padx = 20) 

# Label pour afficher le projet et la mesure ouverts (se met à jour en continu)
label_projet_mesure = tk.Label(fenetre, text="Aucun projet ou mesures d'ouverts", font=("Helvetica", 12), fg="black")
label_projet_mesure.pack(side="top", pady=5)



# Créer un canevas pour afficher l'image
canvas = tk.Canvas(fenetre, width=800, height=500)
canvas.pack()

# Charger l'image avec PIL
image = Image.open("instructions_debut.png")

# Redimensionner l'image pour qu'elle tienne dans le canevas
image_resized = image.resize((500, 300), Image.Resampling.LANCZOS)

# Convertir l'image redimensionnée pour Tkinter
image_tk = ImageTk.PhotoImage(image_resized)

# Calculer les coordonnées pour centrer l'image
canvas_width = 800
canvas_height = 500
image_width, image_height = image_resized.size
center_x = canvas_width // 2
center_y = canvas_height // 2 -70

# Placer l'image au centre du canevas
canvas.create_image(center_x, center_y, anchor="center", image=image_tk)

# Garder une référence à l'image pour éviter le problème de collection par le garbage collector
canvas.image = image_tk


# Charger les images des logos de l'université de Lille et du projet BeProAct
image1 = Image.open("logo_BeProAct.png")  
image2 = Image.open("logo_Ulille.png")

# Redimensionner les images proportionnellement (maximum 300x300)
image1_resized = resize_image(image1, 230,230)
image2_resized = resize_image(image2, 230,230)

# Convertir les images redimensionnées en objets Tkinter
photo1 = ImageTk.PhotoImage(image1_resized)
photo2 = ImageTk.PhotoImage(image2_resized)

# Créer des labels pour afficher les images
label1 = tk.Label(fenetre, image=photo1)
label2 = tk.Label(fenetre, image=photo2)



# Initialiser les boutons de l'interface au départ 
activer_boutons()

# Afficher le logo de Polytech
afficher_logo()

# positionner les logos de l'université de Lille et du projet BeProAct
positionner_images()

# Empêcher l'utilisateur de changer la taille de la fenêtre 
fenetre.resizable(False,False)

# Mettre le menu
fenetre.config(menu=menu_barre)

# Lancer la fenêtre principale de l'interface
fenetre.mainloop()

